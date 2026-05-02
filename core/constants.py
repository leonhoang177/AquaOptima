#!/usr/bin/env python3
"""
constants.py -- All configuration constants for the aquaculture simulation.
Organized by category. Derived values at the bottom.
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
NUM_WORKERS = None

# ╔══════════════════════════════════════════════════════════════╗
# ║                    EA CONFIGURATION                         ║
# ╚══════════════════════════════════════════════════════════════╝

MAX_BUDGET = 200.0
AQUACULTURE_DAYS = 20
POND_GENERATIONS = 5
RUN_TIMELINES = 2
POND_POPULATION = 15
FRAME_SKIP = 1
EA_MUTATION_RATE = 0.25
EA_ELITISM_COUNT = max(1, round(0.2 * POND_POPULATION))
EA_TOURNAMENT_K = max(2, round(0.4 * POND_POPULATION))

# ╔══════════════════════════════════════════════════════════════╗
# ║                 EA POLICY RANGES                            ║
# ║  Ranges the EA can explore for genotype parameters.         ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_QUANTITY_RANGE = (6, 30)
FOOD_INTERVAL_RANGE = (3, 24)
PROBIOTIC_QUANTITY_RANGE = (1, 5)
PROBIOTIC_INTERVAL_STEPS = list(range(24, 169, 12))
OXYGEN_DURATION_RANGE = (1, 4)
OXYGEN_INTERVAL_RANGE = (1, 24)


# ╔══════════════════════════════════════════════════════════════╗
# ║                 FITNESS WEIGHTS                             ║
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
# ║                    FISH POPULATION                          ║
# ║  MAX_FISH_COUNT scales with pond size via cube-root.        ║
# ║  FISH_DENSITY_K=0.55 gives ~50 fish for 200×75×50 pond.    ║
# ╚══════════════════════════════════════════════════════════════╝

FISH_DENSITY_K = 0.55
MAX_FISH_COUNT = max(10, int(FISH_DENSITY_K * (POND_WIDTH * POND_HEIGHT * POND_DEPTH) ** (1/3)))

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH TRAITS (FIXED AT BIRTH)                ║
# ╚══════════════════════════════════════════════════════════════╝

MOUTH_SIZE_RANGE = (3.0, 8.0)
BODY_SIZE_RANGE = (4.0, 10.0)
VELOCITY_RANGE = (3.0, 9.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH STATS (DYNAMIC)                        ║
# ╚══════════════════════════════════════════════════════════════╝

HEALTH_RANGE = (80.0, 100.0)
FULLNESS_RANGE = (50.0, 100.0)
IMMUNITY_RANGE = (70.0, 100.0)
OXYGEN_RANGE = (80.0, 100.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 STAT DECAY (PER TIMESTEP)                   ║
# ╚══════════════════════════════════════════════════════════════╝

OXYGEN_DECAY = 0.22
OXYGEN_DECAY_NH3_MULT = 3.0
OXYGEN_PASSIVE_REGEN = 0.03
FULLNESS_DECAY = 0.08
FULLNESS_COST_MOVE = 0.16

# ╔══════════════════════════════════════════════════════════════╗
# ║                 HEALTH DECAY & REGEN                        ║
# ╚══════════════════════════════════════════════════════════════╝

HEALTH_DECAY_NO_FULLNESS = 2.5
HEALTH_DECAY_INFECTED = 0.6
HEALTH_DECAY_PARASITE = 0.8
HEALTH_DECAY_IN_NH3 = 0.3
HEALTH_REGEN = 0.02

# ╔══════════════════════════════════════════════════════════════╗
# ║                 VELOCITY REDUCTION                          ║
# ╚══════════════════════════════════════════════════════════════╝

VELOCITY_HEALTH_THRESHOLD = 0.5
VELOCITY_FULLNESS_THRESHOLD = 0.5

# ╔══════════════════════════════════════════════════════════════╗
# ║                 DISEASE & PARASITE                          ║
# ╚══════════════════════════════════════════════════════════════╝

IMMUNITY_DECAY_IN_DISEASE = 10.0
IMMUNITY_DECAY_IN_NH3 = 7.0
IMMUNITY_REGEN = 0.02
DISEASE_SELF_CURE_CHANCE = 0.08
PARASITE_CONTACT_CHANCE = 0.35
PARASITE_FULLNESS_EFFICIENCY = 0.5
PARASITE_EXTRA_FULLNESS_DRAIN = 2.0
PARASITE_VELOCITY_MULT = 0.75

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FOOD & CONSUMABLES                          ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_VALUE = 5.0
FOOD_FULLNESS_GAIN = 20.0
FOOD_DRIFT_SPEED = 0.15

PROBIOTIC_VALUE = 3.0
PROBIOTIC_IMMUNITY_GAIN = 40.0
PROBIOTIC_DRIFT_SPEED = 0.12

OXYGEN_BUBBLE_GAIN = 30.0
OXYGEN_BUBBLE_SPEED = 0.5
OXYGEN_BUBBLES_PER_PUMP = 10

# ╔══════════════════════════════════════════════════════════════╗
# ║                 ECONOMIC (PRICES)                           ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_PRICE = 0.05
PROBIOTIC_PRICE = 0.75
OXYGEN_PRICE = 2.50

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
# ║                 SINKING & FLOATING                          ║
# ╚══════════════════════════════════════════════════════════════╝

SINK_SPEED = 0.3
SINK_SPEED_HEAVY = 0.6

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FECAL                                       ║
# ╚══════════════════════════════════════════════════════════════╝

FECAL_DROP_INTERVAL = 3
FECAL_BASE_CHANCE = 0.05
FECAL_VALUE = 3.0
FECAL_SINK_SPEED = 0.4
MAX_SINKING_FECAL = 50

# ╔══════════════════════════════════════════════════════════════╗
# ║                 DEAD FISH                                   ║
# ╚══════════════════════════════════════════════════════════════╝

DEAD_FISH_NH3_RADIUS = 12.0
DEAD_FISH_FLOAT_CHANCE = 0.40
DEAD_FISH_FLOAT_DURATION_RANGE = (24, 72)
DEAD_FISH_FLOAT_SPEED = 0.4
DEAD_FISH_POLLUTANT_MULT = 3.0
INFECTED_FISH_DISEASE_RADIUS_MULT = 5.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 CANNIBALISM                                 ║
# ╚══════════════════════════════════════════════════════════════╝

CANNIBAL_FULLNESS_THRESHOLD = 0.7
CANNIBAL_BASE_CHANCE = 0.25
CANNIBAL_HUNGER_MULT = 0.80
CANNIBAL_FULLNESS_GAIN_MULT = 2.0
CANNIBAL_COLLISION_RADIUS_MULT = 1.2

# ╔══════════════════════════════════════════════════════════════╗
# ║                 POLLUTANT TRANSFORMATION                    ║
# ║  Chances sum to 1.0 (100%).                                 ║
# ║  Final slice = harmless decomposition (fallthrough).        ║
# ╚══════════════════════════════════════════════════════════════╝

POLLUTANT_TO_NH3_CHANCE = 0.30
POLLUTANT_TO_DISEASE_CHANCE = 0.10
POLLUTANT_TO_PARASITE_CHANCE = 0.10
POLLUTANT_TO_BOTH_CHANCE = 0.05
POLLUTANT_TO_PLANT_CHANCE = 0.10
POLLUTANT_TO_OBSTACLE_CHANCE = 0.20
POLLUTANT_TO_NOTHING_CHANCE = 0.15
POLLUTANT_RADIUS_SCALE = 1.5
POLLUTANT_OBSTACLE_AREA_RANGE = (3, 8)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 NH3 HAZARD                                  ║
# ╚══════════════════════════════════════════════════════════════╝

NH3_BUBBLE_SPEED = 0.4
NH3_AREA_RADIUS_RANGE = (6.0, 14.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 NATURAL SPAWN RATES                         ║
# ╚══════════════════════════════════════════════════════════════╝

NATURAL_OXYGEN_SPAWN_RATE = 0.12
NATURAL_NH3_SPAWN_RATE = 0.04

# ╔══════════════════════════════════════════════════════════════╗
# ║                 OBSTACLES                                   ║
# ╚══════════════════════════════════════════════════════════════╝

OBSTACLE_DENSITY_FACTOR = 0.15
OBSTACLE_MAX_DIM_FRAC = 0.10
OBSTACLE_AREA_RANGE = (30, 150)
OBSTACLE_ASPECT_RANGE = (0.3, 3.0)
OBSTACLE_DEPTH_RANGE = (5.0, 15.0)

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FLOOR MECHANICS                             ║
# ╚══════════════════════════════════════════════════════════════╝

FLOOR_HAZARD_HEIGHT = 15
STACK_RADIUS = 5.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 PSO DISTANCE RADII                          ║
# ╚══════════════════════════════════════════════════════════════╝

SENSITIVE_DISTANCE = 30.0
SOCIAL_DISTANCE = 60.0
SELFISH_DISTANCE = 10.0
FISH_EAT_RANGE = 3.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 PSO VECTOR WEIGHTS                          ║
# ╚══════════════════════════════════════════════════════════════╝

PSO_INERTIA = 0.4

PSO_FOOD_WEIGHT = 3.0
PSO_FOOD_URGENT_MULT = 2.5
PSO_FOOD_URGENT_THRESHOLD = 0.5

PSO_PROBIOTIC_WEIGHT = 1.5

PSO_OXYGEN_WEIGHT = 2.2
PSO_OXYGEN_CRITICAL_MULT = 2.0
PSO_OXYGEN_THRESHOLD = 0.7
PSO_OXYGEN_CRITICAL_THRESHOLD = 0.3
PSO_OXYGEN_INTERCEPT_STEPS = 3

PSO_SOCIAL_WEIGHT = 2.2
PSO_SELFISH_WEIGHT = 1.5

PSO_NH3_WEIGHT = 3.5
PSO_NH3_HUNGRY_OVERRIDE = 0.5
PSO_DISEASE_WEIGHT = 2.2
PSO_PARASITE_WEIGHT = 2.5

PSO_RUN_WEIGHT = 5.0
PSO_OBSTACLE_WEIGHT = 2.0

PSO_SWARM_HUNGRY_WEIGHT = 3.5
PSO_SWARM_HUNGRY_THRESHOLD = 0.7

# ╔══════════════════════════════════════════════════════════════╗
# ║                 DROP LOCATIONS                              ║
# ╚══════════════════════════════════════════════════════════════╝

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

LOC_NAMES = {
    0: 'Center', 1: 'Top-Left', 2: 'Top-Right', 3: 'Bot-Left', 4: 'Bot-Right',
    5: 'Top-Center', 6: 'Bot-Center', 7: 'Left-Center', 8: 'Right-Center', 9: 'Random'
}

# ════════════════════════════════════════════════════════════════
#  DERIVED CONSTANTS (do not edit directly)
# ════════════════════════════════════════════════════════════════

RUNTIME = AQUACULTURE_DAYS * 24

OBSTACLE_MAX_WIDTH = POND_WIDTH * OBSTACLE_MAX_DIM_FRAC
OBSTACLE_MAX_HEIGHT = POND_HEIGHT * OBSTACLE_MAX_DIM_FRAC
OBSTACLE_MAX_DEPTH = POND_DEPTH * OBSTACLE_MAX_DIM_FRAC

NUM_OBSTACLES = max(5, round(math.sqrt(POND_WIDTH * POND_HEIGHT) * OBSTACLE_DENSITY_FACTOR))