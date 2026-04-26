#!/usr/bin/env python3
"""
constants.py -- All configuration constants for the aquaculture simulation.
"""

from enum import IntEnum
from pathlib import Path

# ╔══════════════════════════════════════════════════════════════╗
# ║                    PROJECT PATHS                            ║
# ╚══════════════════════════════════════════════════════════════╝

PROJECT_ROOT = Path(__file__).resolve().parent.parent
RESULTS_CSV_PATH = str(PROJECT_ROOT / 'logs' / 'results.csv')
SIMULATION_JSON_PATH = str(PROJECT_ROOT / 'logs' / 'simulation_data.json')
PLOTS_DIR = str(PROJECT_ROOT / 'plots')

# ╔══════════════════════════════════════════════════════════════╗
# ║                    USER CONFIGURATION                       ║
# ╚══════════════════════════════════════════════════════════════╝

MAX_BUDGET = 300.0
INITIAL_FISH_POPULATION = 30
AQUACULTURE_DAYS = 60
POND_GENERATIONS = 20
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
POND_DEPTH = 50.0

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
FULLNESS_DECAY = 0.10
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
IMMUNITY_REGEN = 0.02
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
DISEASE_AREA_DECAY = 36
PARASITE_AREA_DECAY = 36
POLLUTANT_TO_HAZARD_TIMESTEPS = 48
DISEASE_AREA_RADIUS_DECAY = 0.990

# ╔══════════════════════════════════════════════════════════════╗
# ║                 POLLUTANT TRANSFORMATION                    ║
# ╚══════════════════════════════════════════════════════════════╝

POLLUTANT_TO_NH3_CHANCE = 0.25
POLLUTANT_TO_DISEASE_CHANCE = 0.10
POLLUTANT_TO_PARASITE_CHANCE = 0.10
POLLUTANT_TO_BOTH_CHANCE = 0.05
POLLUTANT_TO_PLANT_CHANCE = 0.10
POLLUTANT_TO_OBSTACLE_CHANCE = 0.25
POLLUTANT_RADIUS_SCALE = 1.5
DEAD_FISH_POLLUTANT_MULT = 1.5
POLLUTANT_OBSTACLE_AREA_RANGE = (3, 8)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FOOD & HEALING GAINS                        ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_ENERGY_GAIN = 25.0
FOOD_FULLNESS_GAIN = 20.0
FOOD_VALUE = 5.0
PROBIOTIC_VALUE = 3.0
PROBIOTIC_IMMUNITY_GAIN = 40.0
OXYGEN_BUBBLE_GAIN = 30.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 NATURAL SPAWN RATES                         ║
# ╚══════════════════════════════════════════════════════════════╝

NATURAL_OXYGEN_SPAWN_RATE = 0.12
NATURAL_NH3_SPAWN_RATE = 0.015
OXYGEN_BUBBLES_PER_PUMP = 7

# ╔══════════════════════════════════════════════════════════════╗
# ║                 ENVIRONMENT OBJECTS                         ║
# ╚══════════════════════════════════════════════════════════════╝

NUM_OBSTACLES = 15
OBSTACLE_MAX_DIM_FRAC = 0.10
OBSTACLE_AREA_RANGE = (30, 150)
OBSTACLE_ASPECT_RANGE = (0.3, 3.0)
OBSTACLE_DEPTH_RANGE = (5.0, 15.0)
OXYGEN_BUBBLE_SPEED = 0.5
NH3_AREA_RADIUS_RANGE = (6.0, 14.0)
NH3_AREA_SPEED = 0.2

# ╔══════════════════════════════════════════════════════════════╗
# ║                 SINKING MECHANICS                           ║
# ╚══════════════════════════════════════════════════════════════╝

SINK_SPEED = 0.3
SINK_SPEED_HEAVY = 0.6

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FLOOR HAZARD MECHANICS                      ║
# ╚══════════════════════════════════════════════════════════════╝

FLOOR_HAZARD_HEIGHT = 8.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FECAL MECHANICS                             ║
# ╚══════════════════════════════════════════════════════════════╝

FECAL_DROP_INTERVAL = 2
FECAL_BASE_CHANCE = 0.2
FECAL_VALUE = 2.0
FECAL_STACK_RADIUS = 10.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 CANNIBALISM MECHANICS                       ║
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
PSO_PARASITE_WEIGHT = 3.0
PSO_RELIEF_WEIGHT = 4.0
PSO_RUN_WEIGHT = 5.0
PSO_OBSTACLE_WEIGHT = 2.0

STATE_OVERRIDE_PARASITE_CHANCE = 0.6

# ╔══════════════════════════════════════════════════════════════╗
# ║                 EA / MISC                                   ║
# ╚══════════════════════════════════════════════════════════════╝

EA_MUTATION_RATE = 0.25
FISH_EAT_RANGE = 3.0
INFECTED_FISH_DISEASE_RADIUS_MULT = 1.5

# ════════════════════════════════════════════════════════════════
#  DERIVED (do not edit)
# ════════════════════════════════════════════════════════════════

RUNTIME = AQUACULTURE_DAYS * 24
LOC_NAMES = {0: 'Middle', 1: 'Corner', 2: 'Random'}

FOOD_QUANTITY_RANGE = (1, 5)
FOOD_INTERVAL_RANGE = (2, 24)

OBSTACLE_MAX_WIDTH = POND_WIDTH * OBSTACLE_MAX_DIM_FRAC
OBSTACLE_MAX_HEIGHT = POND_HEIGHT * OBSTACLE_MAX_DIM_FRAC
OBSTACLE_MAX_DEPTH = POND_DEPTH * OBSTACLE_MAX_DIM_FRAC


class DropLocation(IntEnum):
    MIDDLE = 0
    CORNER = 1
    RANDOM = 2