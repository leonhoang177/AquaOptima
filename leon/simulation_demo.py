#!/usr/bin/env python3
"""
Largemouth Bass Aquaculture Optimizer
PSO (fish swarm behavior) + EA (pond configuration evolution)
"""

import random
import math
import json
import copy
import os
from dataclasses import dataclass, field
from typing import List, Optional, Tuple
from enum import IntEnum

# ============================================================
# CONSTANTS
# ============================================================
FOOD_PRICE = 0.10
PROBIOTIC_PRICE = 0.50
OXYGEN_PRICE = 2.00

W1_SURVIVAL = 0.50
W2_CONDITION = 0.35
W3_EFFICIENCY = 0.15

POND_WIDTH = 200.0
POND_HEIGHT = 200.0

# Fish stat ranges
HP_RANGE = (80, 120)
ENERGY_RANGE = (60, 100)
FULLNESS_RANGE = (50, 80)
IMMUNITY_RANGE = (70, 100)
OXYGEN_RANGE = (80, 100)
VELOCITY_RANGE = (1.0, 3.0)
MOUTH_SIZE_RANGE = (3, 8)
BODY_SIZE_RANGE = (4, 10)

# PSO distances
SENSITIVE_DISTANCE = 40.0
SOCIAL_DISTANCE = 25.0
SELFISH_DISTANCE = 8.0

# Decay rates per timestep
OXYGEN_DECAY = 0.3
ENERGY_DECAY = 0.15
FULLNESS_DECAY = 0.2
IMMUNITY_DECAY_IN_DISEASE = 1.5
HP_DECAY_NO_ENERGY = 0.8
HP_DECAY_NO_FULLNESS = 0.5
HP_DECAY_INFECTED = 1.0
HP_DECAY_PARASITE = 1.5
ENERGY_COST_MOVE = 0.2

# Object lifetimes
FOOD_EXPIRE_TIMESTEPS = 30
PROBIOTIC_EXPIRE_TIMESTEPS = 10
FECAL_EXPIRE_TIMESTEPS = 20
DEAD_FISH_DECAY_TIMESTEPS = 10
NH3_EXPIRE_TIMESTEPS = 40
DISEASE_AREA_DECAY = 50
PARASITE_AREA_DECAY = 50
POLLUTANT_TO_HAZARD_TIMESTEPS = 15

# Gains
FOOD_ENERGY_GAIN = 15.0
FOOD_FULLNESS_GAIN = 12.0
PROBIOTIC_IMMUNITY_BOOST = 30.0
OXYGEN_BUBBLE_GAIN = 20.0
IMMUNITY_BOOST_DURATION = 10
BOOSTING_DURATION = 5

# Natural spawn rates
NATURAL_OXYGEN_SPAWN_RATE = 0.02
NATURAL_NH3_SPAWN_RATE = 0.01

# Obstacle count
NUM_OBSTACLES = 5


class DropLocation(IntEnum):
    MIDDLE = 0
    CORNER = 1
    RANDOM = 2


# ============================================================
# DATA CLASSES
# ============================================================

@dataclass
class PondGenotype:
    food_interval: int = 6
    food_quantity: int = 5
    food_location: int = 0
    probiotic_interval: int = 12
    probiotic_quantity: int = 3
    probiotic_location: int = 0
    oxygen_interval: int = 8
    oxygen_duration: int = 2
    oxygen_location: int = 0

    def total_cost(self, runtime: int) -> float:
        food_cost = (runtime / self.food_interval) * self.food_quantity * FOOD_PRICE
        prob_cost = (runtime / self.probiotic_interval) * self.probiotic_quantity * PROBIOTIC_PRICE
        oxy_cost = (runtime / self.oxygen_interval) * self.oxygen_duration * OXYGEN_PRICE
        return food_cost + prob_cost + oxy_cost

    def gatekeeper_cost(self) -> float:
        return (self.food_quantity * FOOD_PRICE +
                self.probiotic_quantity * PROBIOTIC_PRICE +
                self.oxygen_duration * OXYGEN_PRICE)

    def to_dict(self):
        return {
            'food_interval': self.food_interval,
            'food_quantity': self.food_quantity,
            'food_location': self.food_location,
            'probiotic_interval': self.probiotic_interval,
            'probiotic_quantity': self.probiotic_quantity,
            'probiotic_location': self.probiotic_location,
            'oxygen_interval': self.oxygen_interval,
            'oxygen_duration': self.oxygen_duration,
            'oxygen_location': self.oxygen_location,
        }

    @staticmethod
    def random():
        return PondGenotype(
            food_interval=random.randint(1, 24),
            food_quantity=random.randint(1, 10),
            food_location=random.randint(0, 2),
            probiotic_interval=random.randint(1, 24),
            probiotic_quantity=random.randint(1, 10),
            probiotic_location=random.randint(0, 2),
            oxygen_interval=random.randint(1, 24),
            oxygen_duration=random.randint(1, 4),
            oxygen_location=random.randint(0, 2),
        )

    def crossover(self, other: 'PondGenotype') -> 'PondGenotype':
        child = PondGenotype()
        for attr in ['food_interval', 'food_quantity', 'food_location',
                      'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
                      'oxygen_interval', 'oxygen_duration', 'oxygen_location']:
            if random.random() < 0.5:
                setattr(child, attr, getattr(self, attr))
            else:
                setattr(child, attr, getattr(other, attr))
        return child

    def mutate(self, rate=0.2):
        if random.random() < rate:
            self.food_interval = random.randint(1, 24)
        if random.random() < rate:
            self.food_quantity = random.randint(1, 10)
        if random.random() < rate:
            self.food_location = random.randint(0, 2)
        if random.random() < rate:
            self.probiotic_interval = random.randint(1, 24)
        if random.random() < rate:
            self.probiotic_quantity = random.randint(1, 10)
        if random.random() < rate:
            self.probiotic_location = random.randint(0, 2)
        if random.random() < rate:
            self.oxygen_interval = random.randint(1, 24)
        if random.random() < rate:
            self.oxygen_duration = random.randint(1, 4)
        if random.random() < rate:
            self.oxygen_location = random.randint(0, 2)


@dataclass
class Obstacle:
    x: float
    y: float
    w: float
    h: float
    is_static: bool = True
    vx: float = 0.0
    vy: float = 0.0

    def contains(self, px, py):
        return (self.x <= px <= self.x + self.w and
                self.y <= py <= self.y + self.h)

    def nearest_surface_point(self, px, py):
        cx = max(self.x, min(px, self.x + self.w))
        cy = max(self.y, min(py, self.y + self.h))
        return cx, cy


@dataclass
class DynamicObject:
    x: float
    y: float
    obj_type: str  # 'food', 'probiotic', 'fecal', 'dead_fish', 'oxygen', 'pollutant'
    value: float = 5.0
    age: int = 0
    max_age: int = 30
    vx: float = 0.0
    vy: float = 0.0
    alive: bool = True


@dataclass
class HazardArea:
    x: float
    y: float
    radius: float
    hazard_type: str  # 'nh3', 'disease', 'parasite'
    age: int = 0
    max_age: int = 50
    alive: bool = True
    vx: float = 0.0
    vy: float = 0.0

    def contains(self, px, py):
        dx = px - self.x
        dy = py - self.y
        return (dx * dx + dy * dy) <= self.radius * self.radius


@dataclass
class Fish:
    # Identity
    fish_id: int = 0
    # Position & velocity
    x: float = 0.0
    y: float = 0.0
    vx: float = 0.0
    vy: float = 0.0
    # Traits (fixed)
    mouth_size: float = 5.0
    body_size: float = 6.0
    # Stats (dynamic)
    hp: float = 100.0
    max_hp: float = 100.0
    energy: float = 80.0
    max_energy: float = 80.0
    fullness: float = 60.0
    max_fullness: float = 60.0
    immunity: float = 80.0
    max_immunity: float = 80.0
    oxygen: float = 90.0
    max_oxygen: float = 90.0
    base_velocity: float = 2.0
    # States
    is_boosting: bool = False
    boost_timer: int = 0
    is_infected: bool = False
    has_parasite: bool = False
    is_running: bool = False
    is_hunting: bool = False
    alive: bool = True
    # Fecal tracking
    fecal_timer: int = 0

    def effective_velocity(self) -> float:
        v = self.base_velocity
        if self.hp <= self.max_hp * 0.5:
            v *= 0.5
        if self.energy <= self.max_energy * 0.5:
            v *= 0.5
        if self.fullness <= self.max_fullness * 0.5:
            v *= 0.5
        if self.has_parasite:
            v *= 0.75
        if self.is_running or self.is_hunting:
            v *= 1.5
        return v

    def normalized_stats(self):
        hp_n = max(0, self.hp) / self.max_hp
        en_n = max(0, self.energy) / self.max_energy
        fu_n = max(0, self.fullness) / self.max_fullness
        im_n = max(0, self.immunity) / self.max_immunity
        vel_n = min(1.0, self.effective_velocity() / (self.base_velocity * 1.5 + 0.01))
        return (hp_n + en_n + fu_n + im_n + vel_n) / 5.0

    def to_snapshot(self):
        return {
            'id': self.fish_id,
            'x': round(self.x, 1),
            'y': round(self.y, 1),
            'hp': round(self.hp, 1),
            'energy': round(self.energy, 1),
            'fullness': round(self.fullness, 1),
            'immunity': round(self.immunity, 1),
            'oxygen': round(self.oxygen, 1),
            'alive': self.alive,
            'is_infected': self.is_infected,
            'has_parasite': self.has_parasite,
            'is_running': self.is_running,
            'is_hunting': self.is_hunting,
            'is_boosting': self.is_boosting,
            'body_size': self.body_size,
            'mouth_size': self.mouth_size,
        }


def create_fish(fish_id: int) -> Fish:
    f = Fish()
    f.fish_id = fish_id
    f.x = random.uniform(20, POND_WIDTH - 20)
    f.y = random.uniform(20, POND_HEIGHT - 20)
    f.mouth_size = random.uniform(*MOUTH_SIZE_RANGE)
    f.body_size = random.uniform(*BODY_SIZE_RANGE)
    f.max_hp = random.uniform(*HP_RANGE)
    f.hp = f.max_hp
    f.max_energy = random.uniform(*ENERGY_RANGE)
    f.energy = f.max_energy
    f.max_fullness = random.uniform(*FULLNESS_RANGE)
    f.fullness = f.max_fullness * 0.8
    f.max_immunity = random.uniform(*IMMUNITY_RANGE)
    f.immunity = f.max_immunity
    f.max_oxygen = random.uniform(*OXYGEN_RANGE)
    f.oxygen = f.max_oxygen
    f.base_velocity = random.uniform(*VELOCITY_RANGE)
    f.vx = random.uniform(-1, 1)
    f.vy = random.uniform(-1, 1)
    return f


def get_drop_position(location_enum: int) -> Tuple[float, float]:
    if location_enum == DropLocation.MIDDLE:
        return (POND_WIDTH / 2 + random.uniform(-15, 15),
                POND_HEIGHT / 2 + random.uniform(-15, 15))
    elif location_enum == DropLocation.CORNER:
        corner = random.choice([
            (15, 15), (POND_WIDTH - 15, 15),
            (15, POND_HEIGHT - 15), (POND_WIDTH - 15, POND_HEIGHT - 15)
        ])
        return (corner[0] + random.uniform(-10, 10),
                corner[1] + random.uniform(-10, 10))
    else:
        return (random.uniform(10, POND_WIDTH - 10),
                random.uniform(10, POND_HEIGHT - 10))


def dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)


def clamp(val, lo, hi):
    return max(lo, min(hi, val))


def normalize_vec(vx, vy):
    mag = math.sqrt(vx * vx + vy * vy)
    if mag < 1e-8:
        return 0.0, 0.0
    return vx / mag, vy / mag


# ============================================================
# POND SIMULATION ENGINE
# ============================================================

class PondSimulation:
    def __init__(self, genotype: PondGenotype, fishes: List[Fish], runtime: int,
                 max_budget: float, record_frames: bool = False, frame_skip: int = 1):
        self.genotype = genotype
        self.runtime = runtime
        self.max_budget = max_budget
        self.record_frames = record_frames
        self.frame_skip = frame_skip

        # Deep copy fishes so each pond gets its own swarm
        self.fishes: List[Fish] = copy.deepcopy(fishes)
        self.initial_count = len(self.fishes)
        self.timestep = 0

        # Environment objects
        self.objects: List[DynamicObject] = []
        self.hazards: List[HazardArea] = []
        self.obstacles: List[Obstacle] = []

        # Generate obstacles
        self._generate_obstacles()

        # Oxygen pump tracking
        self.oxygen_pump_active = 0

        # Recording
        self.frames = []

        # PSO inertia
        self.w_inertia = 0.4

    def _generate_obstacles(self):
        for i in range(NUM_OBSTACLES):
            w = random.uniform(8, 20)
            h = random.uniform(8, 20)
            x = random.uniform(10, POND_WIDTH - 10 - w)
            y = random.uniform(10, POND_HEIGHT - 10 - h)
            is_static = random.random() < 0.6
            vx = random.uniform(-0.3, 0.3) if not is_static else 0
            vy = random.uniform(-0.3, 0.3) if not is_static else 0
            self.obstacles.append(Obstacle(x, y, w, h, is_static, vx, vy))

    def _is_in_obstacle(self, px, py):
        for obs in self.obstacles:
            if obs.contains(px, py):
                return True
        return False

    def _clamp_to_pond(self, x, y):
        return clamp(x, 2, POND_WIDTH - 2), clamp(y, 2, POND_HEIGHT - 2)

    def run(self) -> dict:
        for t in range(self.runtime):
            self.timestep = t
            self._step()
            if self.record_frames and (t % self.frame_skip == 0):
                self.frames.append(self._capture_frame())
            # Early termination if all fish dead
            alive_fish = [f for f in self.fishes if f.alive]
            if len(alive_fish) == 0:
                break

        alive_fish = [f for f in self.fishes if f.alive]
        survival_rate = len(alive_fish) / self.initial_count if self.initial_count > 0 else 0
        avg_condition = 0.0
        if alive_fish:
            avg_condition = sum(f.normalized_stats() for f in alive_fish) / len(alive_fish)

        cost = self.genotype.total_cost(self.runtime)
        efficiency = max(0, (self.max_budget - cost) / self.max_budget)

        fitness = W1_SURVIVAL * survival_rate + W2_CONDITION * avg_condition + W3_EFFICIENCY * efficiency

        return {
            'survival_rate': survival_rate,
            'avg_condition': avg_condition,
            'efficiency': efficiency,
            'fitness': fitness,
            'cost': cost,
            'alive_count': len(alive_fish),
            'initial_count': self.initial_count,
            'frames': self.frames,
            'genotype': self.genotype.to_dict(),
        }

    def _step(self):
        t = self.timestep

        # 1. Spawn policies
        self._spawn_food(t)
        self._spawn_probiotics(t)
        self._manage_oxygen_pump(t)
        self._natural_spawns()

        # 2. Update dynamic objects (age, expire, transform)
        self._update_objects()

        # 3. Update hazard areas
        self._update_hazards()

        # 4. Update obstacles (dynamic ones)
        self._update_obstacles()

        # 5. Fish stat decay
        self._decay_fish_stats()

        # 6. Fish-environment interactions (eating, absorbing oxygen, disease/parasite contact)
        self._fish_environment_interactions()

        # 7. PSO movement
        self._pso_update()

        # 8. Cannibalism check
        self._cannibalism_check()

        # 9. Fecal drops
        self._fecal_drops()

        # 10. Fish death check
        self._death_check()

    # ---------- SPAWNING ----------
    def _spawn_food(self, t):
        if t % self.genotype.food_interval == 0:
            for _ in range(self.genotype.food_quantity):
                x, y = get_drop_position(self.genotype.food_location)
                self.objects.append(DynamicObject(
                    x=x, y=y, obj_type='food',
                    value=5.0, max_age=FOOD_EXPIRE_TIMESTEPS
                ))

    def _spawn_probiotics(self, t):
        if t % self.genotype.probiotic_interval == 0:
            for _ in range(self.genotype.probiotic_quantity):
                x, y = get_drop_position(self.genotype.probiotic_location)
                self.objects.append(DynamicObject(
                    x=x, y=y, obj_type='probiotic',
                    value=3.0, max_age=PROBIOTIC_EXPIRE_TIMESTEPS
                ))

    def _manage_oxygen_pump(self, t):
        if t % self.genotype.oxygen_interval == 0:
            self.oxygen_pump_active = self.genotype.oxygen_duration
        if self.oxygen_pump_active > 0:
            # Spawn oxygen bubbles
            for _ in range(3):
                x, y = get_drop_position(self.genotype.oxygen_location)
                self.objects.append(DynamicObject(
                    x=x, y=y, obj_type='oxygen',
                    value=1.0, max_age=9999,
                    vx=random.uniform(-0.5, 0.5),
                    vy=random.uniform(-0.5, 0.5)
                ))
            self.oxygen_pump_active -= 1

    def _natural_spawns(self):
        if random.random() < NATURAL_OXYGEN_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH - 10), random.uniform(10, POND_HEIGHT - 10)
            self.objects.append(DynamicObject(
                x=x, y=y, obj_type='oxygen', value=1.0, max_age=9999,
                vx=random.uniform(-0.5, 0.5), vy=random.uniform(-0.5, 0.5)
            ))
        if random.random() < NATURAL_NH3_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH - 10), random.uniform(10, POND_HEIGHT - 10)
            self.hazards.append(HazardArea(
                x=x, y=y, radius=random.uniform(8, 15),
                hazard_type='nh3', max_age=NH3_EXPIRE_TIMESTEPS,
                vx=random.uniform(-0.2, 0.2), vy=random.uniform(-0.2, 0.2)
            ))

    # ---------- OBJECT UPDATES ----------
    def _update_objects(self):
        new_objects = []
        for obj in self.objects:
            obj.age += 1
            # Move if has velocity
            if obj.obj_type == 'oxygen':
                obj.x += obj.vx
                obj.y += obj.vy
                # Bounce off walls
                if obj.x < 2 or obj.x > POND_WIDTH - 2:
                    obj.vx *= -1
                if obj.y < 2 or obj.y > POND_HEIGHT - 2:
                    obj.vy *= -1
                obj.x, obj.y = self._clamp_to_pond(obj.x, obj.y)
                # Remove oxygen if inside NH3
                in_nh3 = any(h.contains(obj.x, obj.y) and h.hazard_type == 'nh3' and h.alive
                             for h in self.hazards)
                if in_nh3:
                    obj.alive = False
                    continue
                new_objects.append(obj)
                continue

            if obj.age >= obj.max_age and obj.alive:
                # Expire -> become pollutant
                if obj.obj_type in ('food', 'probiotic', 'fecal', 'dead_fish'):
                    if obj.value > 0:
                        poll_val = obj.value
                        if obj.obj_type == 'dead_fish':
                            poll_val = obj.value * 1.5
                        # Don't create pollutant inside NH3
                        in_nh3 = any(h.contains(obj.x, obj.y) and h.hazard_type == 'nh3' and h.alive
                                     for h in self.hazards)
                        if not in_nh3:
                            new_objects.append(DynamicObject(
                                x=obj.x, y=obj.y, obj_type='pollutant',
                                value=poll_val, max_age=POLLUTANT_TO_HAZARD_TIMESTEPS
                            ))
                    obj.alive = False
                    continue
                elif obj.obj_type == 'pollutant':
                    # Pollutant -> disease or parasite area
                    r = obj.value * 1.5
                    if random.random() < 0.4:
                        self.hazards.append(HazardArea(
                            x=obj.x, y=obj.y, radius=r,
                            hazard_type='disease', max_age=DISEASE_AREA_DECAY
                        ))
                    if random.random() < 0.3:
                        self.hazards.append(HazardArea(
                            x=obj.x, y=obj.y, radius=r,
                            hazard_type='parasite', max_age=PARASITE_AREA_DECAY
                        ))
                    obj.alive = False
                    continue

            if obj.alive:
                new_objects.append(obj)

        self.objects = new_objects

    def _update_hazards(self):
        new_hazards = []
        for h in self.hazards:
            h.age += 1
            # Move NH3
            if h.hazard_type == 'nh3':
                h.x += h.vx
                h.y += h.vy
                if h.x < 5 or h.x > POND_WIDTH - 5:
                    h.vx *= -1
                if h.y < 5 or h.y > POND_HEIGHT - 5:
                    h.vy *= -1
                h.x = clamp(h.x, 5, POND_WIDTH - 5)
                h.y = clamp(h.y, 5, POND_HEIGHT - 5)

            if h.age >= h.max_age:
                if h.hazard_type == 'nh3':
                    # NH3 expires -> pollutant with 50% value
                    in_nh3_other = False  # already expiring
                    self.objects.append(DynamicObject(
                        x=h.x, y=h.y, obj_type='pollutant',
                        value=h.radius * 0.5, max_age=POLLUTANT_TO_HAZARD_TIMESTEPS
                    ))
                h.alive = False
                continue

            # Disease and parasite areas decay radius
            if h.hazard_type in ('disease', 'parasite'):
                h.radius = max(1, h.radius * 0.998)

            if h.alive:
                new_hazards.append(h)

        self.hazards = new_hazards

    def _update_obstacles(self):
        for obs in self.obstacles:
            if not obs.is_static:
                obs.x += obs.vx
                obs.y += obs.vy
                if obs.x < 2 or obs.x + obs.w > POND_WIDTH - 2:
                    obs.vx *= -1
                if obs.y < 2 or obs.y + obs.h > POND_HEIGHT - 2:
                    obs.vy *= -1
                obs.x = clamp(obs.x, 2, POND_WIDTH - 2 - obs.w)
                obs.y = clamp(obs.y, 2, POND_HEIGHT - 2 - obs.h)

    # ---------- FISH STAT DECAY ----------
    def _decay_fish_stats(self):
        for f in self.fishes:
            if not f.alive:
                continue
            # Oxygen natural decay
            f.oxygen -= OXYGEN_DECAY
            # Check if in NH3 -> faster oxygen drain
            for h in self.hazards:
                if h.hazard_type == 'nh3' and h.alive and h.contains(f.x, f.y):
                    f.oxygen -= OXYGEN_DECAY * 2

            # Energy decay
            energy_cost = ENERGY_DECAY
            if f.has_parasite:
                energy_cost *= 1.5
            if f.is_running or f.is_hunting:
                energy_cost *= 1.5
            f.energy -= energy_cost

            # Fullness decay
            fullness_decay = FULLNESS_DECAY
            if f.has_parasite:
                fullness_decay *= 1.5
            f.fullness -= fullness_decay

            # HP effects
            if f.energy <= 0:
                f.hp -= HP_DECAY_NO_ENERGY
            if f.fullness <= 0:
                f.hp -= HP_DECAY_NO_FULLNESS
            if f.is_infected:
                f.hp -= HP_DECAY_INFECTED
            if f.has_parasite and self.timestep % 3 == 0:
                f.hp -= HP_DECAY_PARASITE

            # Boosting timer
            if f.is_boosting:
                f.boost_timer -= 1
                if f.boost_timer <= 0:
                    f.is_boosting = False

            # Disease contact
            for h in self.hazards:
                if h.hazard_type == 'disease' and h.alive and h.contains(f.x, f.y):
                    f.immunity -= IMMUNITY_DECAY_IN_DISEASE
                    if f.immunity <= 0:
                        f.is_infected = True
                        f.immunity = 0

            # Parasite contact
            for h in self.hazards:
                if h.hazard_type == 'parasite' and h.alive and h.contains(f.x, f.y):
                    if random.random() < 0.1:
                        f.has_parasite = True

    # ---------- FISH-ENVIRONMENT INTERACTIONS ----------
    def _fish_environment_interactions(self):
        for f in self.fishes:
            if not f.alive:
                continue

            for obj in self.objects:
                if not obj.alive or obj.value <= 0:
                    continue
                d = dist(f.x, f.y, obj.x, obj.y)
                if d > f.body_size + 2:
                    continue

                if obj.obj_type == 'food' and f.fullness < f.max_fullness:
                    obj.value -= 1
                    gain = FOOD_FULLNESS_GAIN
                    if f.has_parasite:
                        gain *= 0.5
                    f.fullness = min(f.max_fullness, f.fullness + gain)
                    f.energy = min(f.max_energy, f.energy + FOOD_ENERGY_GAIN)
                    if obj.value <= 0:
                        obj.alive = False

                elif obj.obj_type == 'probiotic' and not f.is_boosting:
                    obj.value -= 1
                    f.immunity = min(f.max_immunity, f.immunity + PROBIOTIC_IMMUNITY_BOOST)
                    f.is_boosting = True
                    f.boost_timer = BOOSTING_DURATION
                    if obj.value <= 0:
                        obj.alive = False

                elif obj.obj_type == 'oxygen':
                    f.oxygen = min(f.max_oxygen, f.oxygen + OXYGEN_BUBBLE_GAIN)
                    obj.alive = False

    # ---------- PSO UPDATE ----------
    def _pso_update(self):
        alive_fish = [f for f in self.fishes if f.alive]
        if not alive_fish:
            return

        for f in alive_fish:
            vel = f.effective_velocity()
            # Start with inertia
            new_vx = self.w_inertia * f.vx
            new_vy = self.w_inertia * f.vy

            # Calculate all PSO vectors
            vectors = self._calculate_pso_vectors(f, alive_fish)

            for weight, vx, vy in vectors:
                new_vx += weight * vx
                new_vy += weight * vy

            # Normalize and scale by effective velocity
            mag = math.sqrt(new_vx ** 2 + new_vy ** 2)
            if mag > 0.01:
                new_vx = (new_vx / mag) * vel
                new_vy = (new_vy / mag) * vel

            # State overrides
            if f.has_parasite and random.random() < 0.6:
                # Scrub against nearest obstacle
                sv = self._scrub_vector(f)
                if sv:
                    new_vx, new_vy = sv[0] * vel, sv[1] * vel

            if f.is_running and random.random() < 0.7:
                rv = self._run_vector(f, alive_fish)
                if rv:
                    new_vx, new_vy = rv[0] * vel * 1.2, rv[1] * vel * 1.2

            if f.is_hunting and random.random() < 0.7:
                hv = self._hunt_vector_direct(f, alive_fish)
                if hv:
                    new_vx, new_vy = hv[0] * vel * 1.2, hv[1] * vel * 1.2

            f.vx = new_vx
            f.vy = new_vy

            # Move
            new_x = f.x + f.vx
            new_y = f.y + f.vy

            # Obstacle collision
            for obs in self.obstacles:
                if obs.contains(new_x, new_y):
                    # Push out
                    sx, sy = obs.nearest_surface_point(f.x, f.y)
                    dx, dy = f.x - sx, f.y - sy
                    dx, dy = normalize_vec(dx, dy)
                    new_x = f.x + dx * 2
                    new_y = f.y + dy * 2
                    f.vx *= -0.5
                    f.vy *= -0.5
                    # Scrubbing removes parasite
                    if f.has_parasite and random.random() < 0.15:
                        f.has_parasite = False

            new_x, new_y = self._clamp_to_pond(new_x, new_y)
            f.x = new_x
            f.y = new_y

            # Energy cost for movement
            move_cost = ENERGY_COST_MOVE * vel
            if f.has_parasite:
                move_cost *= 1.5
            if f.is_running or f.is_hunting:
                move_cost *= 1.5
            f.energy -= move_cost

    def _calculate_pso_vectors(self, f: Fish, alive_fish: List[Fish]):
        vectors = []

        # ---------- cFood ----------
        fullness_ratio = max(0, f.fullness) / f.max_fullness
        if fullness_ratio < 1.0:
            food_weight = 2.0 * (1.0 - fullness_ratio)
            energy_ratio = max(0, f.energy) / f.max_energy
            if energy_ratio < 0.3:
                food_weight *= 2.0
            nearest_food = None
            nearest_dist = float('inf')
            for obj in self.objects:
                if obj.alive and obj.obj_type == 'food' and obj.value > 0:
                    d = dist(f.x, f.y, obj.x, obj.y)
                    if d < SENSITIVE_DISTANCE and d < nearest_dist:
                        nearest_dist = d
                        nearest_food = obj
            if nearest_food:
                dx, dy = normalize_vec(nearest_food.x - f.x, nearest_food.y - f.y)
                vectors.append((food_weight, dx, dy))

        # ---------- cProbiotic ----------
        if not f.is_boosting:
            imm_ratio = max(0, f.immunity) / f.max_immunity
            prob_weight = 1.5 * (1.0 - imm_ratio)
            nearest_prob = None
            nearest_dist = float('inf')
            for obj in self.objects:
                if obj.alive and obj.obj_type == 'probiotic' and obj.value > 0:
                    d = dist(f.x, f.y, obj.x, obj.y)
                    if d < SENSITIVE_DISTANCE and d < nearest_dist:
                        nearest_dist = d
                        nearest_prob = obj
            if nearest_prob:
                dx, dy = normalize_vec(nearest_prob.x - f.x, nearest_prob.y - f.y)
                vectors.append((prob_weight, dx, dy))

        # ---------- cOxygen ----------
        oxy_ratio = max(0, f.oxygen) / f.max_oxygen
        if oxy_ratio < 0.7:
            oxy_weight = 3.0 * (1.0 - oxy_ratio)
            if oxy_ratio < 0.3:
                oxy_weight *= 3.0  # Critical priority
            nearest_oxy = None
            nearest_dist = float('inf')
            for obj in self.objects:
                if obj.alive and obj.obj_type == 'oxygen':
                    d = dist(f.x, f.y, obj.x, obj.y)
                    # Intercept path: predict where bubble will be
                    future_x = obj.x + obj.vx * 3
                    future_y = obj.y + obj.vy * 3
                    d_future = dist(f.x, f.y, future_x, future_y)
                    effective_d = min(d, d_future)
                    if effective_d < SENSITIVE_DISTANCE and effective_d < nearest_dist:
                        nearest_dist = effective_d
                        nearest_oxy = obj
            if nearest_oxy:
                # Intercept
                target_x = nearest_oxy.x + nearest_oxy.vx * 3
                target_y = nearest_oxy.y + nearest_oxy.vy * 3
                dx, dy = normalize_vec(target_x - f.x, target_y - f.y)
                vectors.append((oxy_weight, dx, dy))

        # ---------- cSocial & cSelfish ----------
        social_vx, social_vy = 0.0, 0.0
        selfish_vx, selfish_vy = 0.0, 0.0
        social_count = 0
        selfish_count = 0

        for other in alive_fish:
            if other.fish_id == f.fish_id:
                continue
            d = dist(f.x, f.y, other.x, other.y)
            if d < SELFISH_DISTANCE and d > 0.1:
                dx, dy = normalize_vec(f.x - other.x, f.y - other.y)
                selfish_vx += dx / d
                selfish_vy += dy / d
                selfish_count += 1
            elif d < SOCIAL_DISTANCE:
                social_vx += other.x - f.x
                social_vy += other.y - f.y
                social_count += 1

        if social_count > 0:
            sx, sy = normalize_vec(social_vx / social_count, social_vy / social_count)
            vectors.append((0.8, sx, sy))

        if selfish_count > 0:
            sx, sy = normalize_vec(selfish_vx, selfish_vy)
            vectors.append((1.5, sx, sy))

        # ---------- cNH3 ----------
        for h in self.hazards:
            if h.hazard_type == 'nh3' and h.alive:
                d = dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    nh3_weight = 4.0
                    # Unless extremely hungry and food inside
                    if fullness_ratio < 0.1:
                        has_food_in_nh3 = any(
                            obj.alive and obj.obj_type == 'food' and h.contains(obj.x, obj.y)
                            for obj in self.objects
                        )
                        if has_food_in_nh3:
                            nh3_weight = 0.5
                    dx, dy = normalize_vec(f.x - h.x, f.y - h.y)
                    vectors.append((nh3_weight, dx, dy))

        # ---------- cDisease ----------
        for h in self.hazards:
            if h.hazard_type == 'disease' and h.alive:
                d = dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    disease_weight = 2.5
                    if f.is_boosting:
                        disease_weight = 0.3  # Can risk it
                    dx, dy = normalize_vec(f.x - h.x, f.y - h.y)
                    vectors.append((disease_weight, dx, dy))

        # ---------- cParasite ----------
        for h in self.hazards:
            if h.hazard_type == 'parasite' and h.alive:
                d = dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    dx, dy = normalize_vec(f.x - h.x, f.y - h.y)
                    vectors.append((3.0, dx, dy))

        # ---------- cRun ----------
        f.is_running = False
        for other in alive_fish:
            if other.fish_id == f.fish_id or not other.alive:
                continue
            if other.mouth_size > f.body_size:
                d = dist(f.x, f.y, other.x, other.y)
                if d < SENSITIVE_DISTANCE and d > 0.1:
                    f.is_running = True
                    run_weight = 5.0 * (SENSITIVE_DISTANCE / (d + 1))
                    dx, dy = normalize_vec(f.x - other.x, f.y - other.y)
                    vectors.append((run_weight, dx, dy))

        # ---------- cHunt ----------
        f.is_hunting = False
        if f.fullness <= 0:
            for other in alive_fish:
                if other.fish_id == f.fish_id or not other.alive:
                    continue
                if f.mouth_size > other.body_size:
                    d = dist(f.x, f.y, other.x, other.y)
                    if d < SENSITIVE_DISTANCE:
                        # Cannibal rate inversely scales with fullness (already <= 0)
                        if random.random() < 0.3:
                            f.is_hunting = True
                            hunt_weight = 3.0 * (SENSITIVE_DISTANCE / (d + 1))
                            dx, dy = normalize_vec(other.x - f.x, other.y - f.y)
                            vectors.append((hunt_weight, dx, dy))
                            break  # Hunt one target

        # ---------- cRelief ----------
        if f.has_parasite:
            sv = self._scrub_vector(f)
            if sv:
                vectors.append((4.0, sv[0], sv[1]))

        return vectors

    def _scrub_vector(self, f: Fish):
        nearest_obs = None
        nearest_dist = float('inf')
        for obs in self.obstacles:
            sx, sy = obs.nearest_surface_point(f.x, f.y)
            d = dist(f.x, f.y, sx, sy)
            if d < nearest_dist:
                nearest_dist = d
                nearest_obs = obs
        if nearest_obs:
            sx, sy = nearest_obs.nearest_surface_point(f.x, f.y)
            dx, dy = normalize_vec(sx - f.x, sy - f.y)
            return dx, dy
        return None

    def _run_vector(self, f: Fish, alive_fish: List[Fish]):
        flee_x, flee_y = 0.0, 0.0
        count = 0
        for other in alive_fish:
            if other.fish_id == f.fish_id:
                continue
            if other.mouth_size > f.body_size:
                d = dist(f.x, f.y, other.x, other.y)
                if d < SENSITIVE_DISTANCE and d > 0.1:
                    dx, dy = normalize_vec(f.x - other.x, f.y - other.y)
                    flee_x += dx / (d + 1)
                    flee_y += dy / (d + 1)
                    count += 1
        if count > 0:
            return normalize_vec(flee_x, flee_y)
        return None

    def _hunt_vector_direct(self, f: Fish, alive_fish: List[Fish]):
        nearest = None
        nearest_dist = float('inf')
        for other in alive_fish:
            if other.fish_id == f.fish_id:
                continue
            if f.mouth_size > other.body_size:
                d = dist(f.x, f.y, other.x, other.y)
                if d < SENSITIVE_DISTANCE and d < nearest_dist:
                    nearest_dist = d
                    nearest = other
        if nearest:
            dx, dy = normalize_vec(nearest.x - f.x, nearest.y - f.y)
            return dx, dy
        return None

    # ---------- CANNIBALISM ----------
    def _cannibalism_check(self):
        alive_fish = [f for f in self.fishes if f.alive]
        for f in alive_fish:
            if not f.alive or not f.is_hunting:
                continue
            for target in alive_fish:
                if target.fish_id == f.fish_id or not target.alive:
                    continue
                if f.mouth_size > target.body_size:
                    d = dist(f.x, f.y, target.x, target.y)
                    if d <= target.body_size:
                        # Cannibalism occurs
                        target.hp = 0
                        target.alive = False
                        f.fullness = min(f.max_fullness, f.fullness + target.body_size * 2)
                        f.is_hunting = False
                        break

    # ---------- FECAL DROPS ----------
    def _fecal_drops(self):
        for f in self.fishes:
            if not f.alive:
                continue
            f.fecal_timer += 1
            if f.fecal_timer >= 2 and f.fullness > 0:
                f.fecal_timer = 0
                chance = (f.fullness / f.max_fullness) * 0.3
                if random.random() < chance:
                    fecal_val = 2.0
                    # Stack nearby fecal
                    stacked = False
                    for obj in self.objects:
                        if obj.alive and obj.obj_type == 'fecal':
                            if dist(f.x, f.y, obj.x, obj.y) < 10:
                                obj.value += fecal_val
                                stacked = True
                                break
                    if not stacked:
                        self.objects.append(DynamicObject(
                            x=f.x + random.uniform(-3, 3),
                            y=f.y + random.uniform(-3, 3),
                            obj_type='fecal', value=fecal_val,
                            max_age=FECAL_EXPIRE_TIMESTEPS
                        ))

    # ---------- DEATH CHECK ----------
    def _death_check(self):
        for f in self.fishes:
            if not f.alive:
                continue
            if f.hp <= 0 or f.oxygen <= 0:
                f.alive = False
                # Spawn dead fish body
                self.objects.append(DynamicObject(
                    x=f.x, y=f.y, obj_type='dead_fish',
                    value=f.body_size, max_age=DEAD_FISH_DECAY_TIMESTEPS
                ))
                # Infected fish creates disease area
                if f.is_infected:
                    self.hazards.append(HazardArea(
                        x=f.x, y=f.y, radius=f.body_size * 1.5,
                        hazard_type='disease', max_age=DISEASE_AREA_DECAY
                    ))

    # ---------- FRAME CAPTURE ----------
    def _capture_frame(self):
        alive_fish = [f for f in self.fishes if f.alive]
        return {
            't': self.timestep,
            'day': self.timestep // 24,
            'hour': self.timestep % 24,
            'fish': [f.to_snapshot() for f in alive_fish],
            'objects': [
                {
                    'x': round(o.x, 1), 'y': round(o.y, 1),
                    'type': o.obj_type, 'value': round(o.value, 1)
                }
                for o in self.objects if o.alive
            ],
            'hazards': [
                {
                    'x': round(h.x, 1), 'y': round(h.y, 1),
                    'r': round(h.radius, 1), 'type': h.hazard_type
                }
                for h in self.hazards if h.alive
            ],
            'obstacles': [
                {
                    'x': round(o.x, 1), 'y': round(o.y, 1),
                    'w': round(o.w, 1), 'h': round(o.h, 1)
                }
                for o in self.obstacles
            ],
            'alive_count': len(alive_fish),
            'total_count': self.initial_count,
        }


# ============================================================
# EVOLUTIONARY ALGORITHM
# ============================================================

class EvolutionaryAlgorithm:
    def __init__(self, max_budget, initial_fish_population, aquaculture_days,
                 pond_generations, run_simulations, initial_pond_count=8):
        self.max_budget = max_budget
        self.initial_fish_population = initial_fish_population
        self.aquaculture_days = aquaculture_days
        self.runtime = aquaculture_days * 24
        self.pond_generations = pond_generations
        self.run_simulations = run_simulations
        self.initial_pond_count = initial_pond_count

    def run(self, record_best=True, frame_skip=4):
        all_results = []

        for sim_idx in range(self.run_simulations):
            print(f"\n{'='*60}")
            print(f"  SIMULATION {sim_idx + 1}/{self.run_simulations}")
            print(f"{'='*60}")

            # Create initial fish population (same for all ponds in this simulation)
            base_fishes = [create_fish(i) for i in range(self.initial_fish_population)]

            # Create initial pond population
            ponds = [PondGenotype.random() for _ in range(self.initial_pond_count)]

            best_result = None

            for gen in range(self.pond_generations):
                print(f"\n  Generation {gen + 1}/{self.pond_generations} | Ponds: {len(ponds)}")

                if len(ponds) <= 1 and best_result is not None:
                    break

                gen_results = []

                for p_idx, genotype in enumerate(ponds):
                    # Gatekeeper check
                    gk_cost = genotype.gatekeeper_cost()
                    if gk_cost > self.max_budget:
                        print(f"    Pond {p_idx}: REJECTED (cost ${gk_cost:.2f} > budget ${self.max_budget:.2f})")
                        gen_results.append({
                            'fitness': 0.0,
                            'genotype': genotype,
                            'survival_rate': 0,
                            'avg_condition': 0,
                            'efficiency': 0,
                            'cost': gk_cost,
                            'frames': [],
                        })
                        continue

                    # Run simulation
                    is_last_gen = (gen == self.pond_generations - 1)
                    do_record = record_best and is_last_gen and (len(ponds) <= 2)
                    sim = PondSimulation(
                        genotype=genotype,
                        fishes=base_fishes,
                        runtime=self.runtime,
                        max_budget=self.max_budget,
                        record_frames=do_record,
                        frame_skip=frame_skip
                    )
                    result = sim.run()
                    result['genotype_obj'] = genotype
                    gen_results.append(result)
                    print(f"    Pond {p_idx}: Fitness={result['fitness']:.4f} "
                          f"Survival={result['survival_rate']:.2%} "
                          f"Condition={result['avg_condition']:.3f} "
                          f"Cost=${result['cost']:.2f}")

                # Sort by fitness
                gen_results.sort(key=lambda r: r['fitness'], reverse=True)

                if gen_results:
                    best_result = gen_results[0]

                # Select top half
                half = max(1, len(gen_results) // 2)
                survivors = gen_results[:half]

                # If only 1 left, we're done
                if len(survivors) <= 1:
                    break

                # Crossover and mutation to create new pond population
                new_ponds = []
                survivor_genotypes = [r['genotype_obj'] for r in survivors if 'genotype_obj' in r]
                if not survivor_genotypes:
                    survivor_genotypes = [r.get('genotype_obj', PondGenotype.random()) for r in survivors]

                # Keep survivors
                for g in survivor_genotypes:
                    new_ponds.append(copy.deepcopy(g))

                # Fill rest with crossover + mutation
                while len(new_ponds) < len(ponds):
                    p1 = random.choice(survivor_genotypes)
                    p2 = random.choice(survivor_genotypes)
                    child = p1.crossover(p2)
                    child.mutate(rate=0.25)
                    new_ponds.append(child)

                ponds = new_ponds

            if best_result:
                best_result['simulation_idx'] = sim_idx
                all_results.append(best_result)
                print(f"\n  >> Sim {sim_idx + 1} Best: Fitness={best_result['fitness']:.4f}")

        # Select champion across all simulations
        if not all_results:
            print("No valid results!")
            return None

        all_results.sort(key=lambda r: r['fitness'], reverse=True)
        champion = all_results[0]

        print(f"\n{'='*60}")
        print(f"  CHAMPION POND (from Simulation {champion.get('simulation_idx', 0) + 1})")
        print(f"{'='*60}")
        print(f"  Fitness:       {champion['fitness']:.4f}")
        print(f"  Survival Rate: {champion['survival_rate']:.2%}")
        print(f"  Avg Condition: {champion['avg_condition']:.3f}")
        print(f"  Efficiency:    {champion['efficiency']:.3f}")
        print(f"  Total Cost:    ${champion['cost']:.2f}")
        print(f"  Genotype:      {champion['genotype']}")

        # Re-run champion with full frame recording for visualization
        if record_best and not champion.get('frames'):
            print("\n  Re-running champion with frame recording...")
            base_fishes = [create_fish(i) for i in range(self.initial_fish_population)]
            genotype = PondGenotype(**champion['genotype'])
            sim = PondSimulation(
                genotype=genotype,
                fishes=base_fishes,
                runtime=self.runtime,
                max_budget=self.max_budget,
                record_frames=True,
                frame_skip=frame_skip
            )
            result = sim.run()
            champion['frames'] = result['frames']
            champion['fitness'] = result['fitness']
            champion['survival_rate'] = result['survival_rate']
            champion['avg_condition'] = result['avg_condition']

        return champion


# ============================================================
# MAIN
# ============================================================

def main():
    print("=" * 60)
    print("  LARGEMOUTH BASS AQUACULTURE OPTIMIZER")
    print("  PSO + Evolutionary Algorithm")
    print("=" * 60)

    # --- Configuration ---
    MAX_BUDGET = 50.0
    INITIAL_FISH_POPULATION = 20
    AQUACULTURE_DAYS = 5       # Keep small for demo; increase for realism
    POND_GENERATIONS = 4
    RUN_SIMULATIONS = 2
    INITIAL_POND_COUNT = 6
    FRAME_SKIP = 2             # Record every N timesteps

    ea = EvolutionaryAlgorithm(
        max_budget=MAX_BUDGET,
        initial_fish_population=INITIAL_FISH_POPULATION,
        aquaculture_days=AQUACULTURE_DAYS,
        pond_generations=POND_GENERATIONS,
        run_simulations=RUN_SIMULATIONS,
        initial_pond_count=INITIAL_POND_COUNT,
    )

    champion = ea.run(record_best=True, frame_skip=FRAME_SKIP)

    if champion and champion.get('frames'):
        # Build visualization data
        viz_data = {
            'pond_width': POND_WIDTH,
            'pond_height': POND_HEIGHT,
            'genotype': champion['genotype'],
            'fitness': champion['fitness'],
            'survival_rate': champion['survival_rate'],
            'avg_condition': champion['avg_condition'],
            'cost': champion['cost'],
            'efficiency': champion['efficiency'],
            'initial_fish': INITIAL_FISH_POPULATION,
            'aquaculture_days': AQUACULTURE_DAYS,
            'frames': champion['frames'],
        }

        output_path = 'simulation_data.json'
        with open(output_path, 'w') as fp:
            json.dump(viz_data, fp)
        print(f"\n  Visualization data saved to {output_path}")
        print(f"  Total frames: {len(champion['frames'])}")
        print(f"\n  Open visualization.html in a browser to view the simulation.")
    else:
        print("\n  No frames recorded. Adjust parameters and try again.")


if __name__ == '__main__':
    main()