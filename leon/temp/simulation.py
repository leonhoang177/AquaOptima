#!/usr/bin/env python3
"""
Largemouth Bass Aquaculture Optimizer
PSO (fish swarm behavior) + EA (pond configuration evolution)

Run:   python simulation.py
Output: simulation_data.json  (for visualization.html)
        results.csv           (for plot.py)
"""

import random
import math
import json
import csv
import copy
import time as _time
from dataclasses import dataclass
from typing import List, Tuple
from enum import IntEnum
from concurrent.futures import ProcessPoolExecutor, as_completed
import multiprocessing

# ╔══════════════════════════════════════════════════════════════╗
# ║                    USER CONFIGURATION                       ║
# ╚══════════════════════════════════════════════════════════════╝

MAX_BUDGET = 200.0
INITIAL_FISH_POPULATION = 30
AQUACULTURE_DAYS = 20
POND_GENERATIONS = 10
RUN_TIMELINES = 3
INITIAL_POND_COUNT = 10
FRAME_SKIP = 1
NUM_WORKERS = None

# ╔══════════════════════════════════════════════════════════════╗
# ║                    ECONOMIC CONSTANTS                       ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_PRICE = 0.10
PROBIOTIC_PRICE = 0.50
OXYGEN_PRICE = 2.00

# ╔══════════════════════════════════════════════════════════════╗
# ║                  EA FITNESS WEIGHTS                         ║
# ╚══════════════════════════════════════════════════════════════╝

W1_SURVIVAL = 0.50
W2_HEALTHINESS = 0.35
W3_EFFICIENCY = 0.15

# ╔══════════════════════════════════════════════════════════════╗
# ║                    POND DIMENSIONS                          ║
# ╚══════════════════════════════════════════════════════════════╝

POND_WIDTH = 200.0
POND_HEIGHT = 75.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH TRAIT RANGES (FIXED)                   ║
# ╚══════════════════════════════════════════════════════════════╝

MOUTH_SIZE_RANGE = (3.0, 8.0)
BODY_SIZE_RANGE = (4.0, 10.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH STAT RANGES (DYNAMIC)                  ║
# ╚══════════════════════════════════════════════════════════════╝

HP_RANGE = (80.0, 120.0)
ENERGY_RANGE = (60.0, 100.0)
FULLNESS_RANGE = (50.0, 80.0)
IMMUNITY_RANGE = (70.0, 100.0)
OXYGEN_RANGE = (80.0, 100.0)
VELOCITY_RANGE = (1.0, 3.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                   PSO DISTANCE RADII                        ║
# ╚══════════════════════════════════════════════════════════════╝

SENSITIVE_DISTANCE = 40.0
SOCIAL_DISTANCE = 25.0
SELFISH_DISTANCE = 8.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                STAT DECAY RATES (PER TIMESTEP)              ║
# ╚══════════════════════════════════════════════════════════════╝

OXYGEN_DECAY = 0.05
OXYGEN_DECAY_NH3_MULT = 2.0
ENERGY_DECAY = 0.04
FULLNESS_DECAY = 0.06
ENERGY_COST_MOVE = 0.05

# ╔══════════════════════════════════════════════════════════════╗
# ║              HP DRAIN RATES (WHEN STATS DEPLETED)           ║
# ╚══════════════════════════════════════════════════════════════╝

HP_DECAY_NO_ENERGY = 0.4
HP_DECAY_NO_FULLNESS = 0.3
HP_DECAY_INFECTED = 0.6
HP_DECAY_PARASITE = 0.8

# ╔══════════════════════════════════════════════════════════════╗
# ║              DISEASE & PARASITE MECHANICS                   ║
# ╚══════════════════════════════════════════════════════════════╝

IMMUNITY_DECAY_IN_DISEASE = 1.5
PARASITE_CONTACT_CHANCE = 0.05
PARASITE_FULLNESS_EFFICIENCY = 0.5
PARASITE_EXTRA_FULLNESS_DRAIN = 1.5
PARASITE_EXTRA_ENERGY_DRAIN = 1.5
PARASITE_VELOCITY_MULT = 0.75
PARASITE_SCRUB_CHANCE = 0.15

# ╔══════════════════════════════════════════════════════════════╗
# ║              VELOCITY REDUCTION THRESHOLDS                  ║
# ╚══════════════════════════════════════════════════════════════╝

VELOCITY_HP_THRESHOLD = 0.5
VELOCITY_ENERGY_THRESHOLD = 0.5
VELOCITY_FULLNESS_THRESHOLD = 0.5

# ╔══════════════════════════════════════════════════════════════╗
# ║                 OBJECT LIFETIMES (TIMESTEPS)                ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_EXPIRE_TIMESTEPS = 48
PROBIOTIC_EXPIRE_TIMESTEPS = 18
FECAL_EXPIRE_TIMESTEPS = 36
DEAD_FISH_DECAY_TIMESTEPS = 24
NH3_EXPIRE_TIMESTEPS = 60
DISEASE_AREA_DECAY = 36           # Was 72. Diseases now fade in 1.5 days.
PARASITE_AREA_DECAY = 36          # Was 72. Parasite zones now fade in 1.5 days.
POLLUTANT_TO_HAZARD_TIMESTEPS = 48
DISEASE_AREA_RADIUS_DECAY = 0.990 # Was 0.998. Faster shrinking per timestep.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 POLLUTANT -> HAZARD CHANCES                 ║
# ╚══════════════════════════════════════════════════════════════╝

POLLUTANT_TO_DISEASE_CHANCE = 0.4
POLLUTANT_TO_PARASITE_CHANCE = 0.3
POLLUTANT_RADIUS_SCALE = 1.5
DEAD_FISH_POLLUTANT_MULT = 1.5

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FOOD & HEALING GAINS                        ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_ENERGY_GAIN = 25.0
FOOD_FULLNESS_GAIN = 20.0
FOOD_VALUE = 5.0
PROBIOTIC_VALUE = 3.0
PROBIOTIC_IMMUNITY_BOOST = 40.0
OXYGEN_BUBBLE_GAIN = 30.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 STATE DURATIONS (TIMESTEPS)                 ║
# ╚══════════════════════════════════════════════════════════════╝

BOOSTING_DURATION = 5
IMMUNITY_BOOST_DURATION = 10

# ╔══════════════════════════════════════════════════════════════╗
# ║                 NATURAL SPAWN RATES                         ║
# ╚══════════════════════════════════════════════════════════════╝

NATURAL_OXYGEN_SPAWN_RATE = 0.12
NATURAL_NH3_SPAWN_RATE = 0.005
OXYGEN_BUBBLES_PER_PUMP = 7

# ╔══════════════════════════════════════════════════════════════╗
# ║                 ENVIRONMENT OBJECTS                         ║
# ╚══════════════════════════════════════════════════════════════╝

NUM_OBSTACLES = 15
OBSTACLE_SIZE_RANGE = (8.0, 20.0)
OBSTACLE_STATIC_CHANCE = 0.6
OBSTACLE_MAX_SPEED = 0.3
OXYGEN_BUBBLE_SPEED = 0.5
NH3_AREA_RADIUS_RANGE = (8.0, 15.0)
NH3_AREA_SPEED = 0.2

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FECAL MECHANICS                             ║
# ╚══════════════════════════════════════════════════════════════╝

FECAL_DROP_INTERVAL = 2
FECAL_BASE_CHANCE = 0.2
FECAL_VALUE = 2.0
FECAL_STACK_RADIUS = 10.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 CANNIBALISM MECHANICS                       ║
# ║  Simplified: instant kill, no hunting/running states.       ║
# ╚══════════════════════════════════════════════════════════════╝

CANNIBAL_TRIGGER_CHANCE = 0.3
CANNIBAL_FULLNESS_GAIN_MULT = 2.0
CANNIBAL_COLLISION_RADIUS_MULT = 1.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 PSO VECTOR WEIGHTS                          ║
# ╚══════════════════════════════════════════════════════════════╝

PSO_INERTIA = 0.4
PSO_FOOD_WEIGHT = 2.0
PSO_FOOD_URGENT_MULT = 2.0
PSO_PROBIOTIC_WEIGHT = 1.5
PSO_OXYGEN_WEIGHT = 3.0
PSO_OXYGEN_CRITICAL_MULT = 3.0
PSO_OXYGEN_THRESHOLD = 0.7
PSO_OXYGEN_CRITICAL_THRESHOLD = 0.3
PSO_OXYGEN_INTERCEPT_STEPS = 3
PSO_SOCIAL_WEIGHT = 0.8
PSO_SELFISH_WEIGHT = 1.5
PSO_NH3_WEIGHT = 4.0
PSO_NH3_HUNGRY_OVERRIDE = 0.5
PSO_DISEASE_WEIGHT = 2.5
PSO_DISEASE_BOOSTING_WEIGHT = 0.3
PSO_PARASITE_WEIGHT = 3.0
PSO_RELIEF_WEIGHT = 4.0
PSO_RUN_WEIGHT = 5.0

STATE_OVERRIDE_PARASITE_CHANCE = 0.6

# ╔══════════════════════════════════════════════════════════════╗
# ║                 EA / MISC                                   ║
# ╚══════════════════════════════════════════════════════════════╝

EA_MUTATION_RATE = 0.25
FISH_EAT_RANGE = 3.0
INFECTED_FISH_DISEASE_RADIUS_MULT = 1.5
RESULTS_CSV_PATH = 'results.csv'

# ╔══════════════════════════════════════════════════════════════╗
# ║              OBSTACLE COLLISION                             ║
# ║  Fish bounce off obstacles with a cooldown to prevent       ║
# ║  getting stuck.                                             ║
# ╚══════════════════════════════════════════════════════════════╝

OBSTACLE_BOUNCE_FORCE = 3.0       # How far fish is pushed away from obstacle on collision.
OBSTACLE_BOUNCE_COOLDOWN = 5      # Timesteps before same obstacle can affect fish again.

# ════════════════════════════════════════════════════════════════
#  DERIVED (do not edit)
# ════════════════════════════════════════════════════════════════

RUNTIME = AQUACULTURE_DAYS * 24
LOC_NAMES = {0: 'Middle', 1: 'Corner', 2: 'Random'}

# Food policy: reduced range (was 1-10 quantity)
FOOD_QUANTITY_RANGE = (1, 5)      # Max 5 pellets per drop instead of 10.
FOOD_INTERVAL_RANGE = (2, 24)     # Min 2h between drops instead of 1h.


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
    food_quantity: int = 3
    food_location: int = 0
    probiotic_interval: int = 12
    probiotic_quantity: int = 3
    probiotic_location: int = 0
    oxygen_interval: int = 8
    oxygen_duration: int = 2
    oxygen_location: int = 0

    def total_cost(self, runtime: int) -> float:
        fc = (runtime / self.food_interval) * self.food_quantity * FOOD_PRICE
        pc = (runtime / self.probiotic_interval) * self.probiotic_quantity * PROBIOTIC_PRICE
        oc = (runtime / self.oxygen_interval) * self.oxygen_duration * OXYGEN_PRICE
        return fc + pc + oc

    def per_cycle_cost(self) -> float:
        return (self.food_quantity * FOOD_PRICE +
                self.probiotic_quantity * PROBIOTIC_PRICE +
                self.oxygen_duration * OXYGEN_PRICE)

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in [
            'food_interval', 'food_quantity', 'food_location',
            'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
            'oxygen_interval', 'oxygen_duration', 'oxygen_location']}

    @staticmethod
    def random() -> 'PondGenotype':
        return PondGenotype(
            food_interval=random.randint(*FOOD_INTERVAL_RANGE),
            food_quantity=random.randint(*FOOD_QUANTITY_RANGE),
            food_location=random.randint(0, 2),
            probiotic_interval=random.randint(1, 24),
            probiotic_quantity=random.randint(1, 10),
            probiotic_location=random.randint(0, 2),
            oxygen_interval=random.randint(1, 24),
            oxygen_duration=random.randint(1, 4),
            oxygen_location=random.randint(0, 2))

    def crossover(self, other: 'PondGenotype') -> 'PondGenotype':
        child = PondGenotype()
        for attr in self.to_dict():
            setattr(child, attr, getattr(self if random.random() < 0.5 else other, attr))
        return child

    def mutate(self):
        r = EA_MUTATION_RATE
        if random.random() < r: self.food_interval = random.randint(*FOOD_INTERVAL_RANGE)
        if random.random() < r: self.food_quantity = random.randint(*FOOD_QUANTITY_RANGE)
        if random.random() < r: self.food_location = random.randint(0, 2)
        if random.random() < r: self.probiotic_interval = random.randint(1, 24)
        if random.random() < r: self.probiotic_quantity = random.randint(1, 10)
        if random.random() < r: self.probiotic_location = random.randint(0, 2)
        if random.random() < r: self.oxygen_interval = random.randint(1, 24)
        if random.random() < r: self.oxygen_duration = random.randint(1, 4)
        if random.random() < r: self.oxygen_location = random.randint(0, 2)


@dataclass
class Obstacle:
    x: float; y: float; w: float; h: float
    is_static: bool = True; vx: float = 0.0; vy: float = 0.0

    def contains(self, px, py) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def nearest_surface(self, px, py) -> Tuple[float, float]:
        return max(self.x, min(px, self.x + self.w)), max(self.y, min(py, self.y + self.h))

    def center(self) -> Tuple[float, float]:
        return self.x + self.w / 2, self.y + self.h / 2


@dataclass
class DynObj:
    x: float; y: float; kind: str; value: float = 5.0
    age: int = 0; max_age: int = 30; vx: float = 0.0; vy: float = 0.0; alive: bool = True


@dataclass
class Hazard:
    x: float; y: float; radius: float; kind: str
    age: int = 0; max_age: int = 50; alive: bool = True; vx: float = 0.0; vy: float = 0.0

    def contains(self, px, py) -> bool:
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= self.radius ** 2


@dataclass
class Fish:
    fid: int = 0; x: float = 0.0; y: float = 0.0; vx: float = 0.0; vy: float = 0.0
    mouth_size: float = 5.0; body_size: float = 6.0
    hp: float = 100.0; max_hp: float = 100.0
    energy: float = 80.0; max_energy: float = 80.0
    fullness: float = 60.0; max_fullness: float = 60.0
    immunity: float = 80.0; max_immunity: float = 80.0
    oxygen: float = 90.0; max_oxygen: float = 90.0
    base_velocity: float = 2.0
    is_boosting: bool = False; boost_timer: int = 0
    is_infected: bool = False; has_parasite: bool = False
    alive: bool = True; fecal_timer: int = 0
    obstacle_cooldown: int = 0  # Prevents getting stuck on obstacles

    def eff_vel(self) -> float:
        v = self.base_velocity
        if self.hp <= self.max_hp * VELOCITY_HP_THRESHOLD: v *= 0.5
        if self.energy <= self.max_energy * VELOCITY_ENERGY_THRESHOLD: v *= 0.5
        if self.fullness <= self.max_fullness * VELOCITY_FULLNESS_THRESHOLD: v *= 0.5
        if self.has_parasite: v *= PARASITE_VELOCITY_MULT
        return v

    def norm_stats(self) -> float:
        hp_n = max(0, self.hp) / self.max_hp
        en_n = max(0, self.energy) / self.max_energy
        fu_n = max(0, self.fullness) / self.max_fullness
        im_n = max(0, self.immunity) / self.max_immunity
        vl_n = min(1.0, self.eff_vel() / (self.base_velocity + 1e-9))
        return (hp_n + en_n + fu_n + im_n + vl_n) / 5.0

    def snapshot(self) -> dict:
        return {'id': self.fid, 'x': round(self.x, 1), 'y': round(self.y, 1),
                'hp': round(self.hp, 1), 'max_hp': round(self.max_hp, 1),
                'energy': round(self.energy, 1), 'fullness': round(self.fullness, 1),
                'immunity': round(self.immunity, 1), 'oxygen': round(self.oxygen, 1),
                'alive': self.alive,
                'is_infected': self.is_infected, 'has_parasite': self.has_parasite,
                'is_boosting': self.is_boosting,
                'body_size': round(self.body_size, 1), 'mouth_size': round(self.mouth_size, 1)}


# ============================================================
# HELPERS
# ============================================================

def _dist(x1, y1, x2, y2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def _clamp(v, lo, hi):
    return max(lo, min(hi, v))

def _norm(vx, vy):
    m = math.sqrt(vx * vx + vy * vy)
    return (vx / m, vy / m) if m > 1e-8 else (0.0, 0.0)

def _drop_pos(loc: int):
    if loc == DropLocation.MIDDLE:
        return POND_WIDTH / 2 + random.uniform(-15, 15), POND_HEIGHT / 2 + random.uniform(-10, 10)
    elif loc == DropLocation.CORNER:
        cx, cy = random.choice([(15, 15), (POND_WIDTH - 15, 15),
                                 (15, POND_HEIGHT - 15), (POND_WIDTH - 15, POND_HEIGHT - 15)])
        return cx + random.uniform(-8, 8), cy + random.uniform(-5, 5)
    return random.uniform(10, POND_WIDTH - 10), random.uniform(5, POND_HEIGHT - 5)

def _make_fish(fid: int) -> Fish:
    f = Fish(fid=fid)
    f.x = random.uniform(15, POND_WIDTH - 15); f.y = random.uniform(10, POND_HEIGHT - 10)
    f.mouth_size = random.uniform(*MOUTH_SIZE_RANGE); f.body_size = random.uniform(*BODY_SIZE_RANGE)
    f.max_hp = random.uniform(*HP_RANGE); f.hp = f.max_hp
    f.max_energy = random.uniform(*ENERGY_RANGE); f.energy = f.max_energy
    f.max_fullness = random.uniform(*FULLNESS_RANGE); f.fullness = f.max_fullness * 0.8
    f.max_immunity = random.uniform(*IMMUNITY_RANGE); f.immunity = f.max_immunity
    f.max_oxygen = random.uniform(*OXYGEN_RANGE); f.oxygen = f.max_oxygen
    f.base_velocity = random.uniform(*VELOCITY_RANGE)
    f.vx = random.uniform(-1, 1); f.vy = random.uniform(-1, 1)
    return f

FISH_DICT_KEYS = [
    'fid', 'x', 'y', 'vx', 'vy', 'mouth_size', 'body_size',
    'hp', 'max_hp', 'energy', 'max_energy', 'fullness', 'max_fullness',
    'immunity', 'max_immunity', 'oxygen', 'max_oxygen', 'base_velocity',
    'is_boosting', 'boost_timer', 'is_infected', 'has_parasite',
    'alive', 'fecal_timer', 'obstacle_cooldown']

def _fish_to_dict(f: Fish) -> dict:
    return {s: getattr(f, s) for s in FISH_DICT_KEYS}

def _dict_to_fish(d: dict) -> Fish:
    f = Fish()
    for k, v in d.items():
        if hasattr(f, k): setattr(f, k, v)
    return f


# ============================================================
# PRINTING HELPERS
# ============================================================

def _print_gen_table(gen, max_gen, n_ponds, gen_results):
    print(f"\n  Gen {gen+1:>2}/{max_gen} | {n_ponds} ponds")
    print(f"  +-----+----------+-----------+-------------+--------------+------------+")
    print(f"  |  #  | Fitness  | Survival  | Healthiness |     Cost     |   Status   |")
    print(f"  +-----+----------+-----------+-------------+--------------+------------+")
    for i, r in enumerate(gen_results):
        st = r.get('status', '?')
        if st == 'GATEKEEPER':    st_s = 'GATE'
        elif st == 'OVER-BUDGET': st_s = 'OVER$'
        elif st == 'ALL-DEAD':    st_s = 'DEAD'
        else:                     st_s = 'OK'
        print(f"  | {i:>3} | {r['fitness']:>8.4f} | {r['survival_rate']*100:>8.2f}% | "
              f"{r.get('avg_healthiness',0):>11.4f} | ${r['cost']:>10.2f} | {st_s:>10} |")
    print(f"  +-----+----------+-----------+-------------+--------------+------------+")


def _print_champion_detail(label: str, result: dict):
    g = result.get('genotype', {})
    fit = result.get('fitness', 0)
    sr = result.get('survival_rate', 0)
    hlth = result.get('avg_healthiness', 0)
    eff = result.get('efficiency', 0)
    cost = result.get('cost', 0)
    ac = result.get('alive_count', 0)
    ic = result.get('initial_count', 0)
    W = 56; LW = 24; RW = W - LW - 3
    print(f"\n  +{'-' * W}+")
    print(f"  | {label:^{W-2}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")
    print(f"  | {'Metric':<{LW-2}} | {'Value':>{RW}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")
    print(f"  | {'Fitness':<{LW-2}} | {fit:>{RW}.4f} |")
    print(f"  | {'Survival Rate':<{LW-2}} | {sr*100:>{RW-1}.2f}% |")
    print(f"  | {'Healthiness':<{LW-2}} | {hlth:>{RW}.4f} |")
    print(f"  | {'Efficiency':<{LW-2}} | {eff:>{RW}.4f} |")
    print(f"  | {'Cost':<{LW-2}} | {'${:.2f}'.format(cost):>{RW}} |")
    print(f"  | {'Alive / Initial':<{LW-2}} | {'{} / {}'.format(ac, ic):>{RW}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")
    print(f"  | {'Food Interval':<{LW-2}} | {'{} h'.format(g.get('food_interval','?')):>{RW}} |")
    print(f"  | {'Food Quantity':<{LW-2}} | {'{} pellets'.format(g.get('food_quantity','?')):>{RW}} |")
    print(f"  | {'Food Location':<{LW-2}} | {LOC_NAMES.get(g.get('food_location',-1),'?'):>{RW}} |")
    print(f"  | {'Probiotic Interval':<{LW-2}} | {'{} h'.format(g.get('probiotic_interval','?')):>{RW}} |")
    print(f"  | {'Probiotic Quantity':<{LW-2}} | {'{} pellets'.format(g.get('probiotic_quantity','?')):>{RW}} |")
    print(f"  | {'Probiotic Location':<{LW-2}} | {LOC_NAMES.get(g.get('probiotic_location',-1),'?'):>{RW}} |")
    print(f"  | {'O2 Interval':<{LW-2}} | {'{} h'.format(g.get('oxygen_interval','?')):>{RW}} |")
    print(f"  | {'O2 Duration':<{LW-2}} | {'{} h'.format(g.get('oxygen_duration','?')):>{RW}} |")
    print(f"  | {'O2 Location':<{LW-2}} | {LOC_NAMES.get(g.get('oxygen_location',-1),'?'):>{RW}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")


def _print_champions_summary(champions: list) -> int:
    print(f"\n  +{'=' * 80}+")
    print(f"  | {'ALL TIMELINE CHAMPIONS -- SUMMARY':^78} |")
    print(f"  +{'-' * 12}+{'-' * 10}+{'-' * 11}+{'-' * 13}+{'-' * 14}+{'-' * 14}+")
    print(f"  | {'Timeline':>10} | {'Fitness':>8} | {'Survival':>9} | {'Healthiness':>11} | {'Cost':>12} | {'Efficiency':>12} |")
    print(f"  +{'-' * 12}+{'-' * 10}+{'-' * 11}+{'-' * 13}+{'-' * 14}+{'-' * 14}+")
    best_idx = 0; best_fit = -1.0
    for i, c in enumerate(champions):
        tl = c.get('timeline_idx', i) + 1
        fit = c.get('fitness', 0); sr = c.get('survival_rate', 0)
        hlth = c.get('avg_healthiness', 0); cost = c.get('cost', 0); eff = c.get('efficiency', 0)
        if fit > best_fit: best_fit = fit; best_idx = i
        print(f"  | {tl:>10} | {fit:>8.4f} | {sr*100:>8.2f}% | {hlth:>11.4f} | ${cost:>11.2f} | {eff:>12.4f} |")
    print(f"  +{'-' * 12}+{'-' * 10}+{'-' * 11}+{'-' * 13}+{'-' * 14}+{'-' * 14}+")
    winner = champions[best_idx]
    print(f"\n  >>> Best overall: Timeline {winner.get('timeline_idx', best_idx) + 1} with Fitness = {winner['fitness']:.4f}")
    return best_idx


# ============================================================
# POND SIMULATION ENGINE
# ============================================================

class PondSim:
    __slots__ = ('geno', 'runtime', 'max_budget', 'record', 'fskip',
                 'fish', 'n0', 'ts', 'objs', 'hazards', 'obstacles',
                 'oxy_pump', 'frames', 'accum_cost', 'budget_exceeded',
                 'cannibal_events')

    def __init__(self, geno, fish_templates, runtime, max_budget, record=False, fskip=1):
        self.geno = geno; self.runtime = runtime; self.max_budget = max_budget
        self.record = record; self.fskip = fskip
        self.fish = copy.deepcopy(fish_templates); self.n0 = len(self.fish)
        self.ts = 0; self.objs = []; self.hazards = []; self.obstacles = []
        self.oxy_pump = 0; self.frames = []; self.accum_cost = 0.0
        self.budget_exceeded = False; self.cannibal_events = []
        self._make_obs()

    def _make_obs(self):
        for _ in range(NUM_OBSTACLES):
            w = random.uniform(*OBSTACLE_SIZE_RANGE)
            h = random.uniform(OBSTACLE_SIZE_RANGE[0] * 0.3, OBSTACLE_SIZE_RANGE[1] * 0.5)
            x = random.uniform(5, POND_WIDTH - 5 - w)
            y = random.uniform(3, POND_HEIGHT - 3 - h)
            s = random.random() < OBSTACLE_STATIC_CHANCE
            vx = random.uniform(-OBSTACLE_MAX_SPEED, OBSTACLE_MAX_SPEED) if not s else 0
            vy = random.uniform(-OBSTACLE_MAX_SPEED * 0.5, OBSTACLE_MAX_SPEED * 0.5) if not s else 0
            self.obstacles.append(Obstacle(x, y, w, h, s, vx, vy))

    def _cp(self, x, y):
        return _clamp(x, 2, POND_WIDTH - 2), _clamp(y, 2, POND_HEIGHT - 2)

    def run(self):
        for t in range(self.runtime):
            self.ts = t
            self.cannibal_events = []
            self._step()
            if self.record and t % self.fskip == 0:
                self.frames.append(self._frame())
            if self.budget_exceeded: break
            if not any(f.alive for f in self.fish): break
        alive = [f for f in self.fish if f.alive]
        sr = len(alive) / self.n0 if self.n0 else 0
        hlth = sum(f.norm_stats() for f in alive) / len(alive) if alive else 0
        cost = self.accum_cost
        eff = max(0, (self.max_budget - cost) / self.max_budget) if not self.budget_exceeded else 0
        fit = (W1_SURVIVAL * sr + W2_HEALTHINESS * hlth + W3_EFFICIENCY * eff) if not self.budget_exceeded else 0
        return {'survival_rate': sr, 'avg_healthiness': hlth, 'efficiency': eff,
                'fitness': fit, 'cost': cost, 'alive_count': len(alive),
                'initial_count': self.n0, 'frames': self.frames,
                'genotype': self.geno.to_dict(), 'budget_exceeded': self.budget_exceeded}

    def _step(self):
        t = self.ts
        self._spawn_food(t); self._spawn_prob(t); self._pump_oxy(t); self._nat_spawn()
        self._upd_objs(); self._upd_haz(); self._upd_obs()
        self._decay(); self._eat(); self._pso(); self._cannibal(); self._fecal(); self._death()

    def _add_cost(self, a):
        self.accum_cost += a
        if self.accum_cost > self.max_budget: self.budget_exceeded = True

    def _spawn_food(self, t):
        if t % self.geno.food_interval == 0:
            self._add_cost(self.geno.food_quantity * FOOD_PRICE)
            if self.budget_exceeded: return
            for _ in range(self.geno.food_quantity):
                x, y = _drop_pos(self.geno.food_location)
                self.objs.append(DynObj(x, y, 'food', FOOD_VALUE, max_age=FOOD_EXPIRE_TIMESTEPS))

    def _spawn_prob(self, t):
        if t % self.geno.probiotic_interval == 0:
            self._add_cost(self.geno.probiotic_quantity * PROBIOTIC_PRICE)
            if self.budget_exceeded: return
            for _ in range(self.geno.probiotic_quantity):
                x, y = _drop_pos(self.geno.probiotic_location)
                self.objs.append(DynObj(x, y, 'probiotic', PROBIOTIC_VALUE, max_age=PROBIOTIC_EXPIRE_TIMESTEPS))

    def _pump_oxy(self, t):
        if t % self.geno.oxygen_interval == 0: self.oxy_pump = self.geno.oxygen_duration
        if self.oxy_pump > 0:
            self._add_cost(OXYGEN_PRICE)
            if self.budget_exceeded: return
            for _ in range(OXYGEN_BUBBLES_PER_PUMP):
                x, y = _drop_pos(self.geno.oxygen_location)
                self.objs.append(DynObj(x, y, 'oxygen', 1.0, max_age=99999,
                    vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                    vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED)))
            self.oxy_pump -= 1

    def _nat_spawn(self):
        if random.random() < NATURAL_OXYGEN_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH-10), random.uniform(5, POND_HEIGHT-5)
            self.objs.append(DynObj(x, y, 'oxygen', 1.0, max_age=99999,
                vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED)))
        if random.random() < NATURAL_NH3_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH-10), random.uniform(5, POND_HEIGHT-5)
            self.hazards.append(Hazard(x, y, random.uniform(*NH3_AREA_RADIUS_RANGE), 'nh3',
                max_age=NH3_EXPIRE_TIMESTEPS, vx=random.uniform(-NH3_AREA_SPEED, NH3_AREA_SPEED),
                vy=random.uniform(-NH3_AREA_SPEED, NH3_AREA_SPEED)))

    def _upd_objs(self):
        keep = []
        for o in self.objs:
            o.age += 1
            if o.kind == 'oxygen':
                o.x += o.vx; o.y += o.vy
                if o.x < 2 or o.x > POND_WIDTH-2: o.vx *= -1
                if o.y < 2 or o.y > POND_HEIGHT-2: o.vy *= -1
                o.x, o.y = self._cp(o.x, o.y)
                if any(h.contains(o.x, o.y) and h.kind == 'nh3' and h.alive for h in self.hazards): continue
                keep.append(o); continue
            if o.age >= o.max_age and o.alive:
                if o.kind in ('food', 'probiotic', 'fecal', 'dead_fish'):
                    if o.value > 0:
                        pv = o.value * (DEAD_FISH_POLLUTANT_MULT if o.kind == 'dead_fish' else 1.0)
                        if not any(h.contains(o.x, o.y) and h.kind == 'nh3' and h.alive for h in self.hazards):
                            keep.append(DynObj(o.x, o.y, 'pollutant', pv, max_age=POLLUTANT_TO_HAZARD_TIMESTEPS))
                    continue
                elif o.kind == 'pollutant':
                    r = o.value * POLLUTANT_RADIUS_SCALE
                    if random.random() < POLLUTANT_TO_DISEASE_CHANCE:
                        self.hazards.append(Hazard(o.x, o.y, r, 'disease', max_age=DISEASE_AREA_DECAY))
                    if random.random() < POLLUTANT_TO_PARASITE_CHANCE:
                        self.hazards.append(Hazard(o.x, o.y, r, 'parasite', max_age=PARASITE_AREA_DECAY))
                    continue
            if o.alive: keep.append(o)
        self.objs = keep

    def _upd_haz(self):
        keep = []
        for h in self.hazards:
            h.age += 1
            if h.kind == 'nh3':
                h.x += h.vx; h.y += h.vy
                if h.x < 5 or h.x > POND_WIDTH-5: h.vx *= -1
                if h.y < 3 or h.y > POND_HEIGHT-3: h.vy *= -1
                h.x = _clamp(h.x, 5, POND_WIDTH-5); h.y = _clamp(h.y, 3, POND_HEIGHT-3)
            if h.age >= h.max_age:
                if h.kind == 'nh3':
                    self.objs.append(DynObj(h.x, h.y, 'pollutant', h.radius*0.5, max_age=POLLUTANT_TO_HAZARD_TIMESTEPS))
                continue
            if h.kind in ('disease', 'parasite'):
                h.radius = max(0.5, h.radius * DISEASE_AREA_RADIUS_DECAY)
            keep.append(h)
        self.hazards = keep

    def _upd_obs(self):
        for o in self.obstacles:
            if not o.is_static:
                o.x += o.vx; o.y += o.vy
                if o.x < 2 or o.x + o.w > POND_WIDTH-2: o.vx *= -1
                if o.y < 2 or o.y + o.h > POND_HEIGHT-2: o.vy *= -1
                o.x = _clamp(o.x, 2, POND_WIDTH-2-o.w); o.y = _clamp(o.y, 2, POND_HEIGHT-2-o.h)

    def _decay(self):
        for f in self.fish:
            if not f.alive: continue
            if f.obstacle_cooldown > 0: f.obstacle_cooldown -= 1
            f.oxygen -= OXYGEN_DECAY
            for h in self.hazards:
                if h.kind == 'nh3' and h.contains(f.x, f.y): f.oxygen -= OXYGEN_DECAY * OXYGEN_DECAY_NH3_MULT
            ec = ENERGY_DECAY
            if f.has_parasite: ec *= PARASITE_EXTRA_ENERGY_DRAIN
            f.energy -= ec
            fd = FULLNESS_DECAY
            if f.has_parasite: fd *= PARASITE_EXTRA_FULLNESS_DRAIN
            f.fullness -= fd
            if f.energy <= 0: f.hp -= HP_DECAY_NO_ENERGY
            if f.fullness <= 0: f.hp -= HP_DECAY_NO_FULLNESS
            if f.is_infected: f.hp -= HP_DECAY_INFECTED
            if f.has_parasite and self.ts % 3 == 0: f.hp -= HP_DECAY_PARASITE
            if f.is_boosting:
                f.boost_timer -= 1
                if f.boost_timer <= 0: f.is_boosting = False
            for h in self.hazards:
                if h.kind == 'disease' and h.contains(f.x, f.y):
                    f.immunity -= IMMUNITY_DECAY_IN_DISEASE
                    if f.immunity <= 0: f.is_infected = True; f.immunity = 0
                if h.kind == 'parasite' and h.contains(f.x, f.y):
                    if random.random() < PARASITE_CONTACT_CHANCE: f.has_parasite = True

    def _eat(self):
        for f in self.fish:
            if not f.alive: continue
            for o in self.objs:
                if not o.alive or o.value <= 0: continue
                if _dist(f.x, f.y, o.x, o.y) > f.body_size + FISH_EAT_RANGE: continue
                if o.kind == 'food' and f.fullness < f.max_fullness:
                    o.value -= 1
                    g = FOOD_FULLNESS_GAIN * (PARASITE_FULLNESS_EFFICIENCY if f.has_parasite else 1.0)
                    f.fullness = min(f.max_fullness, f.fullness + g)
                    f.energy = min(f.max_energy, f.energy + FOOD_ENERGY_GAIN)
                    if o.value <= 0: o.alive = False
                elif o.kind == 'probiotic' and not f.is_boosting:
                    o.value -= 1
                    f.immunity = min(f.max_immunity, f.immunity + PROBIOTIC_IMMUNITY_BOOST)
                    f.is_boosting = True; f.boost_timer = BOOSTING_DURATION
                    if o.value <= 0: o.alive = False
                elif o.kind == 'oxygen':
                    f.oxygen = min(f.max_oxygen, f.oxygen + OXYGEN_BUBBLE_GAIN); o.alive = False

    def _pso(self):
        alive = [f for f in self.fish if f.alive]
        if not alive: return
        for f in alive:
            vel = f.eff_vel(); nvx = PSO_INERTIA * f.vx; nvy = PSO_INERTIA * f.vy
            for w, dx, dy in self._vecs(f, alive): nvx += w * dx; nvy += w * dy
            m = math.sqrt(nvx**2 + nvy**2)
            if m > 0.01: nvx = nvx/m*vel; nvy = nvy/m*vel

            # Parasite scrubbing override
            if f.has_parasite and random.random() < STATE_OVERRIDE_PARASITE_CHANCE:
                sv = self._scrub(f)
                if sv: nvx, nvy = sv[0]*vel, sv[1]*vel

            f.vx, f.vy = nvx, nvy
            nx, ny = f.x + f.vx, f.y + f.vy

            # Obstacle collision with bounce and cooldown
            collided = False
            for obs in self.obstacles:
                if obs.contains(nx, ny):
                    collided = True
                    if f.obstacle_cooldown <= 0:
                        # Push away from obstacle center
                        ocx, ocy = obs.center()
                        dx, dy = _norm(f.x - ocx, f.y - ocy)
                        # Add randomness to prevent getting stuck
                        dx += random.uniform(-0.3, 0.3)
                        dy += random.uniform(-0.3, 0.3)
                        dx, dy = _norm(dx, dy)
                        nx = f.x + dx * OBSTACLE_BOUNCE_FORCE
                        ny = f.y + dy * OBSTACLE_BOUNCE_FORCE
                        f.vx = dx * vel * 0.5
                        f.vy = dy * vel * 0.5
                        f.obstacle_cooldown = OBSTACLE_BOUNCE_COOLDOWN
                        if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                            f.has_parasite = False
                    else:
                        # During cooldown, just slide along
                        sx, sy = obs.nearest_surface(f.x, f.y)
                        dx, dy = _norm(f.x - sx, f.y - sy)
                        nx = f.x + dx * 1.5
                        ny = f.y + dy * 1.5
                    break

            # Wall bounce
            if nx < 3 or nx > POND_WIDTH - 3:
                f.vx *= -0.5; nx = _clamp(nx, 3, POND_WIDTH - 3)
            if ny < 3 or ny > POND_HEIGHT - 3:
                f.vy *= -0.5; ny = _clamp(ny, 3, POND_HEIGHT - 3)

            f.x, f.y = self._cp(nx, ny)
            mc = ENERGY_COST_MOVE * vel
            if f.has_parasite: mc *= PARASITE_EXTRA_ENERGY_DRAIN
            f.energy -= mc

    def _vecs(self, f, alive):
        vecs = []; fr = max(0, f.fullness) / f.max_fullness
        # cFood
        if fr < 1.0:
            fw = PSO_FOOD_WEIGHT * (1.0 - fr)
            if max(0, f.energy)/f.max_energy < 0.3: fw *= PSO_FOOD_URGENT_MULT
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'food' and o.value > 0:
                    d = _dist(f.x, f.y, o.x, o.y)
                    if d < SENSITIVE_DISTANCE and d < nd: nd, no = d, o
            if no: dx, dy = _norm(no.x-f.x, no.y-f.y); vecs.append((fw, dx, dy))
        # cProbiotic
        if not f.is_boosting:
            ir = max(0, f.immunity)/f.max_immunity; pw = PSO_PROBIOTIC_WEIGHT*(1.0-ir)
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'probiotic' and o.value > 0:
                    d = _dist(f.x, f.y, o.x, o.y)
                    if d < SENSITIVE_DISTANCE and d < nd: nd, no = d, o
            if no: dx, dy = _norm(no.x-f.x, no.y-f.y); vecs.append((pw, dx, dy))
        # cOxygen
        orr = max(0, f.oxygen)/f.max_oxygen
        if orr < PSO_OXYGEN_THRESHOLD:
            ow = PSO_OXYGEN_WEIGHT*(1.0-orr)
            if orr < PSO_OXYGEN_CRITICAL_THRESHOLD: ow *= PSO_OXYGEN_CRITICAL_MULT
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'oxygen':
                    fx2 = o.x+o.vx*PSO_OXYGEN_INTERCEPT_STEPS; fy2 = o.y+o.vy*PSO_OXYGEN_INTERCEPT_STEPS
                    d = min(_dist(f.x, f.y, o.x, o.y), _dist(f.x, f.y, fx2, fy2))
                    if d < SENSITIVE_DISTANCE and d < nd: nd, no = d, o
            if no:
                tx = no.x+no.vx*PSO_OXYGEN_INTERCEPT_STEPS; ty = no.y+no.vy*PSO_OXYGEN_INTERCEPT_STEPS
                dx, dy = _norm(tx-f.x, ty-f.y); vecs.append((ow, dx, dy))
        # cSocial & cSelfish
        svx, svy, sc = 0, 0, 0; rvx, rvy, rc = 0, 0, 0
        for o in alive:
            if o.fid == f.fid: continue
            d = _dist(f.x, f.y, o.x, o.y)
            if d < SELFISH_DISTANCE and d > 0.1:
                dx, dy = _norm(f.x-o.x, f.y-o.y); rvx += dx/d; rvy += dy/d; rc += 1
            elif d < SOCIAL_DISTANCE: svx += o.x-f.x; svy += o.y-f.y; sc += 1
        if sc > 0: dx, dy = _norm(svx/sc, svy/sc); vecs.append((PSO_SOCIAL_WEIGHT, dx, dy))
        if rc > 0: dx, dy = _norm(rvx, rvy); vecs.append((PSO_SELFISH_WEIGHT, dx, dy))
        # cNH3
        for h in self.hazards:
            if h.kind == 'nh3':
                d = _dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE*0.5:
                    w = PSO_NH3_WEIGHT
                    if fr < 0.1 and any(o.alive and o.kind == 'food' and h.contains(o.x, o.y) for o in self.objs):
                        w = PSO_NH3_HUNGRY_OVERRIDE
                    dx, dy = _norm(f.x-h.x, f.y-h.y); vecs.append((w, dx, dy))
        # cDisease
        for h in self.hazards:
            if h.kind == 'disease':
                d = _dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE*0.5:
                    w = PSO_DISEASE_BOOSTING_WEIGHT if f.is_boosting else PSO_DISEASE_WEIGHT
                    dx, dy = _norm(f.x-h.x, f.y-h.y); vecs.append((w, dx, dy))
        # cParasite
        for h in self.hazards:
            if h.kind == 'parasite':
                d = _dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE*0.5:
                    dx, dy = _norm(f.x-h.x, f.y-h.y); vecs.append((PSO_PARASITE_WEIGHT, dx, dy))
        # cRun (simplified: just flee from bigger fish, no state change)
        for o in alive:
            if o.fid == f.fid: continue
            if o.mouth_size > f.body_size:
                d = _dist(f.x, f.y, o.x, o.y)
                if 0.1 < d < SENSITIVE_DISTANCE:
                    w = PSO_RUN_WEIGHT*(SENSITIVE_DISTANCE/(d+1))
                    dx, dy = _norm(f.x-o.x, f.y-o.y); vecs.append((w, dx, dy))
        # cRelief
        if f.has_parasite:
            sv = self._scrub(f)
            if sv: vecs.append((PSO_RELIEF_WEIGHT, sv[0], sv[1]))
        return vecs

    def _scrub(self, f):
        bd, bo = float('inf'), None
        for o in self.obstacles:
            sx, sy = o.nearest_surface(f.x, f.y); d = _dist(f.x, f.y, sx, sy)
            if d < bd: bd, bo = d, o
        if bo:
            sx, sy = bo.nearest_surface(f.x, f.y)
            return _norm(sx-f.x, sy-f.y)
        return None

    # Simplified cannibalism: instant kill, no hunting/running states
    def _cannibal(self):
        alive = [f for f in self.fish if f.alive]
        for f in alive:
            if not f.alive or f.fullness > 0: continue
            if random.random() > CANNIBAL_TRIGGER_CHANCE: continue
            for t in alive:
                if t.fid == f.fid or not t.alive: continue
                if f.mouth_size > t.body_size:
                    d = _dist(f.x, f.y, t.x, t.y)
                    if d <= t.body_size * CANNIBAL_COLLISION_RADIUS_MULT:
                        t.hp = 0; t.alive = False
                        f.fullness = min(f.max_fullness, f.fullness + t.body_size * CANNIBAL_FULLNESS_GAIN_MULT)
                        self.cannibal_events.append({'x': t.x, 'y': t.y, 'predator': f.fid, 'prey': t.fid})
                        break

    def _fecal(self):
        for f in self.fish:
            if not f.alive: continue
            f.fecal_timer += 1
            if f.fecal_timer >= FECAL_DROP_INTERVAL and f.fullness > 0:
                f.fecal_timer = 0
                if random.random() < (f.fullness/f.max_fullness)*FECAL_BASE_CHANCE:
                    stacked = False
                    for o in self.objs:
                        if o.alive and o.kind == 'fecal' and _dist(f.x, f.y, o.x, o.y) < FECAL_STACK_RADIUS:
                            o.value += FECAL_VALUE; stacked = True; break
                    if not stacked:
                        self.objs.append(DynObj(f.x+random.uniform(-3,3), f.y+random.uniform(-2,2),
                            'fecal', FECAL_VALUE, max_age=FECAL_EXPIRE_TIMESTEPS))

    def _death(self):
        for f in self.fish:
            if not f.alive: continue
            if f.hp <= 0 or f.oxygen <= 0:
                f.alive = False
                self.objs.append(DynObj(f.x, f.y, 'dead_fish', f.body_size, max_age=DEAD_FISH_DECAY_TIMESTEPS))
                if f.is_infected:
                    self.hazards.append(Hazard(f.x, f.y, f.body_size*INFECTED_FISH_DISEASE_RADIUS_MULT,
                        'disease', max_age=DISEASE_AREA_DECAY))

    def _frame(self):
        alive = [f for f in self.fish if f.alive]
        return {
            't': self.ts, 'day': self.ts//24, 'hour': self.ts%24,
            'fish': [f.snapshot() for f in alive],
            'objects': [{'x': round(o.x,1), 'y': round(o.y,1), 'type': o.kind,
                         'value': round(o.value,1)} for o in self.objs if o.alive],
            'hazards': [{'x': round(h.x,1), 'y': round(h.y,1), 'r': round(h.radius,1),
                         'type': h.kind} for h in self.hazards],
            'obstacles': [{'x': round(o.x,1), 'y': round(o.y,1), 'w': round(o.w,1),
                           'h': round(o.h,1)} for o in self.obstacles],
            'alive_count': len(alive), 'total_count': self.n0,
            'cannibal_events': list(self.cannibal_events)}


# ============================================================
# WORKER FUNCTIONS (must be top-level for pickling)
# ============================================================

def _run_pond_worker(args):
    geno_dict, fish_data, runtime, max_budget, do_record, fskip, seed = args
    random.seed(seed)
    geno = PondGenotype(**geno_dict)
    fishes = [_dict_to_fish(fd) for fd in fish_data]
    sim = PondSim(geno, fishes, runtime, max_budget, record=do_record, fskip=fskip)
    result = sim.run()
    result['genotype_obj_dict'] = geno_dict
    return result


def _run_timeline_worker(args):
    """Run an entire timeline (EA loop) as a single worker process."""
    tl_idx, fish_data, runtime, max_budget, pond_generations, \
        initial_pond_count, record_best, frame_skip, seed = args
    random.seed(seed)

    ponds = [PondGenotype.random() for _ in range(initial_pond_count)]
    best_result = None
    csv_rows = []

    for gen in range(pond_generations):
        if len(ponds) <= 1 and best_result is not None:
            break

        is_last = (gen == pond_generations - 1)
        do_rec = record_best and is_last and len(ponds) <= 4

        gen_results = []
        for p_idx, geno in enumerate(ponds):
            if geno.per_cycle_cost() > max_budget:
                r = {'fitness': 0.0, 'survival_rate': 0, 'avg_healthiness': 0,
                     'efficiency': 0, 'cost': geno.total_cost(runtime),
                     'genotype_obj': geno, 'genotype': geno.to_dict(),
                     'frames': [], 'budget_exceeded': True,
                     'alive_count': 0, 'initial_count': len(fish_data),
                     'status': 'GATEKEEPER'}
                gen_results.append(r)
                csv_rows.append(_csv_row_data(tl_idx, gen, p_idx, 'GATEKEEPER', r, geno.to_dict()))
                continue

            # Run simulation sequentially within the timeline process
            sim_seed = random.randint(0, 2**31)
            random.seed(sim_seed)
            geno_obj = PondGenotype(**geno.to_dict())
            fishes = [_dict_to_fish(fd) for fd in fish_data]
            sim = PondSim(geno_obj, fishes, runtime, max_budget, record=do_rec, fskip=frame_skip)
            r = sim.run()
            r['genotype_obj'] = geno
            if r.get('budget_exceeded'):
                r['status'] = 'OVER-BUDGET'; r['fitness'] = 0.0
            elif r.get('survival_rate', 0) == 0:
                r['status'] = 'ALL-DEAD'
            else:
                r['status'] = 'OK'
            gen_results.append(r)
            csv_rows.append(_csv_row_data(tl_idx, gen, p_idx, r['status'], r, r['genotype']))

        gen_results.sort(key=lambda x: x['fitness'], reverse=True)

        if gen_results and gen_results[0]['fitness'] > 0:
            if best_result is None or gen_results[0]['fitness'] > best_result['fitness']:
                best_result = gen_results[0]

        half = max(1, len(gen_results) // 2)
        survivors = gen_results[:half]
        if len(survivors) <= 1: break

        surv_genos = [r['genotype_obj'] for r in survivors]
        new_ponds = [copy.deepcopy(g) for g in surv_genos]
        while len(new_ponds) < len(ponds):
            child = random.choice(surv_genos).crossover(random.choice(surv_genos))
            child.mutate(); new_ponds.append(child)
        ponds = new_ponds

    if best_result:
        best_result['timeline_idx'] = tl_idx
        best_result['fish_data'] = fish_data
        # Remove genotype_obj (not picklable cleanly)
        best_result.pop('genotype_obj', None)
    else:
        best_result = {
            'timeline_idx': tl_idx, 'fitness': 0, 'survival_rate': 0,
            'avg_healthiness': 0, 'efficiency': 0, 'cost': 0,
            'genotype': {}, 'frames': [], 'alive_count': 0,
            'initial_count': len(fish_data), 'fish_data': fish_data}

    return {'champion': best_result, 'csv_rows': csv_rows}


def _csv_row_data(tl_idx, gen_idx, pond_idx, status, result, geno_dict):
    return [
        tl_idx + 1, gen_idx + 1, pond_idx, status,
        f"{result.get('fitness', 0):.4f}",
        f"{result.get('survival_rate', 0):.4f}",
        f"{result.get('avg_healthiness', 0):.4f}",
        f"{result.get('cost', 0):.2f}",
        f"{result.get('efficiency', 0):.4f}",
        result.get('alive_count', 0),
        result.get('initial_count', 0),
        geno_dict.get('food_interval', ''),
        geno_dict.get('food_quantity', ''),
        geno_dict.get('food_location', ''),
        geno_dict.get('probiotic_interval', ''),
        geno_dict.get('probiotic_quantity', ''),
        geno_dict.get('probiotic_location', ''),
        geno_dict.get('oxygen_interval', ''),
        geno_dict.get('oxygen_duration', ''),
        geno_dict.get('oxygen_location', ''),
    ]


# ============================================================
# CSV
# ============================================================

CSV_HEADER = [
    'timeline', 'generation', 'pond', 'status',
    'fitness', 'survival_rate', 'healthiness', 'cost',
    'efficiency', 'alive_count', 'initial_count',
    'food_interval', 'food_quantity', 'food_location',
    'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
    'oxygen_interval', 'oxygen_duration', 'oxygen_location',
]


# ============================================================
# EVOLUTIONARY ALGORITHM — NESTED PARALLELISM
# ============================================================

class EA:
    def __init__(self):
        self.runtime = RUNTIME

    def run(self, record_best=True):
        wall_start = _time.time()
        workers = NUM_WORKERS or max(1, multiprocessing.cpu_count())

        print(f"\n{'=' * 72}")
        print(f"  LARGEMOUTH BASS AQUACULTURE OPTIMIZER -- PSO + EA")
        print(f"{'=' * 72}")
        print(f"  Fish: {INITIAL_FISH_POPULATION}  |  Days: {AQUACULTURE_DAYS}  |  "
              f"Budget: ${MAX_BUDGET:.2f}  |  Workers: {workers}")
        print(f"  Ponds/gen: {INITIAL_POND_COUNT}  |  Generations: {POND_GENERATIONS}  |  "
              f"Timelines: {RUN_TIMELINES}")
        print(f"  Parallelism: {RUN_TIMELINES} timelines in parallel")
        print(f"{'=' * 72}")

        # Build timeline tasks
        timeline_tasks = []
        for tl_idx in range(RUN_TIMELINES):
            base_fishes = [_make_fish(i) for i in range(INITIAL_FISH_POPULATION)]
            fish_data = [_fish_to_dict(f) for f in base_fishes]
            seed = random.randint(0, 2**31)
            timeline_tasks.append((
                tl_idx, fish_data, self.runtime, MAX_BUDGET,
                POND_GENERATIONS, INITIAL_POND_COUNT,
                record_best, FRAME_SKIP, seed
            ))

        # Run all timelines in parallel
        print(f"\n  Launching {RUN_TIMELINES} timelines in parallel...")
        timeline_results = [None] * RUN_TIMELINES
        with ProcessPoolExecutor(max_workers=min(workers, RUN_TIMELINES)) as pool:
            futures = {pool.submit(_run_timeline_worker, t): t[0] for t in timeline_tasks}
            for fut in as_completed(futures):
                tl_idx = futures[fut]
                result = fut.result()
                timeline_results[tl_idx] = result
                champ = result['champion']
                elapsed = _time.time() - wall_start
                print(f"  Timeline {tl_idx+1} finished ({elapsed:.1f}s) | "
                      f"Fitness={champ['fitness']:.4f} | "
                      f"Survival={champ['survival_rate']*100:.2f}%")

        # Collect CSV rows and champions
        all_csv_rows = []
        timeline_champions = []
        for tl_idx in range(RUN_TIMELINES):
            res = timeline_results[tl_idx]
            all_csv_rows.extend(res['csv_rows'])
            timeline_champions.append(res['champion'])

        # Write CSV
        with open(RESULTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerows(all_csv_rows)
        print(f"\n  Saved {RESULTS_CSV_PATH} ({len(all_csv_rows)} rows)")

        # Print each timeline champion
        for champ in timeline_champions:
            tl = champ.get('timeline_idx', 0)
            if champ['fitness'] > 0:
                _print_champion_detail(f"Timeline {tl+1} Champion", champ)
            else:
                print(f"\n  Timeline {tl+1}: No survivors.")

        # Summary table
        valid = [c for c in timeline_champions if c.get('fitness', 0) > 0]
        if not valid:
            print(f"\n{'=' * 72}")
            print(f"  No valid champions across all {RUN_TIMELINES} timelines.")
            print(f"{'=' * 72}")
            return None

        print(f"\n{'=' * 72}")
        best_idx = _print_champions_summary(timeline_champions)
        champ = timeline_champions[best_idx]

        # Re-run champion with frame recording using SAME fish
        if record_best and not champ.get('frames'):
            print(f"\n  Re-running champion (Timeline {champ['timeline_idx']+1}) with frame recording...")
            stored_fish_data = champ.get('fish_data', [])
            if stored_fish_data:
                fishes = [_dict_to_fish(fd) for fd in stored_fish_data]
            else:
                fishes = [_make_fish(i) for i in range(INITIAL_FISH_POPULATION)]
            geno = PondGenotype(**champ['genotype'])
            sim = PondSim(geno, fishes, self.runtime, MAX_BUDGET, record=True, fskip=FRAME_SKIP)
            res = sim.run()
            champ['frames'] = res['frames']

        wall_elapsed = _time.time() - wall_start
        _print_champion_detail(f"GRAND CHAMPION  (Timeline {champ['timeline_idx']+1})", champ)
        print(f"\n  Total wall time: {wall_elapsed:.1f}s")

        return champ


# ============================================================
# MAIN
# ============================================================

def main():
    ea = EA()
    champ = ea.run(record_best=True)

    if champ and champ.get('frames'):
        viz = {
            'pond_width': POND_WIDTH, 'pond_height': POND_HEIGHT,
            'genotype': champ['genotype'],
            'fitness': champ['fitness'],
            'survival_rate': champ['survival_rate'],
            'avg_healthiness': champ.get('avg_healthiness', 0),
            'cost': champ['cost'],
            'efficiency': champ['efficiency'],
            'initial_fish': INITIAL_FISH_POPULATION,
            'aquaculture_days': AQUACULTURE_DAYS,
            'frames': champ['frames']}

        with open('simulation_data.json', 'w') as fp:
            json.dump(viz, fp)
        print(f"\n  Saved simulation_data.json ({len(champ['frames'])} frames)")
        print(f"  Open visualization.html in browser (via: python -m http.server)")
    else:
        print("\n  No frames to export.")


if __name__ == '__main__':
    main()