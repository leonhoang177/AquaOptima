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
# ║  Adjust these to control the simulation scale & behavior.   ║
# ╚══════════════════════════════════════════════════════════════╝

MAX_BUDGET = 200.0                # Max allowed per-cycle cost ($). Ponds exceeding this are rejected by the Gatekeeper.
INITIAL_FISH_POPULATION = 30      # Number of Largemouth Bass at the start of each simulation.
AQUACULTURE_DAYS = 20             # Duration of the aquaculture period in real days. Runtime = this * 24 timesteps.
POND_GENERATIONS = 10             # Number of EA selection rounds. More = better convergence but slower.
RUN_SIMULATIONS = 3               # Number of independent parallel timelines. Best champion is picked across all.
INITIAL_POND_COUNT = 10           # Number of random pond genotypes in the first EA generation.
FRAME_SKIP = 1                    # Record a visualization frame every N timesteps. Lower = smoother but larger JSON.
NUM_WORKERS = None                # Parallel workers. None = auto-detect CPU count. Set to 1 for debugging.

# ╔══════════════════════════════════════════════════════════════╗
# ║                    ECONOMIC CONSTANTS                       ║
# ║  Unit prices for pond policies. Affect total cost & fitness.║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_PRICE = 0.10                 # Cost per food pellet ($). Multiplied by quantity and frequency.
PROBIOTIC_PRICE = 0.50            # Cost per probiotic pellet ($). More expensive than food.
OXYGEN_PRICE = 2.00               # Cost per hour of oxygen pumping ($). Most expensive policy.

# ╔══════════════════════════════════════════════════════════════╗
# ║                  EA FITNESS WEIGHTS                         ║
# ║  Control how the 3 pillars contribute to final fitness.     ║
# ║  Must sum to 1.0. Survival is king, efficiency is minor.    ║
# ╚══════════════════════════════════════════════════════════════╝

W1_SURVIVAL = 0.50                # Weight for survival rate (alive/initial). Dominant factor.
W2_HEALTHINESS = 0.35             # Weight for average fish healthiness (HP, energy, fullness, immunity, velocity).
W3_EFFICIENCY = 0.15              # Weight for budget efficiency ((budget - cost) / budget). Rewards frugality.

# ╔══════════════════════════════════════════════════════════════╗
# ║                    POND DIMENSIONS                          ║
# ║  2D pond size in abstract units. All positions are within.  ║
# ╚══════════════════════════════════════════════════════════════╝

POND_WIDTH = 200.0                # Horizontal extent of the pond environment.
POND_HEIGHT = 75.0               # Vertical extent of the pond environment.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH TRAIT RANGES (FIXED)                   ║
# ║  Randomized once per fish at creation. Cannot change.       ║
# ╚══════════════════════════════════════════════════════════════╝

MOUTH_SIZE_RANGE = (3.0, 8.0)     # Determines max prey size for cannibalism. Larger = more dangerous predator.
BODY_SIZE_RANGE = (4.0, 10.0)     # Defensive stat. If body < another's mouth, this fish is a valid prey target.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH STAT RANGES (DYNAMIC)                  ║
# ║  Randomized at creation. Change every timestep via decay,   ║
# ║  eating, disease, etc. Fish dies if HP or Oxygen <= 0.      ║
# ╚══════════════════════════════════════════════════════════════╝

HP_RANGE = (80.0, 120.0)          # Health points. Fish dies at 0. Drained by starvation, infection, parasites.
ENERGY_RANGE = (60.0, 100.0)      # Movement fuel. Drained by swimming. At 0, HP starts dropping.
FULLNESS_RANGE = (50.0, 80.0)     # Stomach level. Decays naturally. At 0, HP drops. Regained by eating.
IMMUNITY_RANGE = (70.0, 100.0)    # Disease resistance. Drained in disease areas. At 0, fish gets infected.
OXYGEN_RANGE = (80.0, 100.0)      # Dissolved oxygen in fish. Decays naturally, faster in NH3. At 0, fish dies.
VELOCITY_RANGE = (1.0, 3.0)       # Base swimming speed. Reduced by low HP/energy/fullness and parasites.

# ╔══════════════════════════════════════════════════════════════╗
# ║                   PSO DISTANCE RADII                        ║
# ║  Control how far fish can sense and interact with others.   ║
# ╚══════════════════════════════════════════════════════════════╝

SENSITIVE_DISTANCE = 40.0         # Vision radius. Max range for detecting food, hazards, cannibals. Beyond = invisible.
SOCIAL_DISTANCE = 25.0            # Cohesion radius. Fish inside this (but outside selfish) trigger schooling behavior.
SELFISH_DISTANCE = 8.0            # Separation radius. Fish inside this trigger repulsion to avoid clipping.

# ╔══════════════════════════════════════════════════════════════╗
# ║                STAT DECAY RATES (PER TIMESTEP)              ║
# ║  How fast each stat drains every hour. Lower = more         ║
# ║  forgiving. Calibrated for 60-day (1440 ts) survival.       ║
# ╚══════════════════════════════════════════════════════════════╝

OXYGEN_DECAY = 0.05               # O2 loss per timestep. At 0.05, a fish with 90 O2 lasts ~1800 ts (~75 days) alone.
OXYGEN_DECAY_NH3_MULT = 2.0       # Extra O2 drain multiplier while inside NH3 area. Makes NH3 very dangerous.
ENERGY_DECAY = 0.04               # Energy loss per timestep. At 0.04, fish with 80 energy lasts ~2000 ts (~83 days).
FULLNESS_DECAY = 0.06             # Fullness loss per timestep. At 0.06, stomach empties in ~1000 ts (~42 days).
ENERGY_COST_MOVE = 0.05           # Extra energy cost per timestep proportional to velocity. Swimming tax.

# ╔══════════════════════════════════════════════════════════════╗
# ║              HP DRAIN RATES (WHEN STATS DEPLETED)           ║
# ║  These fire every timestep when the condition is met.       ║
# ║  Multiple can stack (e.g., no energy + infected).           ║
# ╚══════════════════════════════════════════════════════════════╝

HP_DECAY_NO_ENERGY = 0.4          # HP loss/ts when energy <= 0. Fish slowly dies without fuel.
HP_DECAY_NO_FULLNESS = 0.3        # HP loss/ts when fullness <= 0. Starvation damage.
HP_DECAY_INFECTED = 0.6           # HP loss/ts while isInfected == True. Bacterial damage.
HP_DECAY_PARASITE = 0.8           # HP loss every 3rd ts while hasParasite == True. Slow parasitic death.

# ╔══════════════════════════════════════════════════════════════╗
# ║              DISEASE & PARASITE MECHANICS                   ║
# ╚══════════════════════════════════════════════════════════════╝

IMMUNITY_DECAY_IN_DISEASE = 1.5   # Immunity loss/ts while inside a disease area. Fast — forces probiotic use.
PARASITE_CONTACT_CHANCE = 0.05    # Chance per ts of contracting parasite while inside parasite area (0-1).
PARASITE_FULLNESS_EFFICIENCY = 0.5  # Multiplier on food fullness gain while parasitized. Halved absorption.
PARASITE_EXTRA_FULLNESS_DRAIN = 1.5 # Multiplier on fullness decay while parasitized. 50% faster hunger.
PARASITE_EXTRA_ENERGY_DRAIN = 1.5   # Multiplier on energy cost while parasitized. 50% more tiring.
PARASITE_VELOCITY_MULT = 0.75    # Velocity multiplier while parasitized. 25% slower.
PARASITE_SCRUB_CHANCE = 0.15     # Chance of removing parasite when colliding with obstacle surface.

# ╔══════════════════════════════════════════════════════════════╗
# ║              VELOCITY REDUCTION THRESHOLDS                  ║
# ║  Fish slow down when stats drop below these fractions.      ║
# ╚══════════════════════════════════════════════════════════════╝

VELOCITY_HP_THRESHOLD = 0.5       # If HP <= 50% of max, velocity halved.
VELOCITY_ENERGY_THRESHOLD = 0.5   # If energy <= 50% of max, velocity halved.
VELOCITY_FULLNESS_THRESHOLD = 0.5 # If fullness <= 50% of max, velocity halved.
VELOCITY_RUNNING_HUNTING_MULT = 1.5  # Speed boost while running or hunting. Costs more energy.
RUNNING_HUNTING_ENERGY_MULT = 1.5    # Energy cost multiplier while running or hunting.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 OBJECT LIFETIMES (TIMESTEPS)                ║
# ║  How long each dynamic object persists before expiring      ║
# ║  and transforming (usually into pollutant).                 ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_EXPIRE_TIMESTEPS = 48        # Food pellet lifespan. 48 ts = 2 days. Becomes pollutant if uneaten.
PROBIOTIC_EXPIRE_TIMESTEPS = 18   # Probiotic lifespan. 18 ts = 18 hours. Expires fast — urgency to consume.
FECAL_EXPIRE_TIMESTEPS = 36       # Fecal drop lifespan. 36 ts = 1.5 days. Becomes pollutant.
DEAD_FISH_DECAY_TIMESTEPS = 24    # Dead fish body lifespan. 24 ts = 1 day. Decays into pollutant.
NH3_EXPIRE_TIMESTEPS = 60         # NH3 area lifespan. 60 ts = 2.5 days. Becomes pollutant at 50% value.
DISEASE_AREA_DECAY = 72           # Disease area lifespan. 72 ts = 3 days. Slowly shrinks then disappears.
PARASITE_AREA_DECAY = 72          # Parasite area lifespan. 72 ts = 3 days. Slowly shrinks then disappears.
POLLUTANT_TO_HAZARD_TIMESTEPS = 48  # Pollutant lifespan before becoming disease/parasite area. 30 ts = 1.25 days.
DISEASE_AREA_RADIUS_DECAY = 0.998   # Per-timestep radius multiplier for disease/parasite areas. Slow shrink.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 POLLUTANT → HAZARD CHANCES                  ║
# ║  Probability that an expired pollutant spawns a hazard.     ║
# ╚══════════════════════════════════════════════════════════════╝

POLLUTANT_TO_DISEASE_CHANCE = 0.4   # 40% chance pollutant becomes disease area.
POLLUTANT_TO_PARASITE_CHANCE = 0.3  # 30% chance pollutant becomes parasite area. Can be both (12% chance).
POLLUTANT_RADIUS_SCALE = 1.5       # Hazard radius = pollutant_value * this. Higher = larger danger zones.
DEAD_FISH_POLLUTANT_MULT = 1.5     # Dead fish pollutant value multiplier. Corpses are extra toxic.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FOOD & HEALING GAINS                        ║
# ║  How much each consumable restores per unit eaten.          ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_ENERGY_GAIN = 25.0           # Energy restored per food unit consumed. One pellet covers ~625 ts of decay.
FOOD_FULLNESS_GAIN = 20.0         # Fullness restored per food unit consumed. One pellet covers ~333 ts of decay.
FOOD_VALUE = 5.0                  # Number of "bites" in each food pellet. Each fish eating reduces by 1.
PROBIOTIC_VALUE = 3.0             # Number of doses in each probiotic pellet.
PROBIOTIC_IMMUNITY_BOOST = 40.0   # Immunity restored per probiotic dose consumed.
OXYGEN_BUBBLE_GAIN = 30.0         # Oxygen restored per bubble absorbed. One bubble covers ~600 ts of decay.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 STATE DURATIONS (TIMESTEPS)                 ║
# ╚══════════════════════════════════════════════════════════════╝

BOOSTING_DURATION = 5             # Timesteps isBoosting lasts after eating probiotic. Refreshed, not stacked.
IMMUNITY_BOOST_DURATION = 10      # (Unused separately — boosting covers this window.)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 NATURAL SPAWN RATES                         ║
# ║  Per-timestep probability of environment spawning objects.  ║
# ╚══════════════════════════════════════════════════════════════╝

NATURAL_OXYGEN_SPAWN_RATE = 0.12  # ~8% chance/ts of a natural O2 bubble appearing. ~2 per day.
NATURAL_NH3_SPAWN_RATE = 0.005    # ~0.5% chance/ts of a natural NH3 area appearing. ~0.7 per day.
OXYGEN_BUBBLES_PER_PUMP = 7       # Number of O2 bubbles spawned per active pump timestep.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 ENVIRONMENT OBJECTS                         ║
# ╚══════════════════════════════════════════════════════════════╝

NUM_OBSTACLES = 15                 # Number of underwater obstacles (rocks). Used for collision and parasite scrubbing.
OBSTACLE_SIZE_RANGE = (8.0, 20.0) # Width/height range for each obstacle.
OBSTACLE_STATIC_CHANCE = 0.6      # Probability an obstacle is static (vs. slowly drifting).
OBSTACLE_MAX_SPEED = 0.3          # Max drift speed for dynamic obstacles.
OXYGEN_BUBBLE_SPEED = 0.5         # Max random velocity for oxygen bubbles.
NH3_AREA_RADIUS_RANGE = (8.0, 15.0)  # Radius range for naturally spawned NH3 areas.
NH3_AREA_SPEED = 0.2              # Max drift speed for NH3 areas.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FECAL MECHANICS                             ║
# ╚══════════════════════════════════════════════════════════════╝

FECAL_DROP_INTERVAL = 2           # Fish can drop fecal every N timesteps (if fullness > 0).
FECAL_BASE_CHANCE = 0.2           # Max fecal chance at full stomach. Actual = (fullness/max) * this.
FECAL_VALUE = 2.0                 # Pollution value of each fecal drop.
FECAL_STACK_RADIUS = 10.0         # Nearby fecal within this radius merge into one larger pile.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 CANNIBALISM MECHANICS                       ║
# ╚══════════════════════════════════════════════════════════════╝

CANNIBAL_TRIGGER_CHANCE = 0.3     # Chance per ts of entering hunting mode when fullness <= 0 and valid target nearby.
CANNIBAL_FULLNESS_GAIN_MULT = 2.0 # Fullness gained = target.body_size * this. Reward for successful hunt.
CANNIBAL_COLLISION_RADIUS_MULT = 1.0  # Kill happens when dist <= target.body_size * this.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 PSO VECTOR WEIGHTS                          ║
# ║  Base weights for each behavioral vector. Dynamically       ║
# ║  scaled by fish stats during simulation.                    ║
# ╚══════════════════════════════════════════════════════════════╝

PSO_INERTIA = 0.4                 # Momentum weight. Higher = fish maintain heading longer.
PSO_FOOD_WEIGHT = 2.0             # Base attraction to food. Scaled by (1 - fullness_ratio).
PSO_FOOD_URGENT_MULT = 2.0       # Extra food weight when energy < 30%.
PSO_PROBIOTIC_WEIGHT = 1.5       # Base attraction to probiotics. Scaled by (1 - immunity_ratio).
PSO_OXYGEN_WEIGHT = 3.0          # Base attraction to O2 bubbles. Scaled by (1 - oxygen_ratio).
PSO_OXYGEN_CRITICAL_MULT = 3.0   # Extra O2 weight when oxygen < 30%. Makes O2 top priority.
PSO_OXYGEN_THRESHOLD = 0.7       # O2 ratio below which cOxygen activates.
PSO_OXYGEN_CRITICAL_THRESHOLD = 0.3  # O2 ratio below which critical multiplier kicks in.
PSO_OXYGEN_INTERCEPT_STEPS = 3   # Timesteps ahead to predict moving O2 bubble position.
PSO_SOCIAL_WEIGHT = 0.8          # Schooling cohesion weight. Keeps swarm together.
PSO_SELFISH_WEIGHT = 1.5         # Separation repulsion weight. Prevents fish overlap.
PSO_NH3_WEIGHT = 4.0             # NH3 avoidance weight. Very high — NH3 is lethal.
PSO_NH3_HUNGRY_OVERRIDE = 0.5    # Reduced NH3 weight when starving and food is inside NH3.
PSO_DISEASE_WEIGHT = 2.5         # Disease area avoidance weight.
PSO_DISEASE_BOOSTING_WEIGHT = 0.3  # Reduced disease weight when isBoosting (immune).
PSO_PARASITE_WEIGHT = 3.0        # Parasite area avoidance weight.
PSO_RELIEF_WEIGHT = 4.0          # Scrubbing vector weight when parasitized.
PSO_RUN_WEIGHT = 5.0             # Cannibal evasion weight. Scaled by distance.
PSO_HUNT_WEIGHT = 3.0            # Cannibal pursuit weight. Scaled by distance.

STATE_OVERRIDE_PARASITE_CHANCE = 0.6  # Chance parasitized fish overrides PSO with scrubbing.
STATE_OVERRIDE_RUNNING_CHANCE = 0.7   # Chance fleeing fish overrides PSO with flee vector.
STATE_OVERRIDE_HUNTING_CHANCE = 0.7   # Chance hunting fish overrides PSO with hunt vector.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 EA MUTATION PARAMETERS                      ║
# ╚══════════════════════════════════════════════════════════════╝

EA_MUTATION_RATE = 0.25           # Per-gene probability of mutation during offspring creation.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH EATING RANGE                           ║
# ╚══════════════════════════════════════════════════════════════╝

FISH_EAT_RANGE = 3.0              # Extra distance beyond body_size for consuming objects.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 INFECTED FISH DISEASE RADIUS                ║
# ╚══════════════════════════════════════════════════════════════╝

INFECTED_FISH_DISEASE_RADIUS_MULT = 1.5  # Disease area radius = body_size * this when infected fish dies.

# ╔══════════════════════════════════════════════════════════════╗
# ║                 CSV OUTPUT FILE                             ║
# ╚══════════════════════════════════════════════════════════════╝

RESULTS_CSV_PATH = 'results.csv'  # Path for the per-pond per-generation tracking CSV.

# ════════════════════════════════════════════════════════════════
#  DERIVED CONSTANTS (do not edit)
# ════════════════════════════════════════════════════════════════

RUNTIME = AQUACULTURE_DAYS * 24   # Total timesteps in one simulation run.


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
            food_interval=random.randint(1, 24),
            food_quantity=random.randint(1, 10),
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
        if random.random() < r: self.food_interval = random.randint(1, 24)
        if random.random() < r: self.food_quantity = random.randint(1, 10)
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
    is_static: bool = True
    vx: float = 0.0; vy: float = 0.0

    def contains(self, px, py) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h

    def nearest_surface(self, px, py) -> Tuple[float, float]:
        return max(self.x, min(px, self.x + self.w)), max(self.y, min(py, self.y + self.h))


@dataclass
class DynObj:
    x: float; y: float
    kind: str
    value: float = 5.0
    age: int = 0
    max_age: int = 30
    vx: float = 0.0; vy: float = 0.0
    alive: bool = True


@dataclass
class Hazard:
    x: float; y: float; radius: float
    kind: str
    age: int = 0; max_age: int = 50
    alive: bool = True
    vx: float = 0.0; vy: float = 0.0

    def contains(self, px, py) -> bool:
        return (px - self.x) ** 2 + (py - self.y) ** 2 <= self.radius ** 2


@dataclass
class Fish:
    fid: int = 0
    x: float = 0.0; y: float = 0.0
    vx: float = 0.0; vy: float = 0.0
    mouth_size: float = 5.0; body_size: float = 6.0
    hp: float = 100.0; max_hp: float = 100.0
    energy: float = 80.0; max_energy: float = 80.0
    fullness: float = 60.0; max_fullness: float = 60.0
    immunity: float = 80.0; max_immunity: float = 80.0
    oxygen: float = 90.0; max_oxygen: float = 90.0
    base_velocity: float = 2.0
    is_boosting: bool = False; boost_timer: int = 0
    is_infected: bool = False; has_parasite: bool = False
    is_running: bool = False; is_hunting: bool = False
    alive: bool = True; fecal_timer: int = 0

    def eff_vel(self) -> float:
        v = self.base_velocity
        if self.hp <= self.max_hp * VELOCITY_HP_THRESHOLD: v *= 0.5
        if self.energy <= self.max_energy * VELOCITY_ENERGY_THRESHOLD: v *= 0.5
        if self.fullness <= self.max_fullness * VELOCITY_FULLNESS_THRESHOLD: v *= 0.5
        if self.has_parasite: v *= PARASITE_VELOCITY_MULT
        if self.is_running or self.is_hunting: v *= VELOCITY_RUNNING_HUNTING_MULT
        return v

    def norm_stats(self) -> float:
        hp_n = max(0, self.hp) / self.max_hp
        en_n = max(0, self.energy) / self.max_energy
        fu_n = max(0, self.fullness) / self.max_fullness
        im_n = max(0, self.immunity) / self.max_immunity
        vl_n = min(1.0, self.eff_vel() / (self.base_velocity * VELOCITY_RUNNING_HUNTING_MULT + 1e-9))
        return (hp_n + en_n + fu_n + im_n + vl_n) / 5.0

    def snapshot(self) -> dict:
        return {'id': self.fid, 'x': round(self.x, 1), 'y': round(self.y, 1),
                'hp': round(self.hp, 1), 'energy': round(self.energy, 1),
                'fullness': round(self.fullness, 1), 'immunity': round(self.immunity, 1),
                'oxygen': round(self.oxygen, 1), 'alive': self.alive,
                'is_infected': self.is_infected, 'has_parasite': self.has_parasite,
                'is_running': self.is_running, 'is_hunting': self.is_hunting,
                'is_boosting': self.is_boosting,
                'body_size': round(self.body_size, 1), 'mouth_size': round(self.mouth_size, 1)}


# ============================================================
# HELPERS
# ============================================================

def _dist(x1, y1, x2, y2) -> float:
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2)

def _clamp(v, lo, hi) -> float:
    return max(lo, min(hi, v))

def _norm(vx, vy) -> Tuple[float, float]:
    m = math.sqrt(vx * vx + vy * vy)
    return (vx / m, vy / m) if m > 1e-8 else (0.0, 0.0)

def _drop_pos(loc: int) -> Tuple[float, float]:
    if loc == DropLocation.MIDDLE:
        return POND_WIDTH / 2 + random.uniform(-15, 15), POND_HEIGHT / 2 + random.uniform(-15, 15)
    elif loc == DropLocation.CORNER:
        cx, cy = random.choice([(15, 15), (POND_WIDTH - 15, 15),
                                 (15, POND_HEIGHT - 15), (POND_WIDTH - 15, POND_HEIGHT - 15)])
        return cx + random.uniform(-10, 10), cy + random.uniform(-10, 10)
    return random.uniform(10, POND_WIDTH - 10), random.uniform(10, POND_HEIGHT - 10)

def _make_fish(fid: int) -> Fish:
    f = Fish(fid=fid)
    f.x = random.uniform(20, POND_WIDTH - 20)
    f.y = random.uniform(20, POND_HEIGHT - 20)
    f.mouth_size = random.uniform(*MOUTH_SIZE_RANGE)
    f.body_size = random.uniform(*BODY_SIZE_RANGE)
    f.max_hp = random.uniform(*HP_RANGE); f.hp = f.max_hp
    f.max_energy = random.uniform(*ENERGY_RANGE); f.energy = f.max_energy
    f.max_fullness = random.uniform(*FULLNESS_RANGE); f.fullness = f.max_fullness * 0.8
    f.max_immunity = random.uniform(*IMMUNITY_RANGE); f.immunity = f.max_immunity
    f.max_oxygen = random.uniform(*OXYGEN_RANGE); f.oxygen = f.max_oxygen
    f.base_velocity = random.uniform(*VELOCITY_RANGE)
    f.vx = random.uniform(-1, 1); f.vy = random.uniform(-1, 1)
    return f


# ============================================================
# POND SIMULATION ENGINE
# ============================================================

class PondSim:
    __slots__ = ('geno', 'runtime', 'max_budget', 'record', 'fskip',
                 'fish', 'n0', 'ts', 'objs', 'hazards', 'obstacles',
                 'oxy_pump', 'frames', 'accum_cost', 'budget_exceeded')

    def __init__(self, geno: PondGenotype, fish_templates: List[Fish],
                 runtime: int, max_budget: float,
                 record: bool = False, fskip: int = 1):
        self.geno = geno
        self.runtime = runtime
        self.max_budget = max_budget
        self.record = record
        self.fskip = fskip
        self.fish: List[Fish] = copy.deepcopy(fish_templates)
        self.n0 = len(self.fish)
        self.ts = 0
        self.objs: List[DynObj] = []
        self.hazards: List[Hazard] = []
        self.obstacles: List[Obstacle] = []
        self.oxy_pump = 0
        self.frames: list = []
        self.accum_cost = 0.0
        self.budget_exceeded = False
        self._make_obstacles()

    def _make_obstacles(self):
        for _ in range(NUM_OBSTACLES):
            w = random.uniform(*OBSTACLE_SIZE_RANGE)
            h = random.uniform(*OBSTACLE_SIZE_RANGE)
            x = random.uniform(10, POND_WIDTH - 10 - w)
            y = random.uniform(10, POND_HEIGHT - 10 - h)
            static = random.random() < OBSTACLE_STATIC_CHANCE
            vx = random.uniform(-OBSTACLE_MAX_SPEED, OBSTACLE_MAX_SPEED) if not static else 0
            vy = random.uniform(-OBSTACLE_MAX_SPEED, OBSTACLE_MAX_SPEED) if not static else 0
            self.obstacles.append(Obstacle(x, y, w, h, static, vx, vy))

    def _cp(self, x, y):
        return _clamp(x, 2, POND_WIDTH - 2), _clamp(y, 2, POND_HEIGHT - 2)

    def run(self) -> dict:
        for t in range(self.runtime):
            self.ts = t
            self._step()
            if self.record and t % self.fskip == 0:
                self.frames.append(self._frame())
            if self.budget_exceeded:
                break
            if not any(f.alive for f in self.fish):
                break

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
        self._spawn_food(t)
        self._spawn_prob(t)
        self._pump_oxy(t)
        self._nat_spawn()
        self._upd_objs()
        self._upd_hazards()
        self._upd_obstacles()
        self._decay_stats()
        self._eat()
        self._pso()
        self._cannibal()
        self._fecal()
        self._death()

    def _add_cost(self, amount: float):
        self.accum_cost += amount
        if self.accum_cost > self.max_budget:
            self.budget_exceeded = True

    def _spawn_food(self, t):
        if t % self.geno.food_interval == 0:
            cost = self.geno.food_quantity * FOOD_PRICE
            self._add_cost(cost)
            if self.budget_exceeded: return
            for _ in range(self.geno.food_quantity):
                x, y = _drop_pos(self.geno.food_location)
                self.objs.append(DynObj(x, y, 'food', FOOD_VALUE, max_age=FOOD_EXPIRE_TIMESTEPS))

    def _spawn_prob(self, t):
        if t % self.geno.probiotic_interval == 0:
            cost = self.geno.probiotic_quantity * PROBIOTIC_PRICE
            self._add_cost(cost)
            if self.budget_exceeded: return
            for _ in range(self.geno.probiotic_quantity):
                x, y = _drop_pos(self.geno.probiotic_location)
                self.objs.append(DynObj(x, y, 'probiotic', PROBIOTIC_VALUE, max_age=PROBIOTIC_EXPIRE_TIMESTEPS))

    def _pump_oxy(self, t):
        if t % self.geno.oxygen_interval == 0:
            self.oxy_pump = self.geno.oxygen_duration
        if self.oxy_pump > 0:
            cost = OXYGEN_PRICE
            self._add_cost(cost)
            if self.budget_exceeded: return
            for _ in range(OXYGEN_BUBBLES_PER_PUMP):
                x, y = _drop_pos(self.geno.oxygen_location)
                self.objs.append(DynObj(x, y, 'oxygen', 1.0, max_age=99999,
                                        vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                                        vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED)))
            self.oxy_pump -= 1

    def _nat_spawn(self):
        if random.random() < NATURAL_OXYGEN_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH - 10), random.uniform(10, POND_HEIGHT - 10)
            self.objs.append(DynObj(x, y, 'oxygen', 1.0, max_age=99999,
                                    vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                                    vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED)))
        if random.random() < NATURAL_NH3_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH - 10), random.uniform(10, POND_HEIGHT - 10)
            self.hazards.append(Hazard(x, y, random.uniform(*NH3_AREA_RADIUS_RANGE), 'nh3',
                                       max_age=NH3_EXPIRE_TIMESTEPS,
                                       vx=random.uniform(-NH3_AREA_SPEED, NH3_AREA_SPEED),
                                       vy=random.uniform(-NH3_AREA_SPEED, NH3_AREA_SPEED)))

    def _upd_objs(self):
        keep = []
        for o in self.objs:
            o.age += 1
            if o.kind == 'oxygen':
                o.x += o.vx; o.y += o.vy
                if o.x < 2 or o.x > POND_WIDTH - 2: o.vx *= -1
                if o.y < 2 or o.y > POND_HEIGHT - 2: o.vy *= -1
                o.x, o.y = self._cp(o.x, o.y)
                if any(h.contains(o.x, o.y) and h.kind == 'nh3' and h.alive for h in self.hazards):
                    continue
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
            if o.alive:
                keep.append(o)
        self.objs = keep

    def _upd_hazards(self):
        keep = []
        for h in self.hazards:
            h.age += 1
            if h.kind == 'nh3':
                h.x += h.vx; h.y += h.vy
                if h.x < 5 or h.x > POND_WIDTH - 5: h.vx *= -1
                if h.y < 5 or h.y > POND_HEIGHT - 5: h.vy *= -1
                h.x = _clamp(h.x, 5, POND_WIDTH - 5)
                h.y = _clamp(h.y, 5, POND_HEIGHT - 5)
            if h.age >= h.max_age:
                if h.kind == 'nh3':
                    self.objs.append(DynObj(h.x, h.y, 'pollutant', h.radius * 0.5,
                                           max_age=POLLUTANT_TO_HAZARD_TIMESTEPS))
                continue
            if h.kind in ('disease', 'parasite'):
                h.radius = max(1, h.radius * DISEASE_AREA_RADIUS_DECAY)
            keep.append(h)
        self.hazards = keep

    def _upd_obstacles(self):
        for o in self.obstacles:
            if not o.is_static:
                o.x += o.vx; o.y += o.vy
                if o.x < 2 or o.x + o.w > POND_WIDTH - 2: o.vx *= -1
                if o.y < 2 or o.y + o.h > POND_HEIGHT - 2: o.vy *= -1
                o.x = _clamp(o.x, 2, POND_WIDTH - 2 - o.w)
                o.y = _clamp(o.y, 2, POND_HEIGHT - 2 - o.h)

    def _decay_stats(self):
        for f in self.fish:
            if not f.alive: continue
            f.oxygen -= OXYGEN_DECAY
            for h in self.hazards:
                if h.kind == 'nh3' and h.contains(f.x, f.y):
                    f.oxygen -= OXYGEN_DECAY * OXYGEN_DECAY_NH3_MULT
            ec = ENERGY_DECAY
            if f.has_parasite: ec *= PARASITE_EXTRA_ENERGY_DRAIN
            if f.is_running or f.is_hunting: ec *= RUNNING_HUNTING_ENERGY_MULT
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
                    if random.random() < PARASITE_CONTACT_CHANCE:
                        f.has_parasite = True

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
                    f.oxygen = min(f.max_oxygen, f.oxygen + OXYGEN_BUBBLE_GAIN)
                    o.alive = False

    def _pso(self):
        alive = [f for f in self.fish if f.alive]
        if not alive: return
        for f in alive:
            vel = f.eff_vel()
            nvx = PSO_INERTIA * f.vx
            nvy = PSO_INERTIA * f.vy
            for w, dx, dy in self._vectors(f, alive):
                nvx += w * dx; nvy += w * dy
            m = math.sqrt(nvx ** 2 + nvy ** 2)
            if m > 0.01: nvx = nvx / m * vel; nvy = nvy / m * vel
            if f.has_parasite and random.random() < STATE_OVERRIDE_PARASITE_CHANCE:
                sv = self._scrub(f)
                if sv: nvx, nvy = sv[0] * vel, sv[1] * vel
            if f.is_running and random.random() < STATE_OVERRIDE_RUNNING_CHANCE:
                rv = self._flee(f, alive)
                if rv: nvx, nvy = rv[0] * vel * 1.2, rv[1] * vel * 1.2
            if f.is_hunting and random.random() < STATE_OVERRIDE_HUNTING_CHANCE:
                hv = self._pursue(f, alive)
                if hv: nvx, nvy = hv[0] * vel * 1.2, hv[1] * vel * 1.2
            f.vx, f.vy = nvx, nvy
            nx, ny = f.x + f.vx, f.y + f.vy
            for obs in self.obstacles:
                if obs.contains(nx, ny):
                    sx, sy = obs.nearest_surface(f.x, f.y)
                    dx, dy = _norm(f.x - sx, f.y - sy)
                    nx, ny = f.x + dx * 2, f.y + dy * 2
                    f.vx *= -0.5; f.vy *= -0.5
                    if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                        f.has_parasite = False
            f.x, f.y = self._cp(nx, ny)
            mc = ENERGY_COST_MOVE * vel
            if f.has_parasite: mc *= PARASITE_EXTRA_ENERGY_DRAIN
            if f.is_running or f.is_hunting: mc *= RUNNING_HUNTING_ENERGY_MULT
            f.energy -= mc

    def _vectors(self, f: Fish, alive: List[Fish]):
        vecs = []
        fr = max(0, f.fullness) / f.max_fullness
        if fr < 1.0:
            fw = PSO_FOOD_WEIGHT * (1.0 - fr)
            if max(0, f.energy) / f.max_energy < 0.3: fw *= PSO_FOOD_URGENT_MULT
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'food' and o.value > 0:
                    d = _dist(f.x, f.y, o.x, o.y)
                    if d < SENSITIVE_DISTANCE and d < nd: nd, no = d, o
            if no:
                dx, dy = _norm(no.x - f.x, no.y - f.y)
                vecs.append((fw, dx, dy))
        if not f.is_boosting:
            ir = max(0, f.immunity) / f.max_immunity
            pw = PSO_PROBIOTIC_WEIGHT * (1.0 - ir)
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'probiotic' and o.value > 0:
                    d = _dist(f.x, f.y, o.x, o.y)
                    if d < SENSITIVE_DISTANCE and d < nd: nd, no = d, o
            if no:
                dx, dy = _norm(no.x - f.x, no.y - f.y)
                vecs.append((pw, dx, dy))
        orr = max(0, f.oxygen) / f.max_oxygen
        if orr < PSO_OXYGEN_THRESHOLD:
            ow = PSO_OXYGEN_WEIGHT * (1.0 - orr)
            if orr < PSO_OXYGEN_CRITICAL_THRESHOLD: ow *= PSO_OXYGEN_CRITICAL_MULT
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'oxygen':
                    fx2 = o.x + o.vx * PSO_OXYGEN_INTERCEPT_STEPS
                    fy2 = o.y + o.vy * PSO_OXYGEN_INTERCEPT_STEPS
                    d = min(_dist(f.x, f.y, o.x, o.y), _dist(f.x, f.y, fx2, fy2))
                    if d < SENSITIVE_DISTANCE and d < nd: nd, no = d, o
            if no:
                tx = no.x + no.vx * PSO_OXYGEN_INTERCEPT_STEPS
                ty = no.y + no.vy * PSO_OXYGEN_INTERCEPT_STEPS
                dx, dy = _norm(tx - f.x, ty - f.y)
                vecs.append((ow, dx, dy))
        svx, svy, sc = 0, 0, 0
        rvx, rvy, rc = 0, 0, 0
        for o in alive:
            if o.fid == f.fid: continue
            d = _dist(f.x, f.y, o.x, o.y)
            if d < SELFISH_DISTANCE and d > 0.1:
                dx, dy = _norm(f.x - o.x, f.y - o.y)
                rvx += dx / d; rvy += dy / d; rc += 1
            elif d < SOCIAL_DISTANCE:
                svx += o.x - f.x; svy += o.y - f.y; sc += 1
        if sc > 0:
            dx, dy = _norm(svx / sc, svy / sc)
            vecs.append((PSO_SOCIAL_WEIGHT, dx, dy))
        if rc > 0:
            dx, dy = _norm(rvx, rvy)
            vecs.append((PSO_SELFISH_WEIGHT, dx, dy))
        for h in self.hazards:
            if h.kind == 'nh3':
                d = _dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    w = PSO_NH3_WEIGHT
                    if fr < 0.1 and any(o.alive and o.kind == 'food' and h.contains(o.x, o.y) for o in self.objs):
                        w = PSO_NH3_HUNGRY_OVERRIDE
                    dx, dy = _norm(f.x - h.x, f.y - h.y)
                    vecs.append((w, dx, dy))
        for h in self.hazards:
            if h.kind == 'disease':
                d = _dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    w = PSO_DISEASE_BOOSTING_WEIGHT if f.is_boosting else PSO_DISEASE_WEIGHT
                    dx, dy = _norm(f.x - h.x, f.y - h.y)
                    vecs.append((w, dx, dy))
        for h in self.hazards:
            if h.kind == 'parasite':
                d = _dist(f.x, f.y, h.x, h.y)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    dx, dy = _norm(f.x - h.x, f.y - h.y)
                    vecs.append((PSO_PARASITE_WEIGHT, dx, dy))
        f.is_running = False
        for o in alive:
            if o.fid == f.fid: continue
            if o.mouth_size > f.body_size:
                d = _dist(f.x, f.y, o.x, o.y)
                if 0.1 < d < SENSITIVE_DISTANCE:
                    f.is_running = True
                    w = PSO_RUN_WEIGHT * (SENSITIVE_DISTANCE / (d + 1))
                    dx, dy = _norm(f.x - o.x, f.y - o.y)
                    vecs.append((w, dx, dy))
        f.is_hunting = False
        if f.fullness <= 0:
            for o in alive:
                if o.fid == f.fid: continue
                if f.mouth_size > o.body_size:
                    d = _dist(f.x, f.y, o.x, o.y)
                    if d < SENSITIVE_DISTANCE and random.random() < CANNIBAL_TRIGGER_CHANCE:
                        f.is_hunting = True
                        w = PSO_HUNT_WEIGHT * (SENSITIVE_DISTANCE / (d + 1))
                        dx, dy = _norm(o.x - f.x, o.y - f.y)
                        vecs.append((w, dx, dy)); break
        if f.has_parasite:
            sv = self._scrub(f)
            if sv: vecs.append((PSO_RELIEF_WEIGHT, sv[0], sv[1]))
        return vecs

    def _scrub(self, f):
        bd, bo = float('inf'), None
        for o in self.obstacles:
            sx, sy = o.nearest_surface(f.x, f.y)
            d = _dist(f.x, f.y, sx, sy)
            if d < bd: bd, bo = d, o
        if bo:
            sx, sy = bo.nearest_surface(f.x, f.y)
            return _norm(sx - f.x, sy - f.y)
        return None

    def _flee(self, f, alive):
        fx, fy, c = 0, 0, 0
        for o in alive:
            if o.fid == f.fid: continue
            if o.mouth_size > f.body_size:
                d = _dist(f.x, f.y, o.x, o.y)
                if 0.1 < d < SENSITIVE_DISTANCE:
                    dx, dy = _norm(f.x - o.x, f.y - o.y)
                    fx += dx / (d + 1); fy += dy / (d + 1); c += 1
        return _norm(fx, fy) if c else None

    def _pursue(self, f, alive):
        bd, bt = float('inf'), None
        for o in alive:
            if o.fid == f.fid: continue
            if f.mouth_size > o.body_size:
                d = _dist(f.x, f.y, o.x, o.y)
                if d < SENSITIVE_DISTANCE and d < bd: bd, bt = d, o
        if bt: return _norm(bt.x - f.x, bt.y - f.y)
        return None

    def _cannibal(self):
        alive = [f for f in self.fish if f.alive]
        for f in alive:
            if not f.alive or not f.is_hunting: continue
            for t in alive:
                if t.fid == f.fid or not t.alive: continue
                if f.mouth_size > t.body_size:
                    if _dist(f.x, f.y, t.x, t.y) <= t.body_size * CANNIBAL_COLLISION_RADIUS_MULT:
                        t.hp = 0; t.alive = False
                        f.fullness = min(f.max_fullness, f.fullness + t.body_size * CANNIBAL_FULLNESS_GAIN_MULT)
                        f.is_hunting = False; break

    def _fecal(self):
        for f in self.fish:
            if not f.alive: continue
            f.fecal_timer += 1
            if f.fecal_timer >= FECAL_DROP_INTERVAL and f.fullness > 0:
                f.fecal_timer = 0
                if random.random() < (f.fullness / f.max_fullness) * FECAL_BASE_CHANCE:
                    stacked = False
                    for o in self.objs:
                        if o.alive and o.kind == 'fecal' and _dist(f.x, f.y, o.x, o.y) < FECAL_STACK_RADIUS:
                            o.value += FECAL_VALUE; stacked = True; break
                    if not stacked:
                        self.objs.append(DynObj(f.x + random.uniform(-3, 3), f.y + random.uniform(-3, 3),
                                               'fecal', FECAL_VALUE, max_age=FECAL_EXPIRE_TIMESTEPS))

    def _death(self):
        for f in self.fish:
            if not f.alive: continue
            if f.hp <= 0 or f.oxygen <= 0:
                f.alive = False
                self.objs.append(DynObj(f.x, f.y, 'dead_fish', f.body_size,
                                        max_age=DEAD_FISH_DECAY_TIMESTEPS))
                if f.is_infected:
                    self.hazards.append(Hazard(f.x, f.y, f.body_size * INFECTED_FISH_DISEASE_RADIUS_MULT,
                                              'disease', max_age=DISEASE_AREA_DECAY))

    def _frame(self):
        alive = [f for f in self.fish if f.alive]
        return {
            't': self.ts, 'day': self.ts // 24, 'hour': self.ts % 24,
            'fish': [f.snapshot() for f in alive],
            'objects': [{'x': round(o.x, 1), 'y': round(o.y, 1), 'type': o.kind,
                         'value': round(o.value, 1)} for o in self.objs if o.alive],
            'hazards': [{'x': round(h.x, 1), 'y': round(h.y, 1), 'r': round(h.radius, 1),
                         'type': h.kind} for h in self.hazards],
            'obstacles': [{'x': round(o.x, 1), 'y': round(o.y, 1), 'w': round(o.w, 1),
                           'h': round(o.h, 1)} for o in self.obstacles],
            'alive_count': len(alive), 'total_count': self.n0}


# ============================================================
# PARALLEL WORKER
# ============================================================

def _run_pond_worker(args):
    geno_dict, fish_data, runtime, max_budget, do_record, fskip, seed = args
    random.seed(seed)
    geno = PondGenotype(**geno_dict)
    fishes = []
    for fd in fish_data:
        f = Fish()
        for k, v in fd.items(): setattr(f, k, v)
        fishes.append(f)
    sim = PondSim(geno, fishes, runtime, max_budget, record=do_record, fskip=fskip)
    result = sim.run()
    result['genotype_obj_dict'] = geno_dict
    return result


def _fish_to_dict(f: Fish) -> dict:
    return {s: getattr(f, s) for s in [
        'fid', 'x', 'y', 'vx', 'vy', 'mouth_size', 'body_size',
        'hp', 'max_hp', 'energy', 'max_energy', 'fullness', 'max_fullness',
        'immunity', 'max_immunity', 'oxygen', 'max_oxygen', 'base_velocity',
        'is_boosting', 'boost_timer', 'is_infected', 'has_parasite',
        'is_running', 'is_hunting', 'alive', 'fecal_timer']}


# ============================================================
# CSV TRACKING
# ============================================================

CSV_HEADER = [
    'simulation', 'generation', 'pond', 'status',
    'fitness', 'survival_rate', 'healthiness', 'cost',
    'efficiency', 'alive_count', 'initial_count',
    'food_interval', 'food_quantity', 'food_location',
    'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
    'oxygen_interval', 'oxygen_duration', 'oxygen_location',
]


def _csv_row(sim_idx, gen_idx, pond_idx, status, result, genotype_dict):
    """Build one CSV row from a pond result."""
    return [
        sim_idx + 1,
        gen_idx + 1,
        pond_idx,
        status,
        f"{result.get('fitness', 0):.4f}",
        f"{result.get('survival_rate', 0):.4f}",
        f"{result.get('avg_healthiness', 0):.4f}",
        f"{result.get('cost', 0):.2f}",
        f"{result.get('efficiency', 0):.4f}",
        result.get('alive_count', 0),
        result.get('initial_count', 0),
        genotype_dict.get('food_interval', ''),
        genotype_dict.get('food_quantity', ''),
        genotype_dict.get('food_location', ''),
        genotype_dict.get('probiotic_interval', ''),
        genotype_dict.get('probiotic_quantity', ''),
        genotype_dict.get('probiotic_location', ''),
        genotype_dict.get('oxygen_interval', ''),
        genotype_dict.get('oxygen_duration', ''),
        genotype_dict.get('oxygen_location', ''),
    ]


# ============================================================
# EVOLUTIONARY ALGORITHM
# ============================================================

class EA:
    def __init__(self):
        self.runtime = RUNTIME
        self.csv_rows: List[list] = []  # Accumulate all rows, write once at end.

    def run(self, record_best=True):
        wall_start = _time.time()
        workers = NUM_WORKERS or max(1, multiprocessing.cpu_count())
        all_results = []
        self.csv_rows = []

        print(f"\n{'═' * 72}")
        print(f"  LARGEMOUTH BASS AQUACULTURE OPTIMIZER  —  PSO + EA")
        print(f"{'═' * 72}")
        print(f"  Fish: {INITIAL_FISH_POPULATION}  |  Days: {AQUACULTURE_DAYS}  |  "
              f"Budget: ${MAX_BUDGET:.2f}  |  Workers: {workers}")
        print(f"  Ponds/gen: {INITIAL_POND_COUNT}  |  Generations: {POND_GENERATIONS}  |  "
              f"Simulations: {RUN_SIMULATIONS}")
        print(f"{'═' * 72}")

        for sim_idx in range(RUN_SIMULATIONS):
            sim_start = _time.time()
            print(f"\n{'─' * 72}")
            print(f"  SIMULATION {sim_idx + 1}/{RUN_SIMULATIONS}")
            print(f"{'─' * 72}")

            base_fishes = [_make_fish(i) for i in range(INITIAL_FISH_POPULATION)]
            fish_data = [_fish_to_dict(f) for f in base_fishes]
            ponds = [PondGenotype.random() for _ in range(INITIAL_POND_COUNT)]
            best_result = None

            for gen in range(POND_GENERATIONS):
                if len(ponds) <= 1 and best_result is not None:
                    break

                is_last = (gen == POND_GENERATIONS - 1)
                do_rec = record_best and is_last and len(ponds) <= 4

                tasks = []
                for p_idx, geno in enumerate(ponds):
                    if geno.per_cycle_cost() > MAX_BUDGET:
                        tasks.append(None)
                    else:
                        seed = random.randint(0, 2 ** 31)
                        tasks.append((geno.to_dict(), fish_data, self.runtime,
                                      MAX_BUDGET, do_rec, FRAME_SKIP, seed))

                results = [None] * len(tasks)
                non_null = [(i, t) for i, t in enumerate(tasks) if t is not None]

                if non_null:
                    with ProcessPoolExecutor(max_workers=min(workers, len(non_null))) as pool:
                        futures = {pool.submit(_run_pond_worker, t): i for i, t in non_null}
                        for fut in as_completed(futures):
                            idx = futures[fut]
                            results[idx] = fut.result()

                gen_results = []
                for p_idx, geno in enumerate(ponds):
                    if results[p_idx] is None:
                        r = {
                            'fitness': 0.0, 'survival_rate': 0, 'avg_healthiness': 0,
                            'efficiency': 0, 'cost': geno.total_cost(self.runtime),
                            'genotype_obj': geno, 'genotype': geno.to_dict(),
                            'frames': [], 'budget_exceeded': True,
                            'alive_count': 0, 'initial_count': INITIAL_FISH_POPULATION,
                            'status': 'GATEKEEPER'}
                        gen_results.append(r)
                        self.csv_rows.append(_csv_row(sim_idx, gen, p_idx, 'GATEKEEPER', r, geno.to_dict()))
                    else:
                        r = results[p_idx]
                        r['genotype_obj'] = PondGenotype(**r['genotype_obj_dict'])
                        if r.get('budget_exceeded'):
                            r['status'] = 'OVER-BUDGET'
                            r['fitness'] = 0.0
                        elif r.get('survival_rate', 0) == 0:
                            r['status'] = 'ALL-DEAD'
                        else:
                            r['status'] = 'OK'
                        gen_results.append(r)
                        self.csv_rows.append(_csv_row(sim_idx, gen, p_idx, r['status'], r, r['genotype']))

                gen_results.sort(key=lambda x: x['fitness'], reverse=True)

                # Print table
                print(f"\n  Gen {gen + 1:>2}/{POND_GENERATIONS} │ {len(ponds)} ponds")
                print(f"  {'#':>3} │ {'Fitness':>8} │ {'Survival':>9} │ {'Healthiness':>11} │ "
                      f"{'Cost':>12} │ {'Status':>11}")
                print(f"  {'─' * 3}─┼─{'─' * 8}─┼─{'─' * 9}─┼─{'─' * 11}─┼─{'─' * 12}─┼─{'─' * 11}")
                for i, r in enumerate(gen_results):
                    fit_s = f"{r['fitness']:.4f}"
                    sur_s = f"{r['survival_rate'] * 100:06.2f}%"
                    hlt_s = f"{r.get('avg_healthiness', 0):.4f}"
                    cst_s = f"${r['cost']:>10.2f}"
                    st = r.get('status', '?')
                    if st == 'GATEKEEPER':   st_s = '🚫 GATE'
                    elif st == 'OVER-BUDGET': st_s = '💸 OVER$'
                    elif st == 'ALL-DEAD':    st_s = '💀 DEAD'
                    else:                     st_s = '✅ OK'
                    print(f"  {i:>3} │ {fit_s:>8} │ {sur_s:>9} │ {hlt_s:>11} │ {cst_s:>12} │ {st_s:>11}")

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
                    child.mutate()
                    new_ponds.append(child)
                ponds = new_ponds

            sim_elapsed = _time.time() - sim_start
            if best_result:
                best_result['simulation_idx'] = sim_idx
                all_results.append(best_result)
                print(f"\n  ▸ Sim {sim_idx + 1} best: Fitness={best_result['fitness']:.4f}  "
                      f"Survival={best_result['survival_rate'] * 100:06.2f}%  "
                      f"({sim_elapsed:.1f}s)")
            else:
                print(f"\n  ▸ Sim {sim_idx + 1}: No survivors. ({sim_elapsed:.1f}s)")

        # Write CSV
        self._write_csv()

        if not all_results:
            print("\n  ❌ No valid results across all simulations.")
            return None

        all_results.sort(key=lambda x: x['fitness'], reverse=True)
        champ = all_results[0]

        if record_best and not champ.get('frames'):
            print("\n  🔄 Re-running champion with frame recording...")
            base_fishes = [_make_fish(i) for i in range(INITIAL_FISH_POPULATION)]
            geno = PondGenotype(**champ['genotype'])
            sim = PondSim(geno, base_fishes, self.runtime, MAX_BUDGET, record=True, fskip=FRAME_SKIP)
            res = sim.run()
            champ['frames'] = res['frames']
            champ['fitness'] = res['fitness']
            champ['survival_rate'] = res['survival_rate']
            champ['avg_healthiness'] = res['avg_healthiness']
            champ['cost'] = res['cost']
            champ['efficiency'] = res['efficiency']

        wall_elapsed = _time.time() - wall_start
        loc_names = {0: 'Middle', 1: 'Corner', 2: 'Random'}
        g = champ['genotype']

        print(f"\n{'═' * 72}")
        print(f"  🏆  CHAMPION POND  (Simulation {champ.get('simulation_idx', 0) + 1})")
        print(f"{'═' * 72}")
        print(f"  {'Metric':<20} {'Value':>15}")
        print(f"  {'─' * 20}─{'─' * 15}")
        print(f"  {'Fitness':<20} {champ['fitness']:>15.4f}")
        print(f"  {'Survival':<20} {champ['survival_rate'] * 100:>14.2f}%")
        print(f"  {'Healthiness':<20} {champ.get('avg_healthiness', 0):>15.4f}")
        print(f"  {'Efficiency':<20} {champ['efficiency']:>15.4f}")
        print(f"  {'Total Cost':<20} ${champ['cost']:>13.2f}")
        print(f"  {'─' * 20}─{'─' * 15}")
        print(f"  {'Food Interval':<20} {g['food_interval']:>12}  h")
        print(f"  {'Food Quantity':<20} {g['food_quantity']:>12}  pellets")
        print(f"  {'Food Location':<20} {loc_names[g['food_location']]:>15}")
        print(f"  {'Probiotic Interval':<20} {g['probiotic_interval']:>12}  h")
        print(f"  {'Probiotic Quantity':<20} {g['probiotic_quantity']:>12}  pellets")
        print(f"  {'Probiotic Location':<20} {loc_names[g['probiotic_location']]:>15}")
        print(f"  {'O₂ Interval':<20} {g['oxygen_interval']:>12}  h")
        print(f"  {'O₂ Duration':<20} {g['oxygen_duration']:>12}  h")
        print(f"  {'O₂ Location':<20} {loc_names[g['oxygen_location']]:>15}")
        print(f"  {'─' * 20}─{'─' * 15}")
        print(f"  Total wall time: {wall_elapsed:.1f}s")

        return champ

    def _write_csv(self):
        with open(RESULTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerows(self.csv_rows)
        print(f"\n  📊 Saved {RESULTS_CSV_PATH} ({len(self.csv_rows)} rows)")


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
        print(f"\n  📁 Saved simulation_data.json ({len(champ['frames'])} frames)")
        print(f"  🌐 Open visualization.html in browser (via local server)")
    else:
        print("\n  ⚠  No frames to export.")


if __name__ == '__main__':
    main()