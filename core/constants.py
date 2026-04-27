#!/usr/bin/env python3
"""
constants.py -- All configuration constants for the aquaculture simulation.
"""

from enum import IntEnum
from pathlib import Path
import math

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

MAX_BUDGET = 500.0
AQUACULTURE_DAYS = 60
POND_GENERATIONS = 20
RUN_TIMELINES = 3
INITIAL_POND_COUNT = 10
FRAME_SKIP = 1
NUM_WORKERS = None
MAX_FISH_COUNT = 50

# ╔══════════════════════════════════════════════════════════════╗
# ║                    ECONOMIC CONSTANTS                       ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_PRICE = 0.05
PROBIOTIC_PRICE = 0.75
OXYGEN_PRICE = 2.50

# ╔══════════════════════════════════════════════════════════════╗
# ║                  EA FITNESS WEIGHTS                         ║
# ╚══════════════════════════════════════════════════════════════╝

W1_YIELD = 0.55
W2_SAVING = 0.33
W3_HEALTHINESS = 0.12

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

HP_RANGE = (80.0, 100.0)
ENERGY_RANGE = (60.0, 100.0)
FULLNESS_RANGE = (50.0, 100.0)
IMMUNITY_RANGE = (70.0, 100.0)
OXYGEN_RANGE = (80.0, 100.0)
VELOCITY_RANGE = (2.0, 6.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                   PSO DISTANCE RADII                        ║
# ╚══════════════════════════════════════════════════════════════╝

SENSITIVE_DISTANCE = 40.0
SOCIAL_DISTANCE = 60.0
SELFISH_DISTANCE = 10.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                STAT DECAY RATES (PER TIMESTEP)              ║
# ╚══════════════════════════════════════════════════════════════╝

OXYGEN_DECAY = 0.10
OXYGEN_DECAY_NH3_MULT = 2.0
OXYGEN_PASSIVE_REGEN = 0.04
ENERGY_DECAY = 0.10
FULLNESS_DECAY = 0.15
ENERGY_COST_MOVE = 0.06

# ╔══════════════════════════════════════════════════════════════╗
# ║              HP DRAIN RATES (WHEN STATS DEPLETED)           ║
# ╚══════════════════════════════════════════════════════════════╝

HP_DECAY_NO_ENERGY = 0.4
HP_DECAY_NO_FULLNESS = 1.0
HP_DECAY_INFECTED = 0.6
HP_DECAY_PARASITE = 0.8
HP_DECAY_IN_NH3 = 0.3

# ╔══════════════════════════════════════════════════════════════╗
# ║              HP REGEN                                       ║
# ╚══════════════════════════════════════════════════════════════╝

HP_REGEN = 0.1

# ╔══════════════════════════════════════════════════════════════╗
# ║              DISEASE & PARASITE MECHANICS                   ║
# ╚══════════════════════════════════════════════════════════════╝

IMMUNITY_DECAY_IN_DISEASE = 1.5
IMMUNITY_REGEN = 0.02
DISEASE_SELF_CURE_CHANCE = 0.08
PARASITE_CONTACT_CHANCE = 0.05
PARASITE_FULLNESS_EFFICIENCY = 0.5
PARASITE_EXTRA_FULLNESS_DRAIN = 1.5
PARASITE_EXTRA_ENERGY_DRAIN = 1.5
PARASITE_VELOCITY_MULT = 0.75
PARASITE_SCRUB_CHANCE = 0.03

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

POLLUTANT_TO_NH3_CHANCE = 0.30
POLLUTANT_TO_DISEASE_CHANCE = 0.10
POLLUTANT_TO_PARASITE_CHANCE = 0.10
POLLUTANT_TO_BOTH_CHANCE = 0.05
POLLUTANT_TO_PLANT_CHANCE = 0.10
POLLUTANT_TO_OBSTACLE_CHANCE = 0.20
POLLUTANT_RADIUS_SCALE = 1.5
DEAD_FISH_POLLUTANT_MULT = 1.5
POLLUTANT_OBSTACLE_AREA_RANGE = (3, 8)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 DEAD FISH NH3                               ║
# ╚══════════════════════════════════════════════════════════════╝

DEAD_FISH_NH3_RADIUS = 10.0

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
NATURAL_NH3_SPAWN_RATE = 0.04
OXYGEN_BUBBLES_PER_PUMP = 10

# ╔══════════════════════════════════════════════════════════════╗
# ║                 ENVIRONMENT OBJECTS                         ║
# ╚══════════════════════════════════════════════════════════════╝

OBSTACLE_DENSITY_FACTOR = 0.15
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

FLOOR_HAZARD_HEIGHT = 12.0

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

CANNIBAL_FULLNESS_THRESHOLD = 0.7
CANNIBAL_BASE_CHANCE = 0.2
CANNIBAL_HUNGER_MULT = 0.5
CANNIBAL_FULLNESS_GAIN_MULT = 2.0
CANNIBAL_COLLISION_RADIUS_MULT = 2.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 PSO VECTOR WEIGHTS                          ║
# ╚══════════════════════════════════════════════════════════════╝

PSO_INERTIA = 0.4
PSO_FOOD_WEIGHT = 3.0
PSO_FOOD_URGENT_MULT = 2.0
PSO_PROBIOTIC_WEIGHT = 1.5
PSO_OXYGEN_WEIGHT = 2.0
PSO_OXYGEN_CRITICAL_MULT = 2.0
PSO_OXYGEN_THRESHOLD = 0.7
PSO_OXYGEN_CRITICAL_THRESHOLD = 0.3
PSO_OXYGEN_INTERCEPT_STEPS = 3
PSO_SOCIAL_WEIGHT = 1.5
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
EA_ELITISM_COUNT = max(1, round(0.2 * INITIAL_POND_COUNT))
EA_TOURNAMENT_K = max(2, round(0.4 * INITIAL_POND_COUNT))
FISH_EAT_RANGE = 3.0
INFECTED_FISH_DISEASE_RADIUS_MULT = 1.5

# ╔══════════════════════════════════════════════════════════════╗
# ║                 PROBIOTIC POLICY RANGES                     ║
# ╚══════════════════════════════════════════════════════════════╝

PROBIOTIC_QUANTITY_RANGE = (1, 5)
PROBIOTIC_INTERVAL_STEPS = list(range(24, 169, 12))

# ════════════════════════════════════════════════════════════════
#  DERIVED (do not edit)
# ════════════════════════════════════════════════════════════════

RUNTIME = AQUACULTURE_DAYS * 24
LOC_NAMES = {
    0: 'Center', 1: 'Top-Left', 2: 'Top-Right', 3: 'Bot-Left', 4: 'Bot-Right',
    5: 'Top-Center', 6: 'Bot-Center', 7: 'Left-Center', 8: 'Right-Center', 9: 'Random'
}

FOOD_QUANTITY_RANGE = (5, 20)
FOOD_INTERVAL_RANGE = (2, 24)

OBSTACLE_MAX_WIDTH = POND_WIDTH * OBSTACLE_MAX_DIM_FRAC
OBSTACLE_MAX_HEIGHT = POND_HEIGHT * OBSTACLE_MAX_DIM_FRAC
OBSTACLE_MAX_DEPTH = POND_DEPTH * OBSTACLE_MAX_DIM_FRAC

NUM_OBSTACLES = max(5, round(math.sqrt(POND_WIDTH * POND_HEIGHT) * OBSTACLE_DENSITY_FACTOR))


class DropLocation(IntEnum):
    CENTER = 0
    TOP_LEFT = 1
    TOP_RIGHT = 2
    BOT_LEFT = 3
    BOT_RIGHT = 4
    TOP_CENTER = 5
    BOT_CENTER = 6
    LEFT_CENTER = 7
    RIGHT_CENTER = 8
    RANDOM = 9