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
DEMO_LOG_PATH = str(PROJECT_ROOT / 'logs' / 'demo.txt')
PLOTS_DIR = str(PROJECT_ROOT / 'plots')
NUM_WORKERS = None

# ╔══════════════════════════════════════════════════════════════╗
# ║                    EA CONFIGURATION                         ║
# ╚══════════════════════════════════════════════════════════════╝

AQUACULTURE_DAYS = 10
POND_GENERATIONS = 3
RUN_TIMELINES = 3
POND_POPULATION = 3
FRAME_SKIP = 1
EA_CROSSOVER_RATE = 0.80
EA_MUTATION_RATE = 0.25
EA_ELITISM_COUNT = max(1, round(0.1 * POND_POPULATION))
EA_TOURNAMENT_K = max(5, round(0.5 * POND_POPULATION))

# ╔══════════════════════════════════════════════════════════════╗
# ║              VERIFICATION CONSTANTS (Option F)              ║
# ╚══════════════════════════════════════════════════════════════╝

VERIFY_MIN_SAMPLES = 3          # Minimum samples for Wilcoxon test
VERIFY_ALPHA = 0.05             # Significance level
VERIFY_MAX_CASCADE_DEPTH = 3    # Max candidates to verify in cascade
VERIFY_SKIP_THRESHOLD = 0.10    # Skip verification if averages differ this much

# ╔══════════════════════════════════════════════════════════════╗
# ║                 EA POLICY RANGES                            ║
# ║  Ranges the EA can explore for genotype parameters.         ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_QUANTITY_RANGE = (1, 10)
FOOD_INTERVAL_RANGE = (1, 24)
PROBIOTIC_QUANTITY_RANGE = (0, 4)
PROBIOTIC_INTERVAL_STEPS = list(range(12, 169, 12))
OXYGEN_DURATION_RANGE = (1, 3)
OXYGEN_INTERVAL_RANGE = (1, 24)

# Binary location options: Center (0) or Random (9)
LOCATION_OPTIONS = [0, 9]


# ╔══════════════════════════════════════════════════════════════╗
# ║                 FITNESS WEIGHTS                             ║
# ║  fitness = W1 * survival_rate + W2 * saving_rate            ║
# ║          + W3 * healthiness                                 ║
# ╚══════════════════════════════════════════════════════════════╝

W1_SURVIVAL_RATE = 0.55
W2_SAVING_RATE = 0.33
W3_HEALTHINESS = 0.12

# ╔══════════════════════════════════════════════════════════════╗
# ║                    POND DIMENSIONS                          ║
# ╚══════════════════════════════════════════════════════════════╝

POND_WIDTH = 180.0
POND_HEIGHT = 85.0
POND_DEPTH = 50.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                    FISH POPULATION                          ║
# ║  INITIAL_FISH_COUNT scales with pond size via cube-root.    ║
# ║  FISH_DENSITY_K=0.55 gives ~50 fish for 200×75×50 pond.    ║
# ╚══════════════════════════════════════════════════════════════╝

FISH_DENSITY_K = 0.55
INITIAL_FISH_COUNT = max(10, int(FISH_DENSITY_K * (POND_WIDTH * POND_HEIGHT * POND_DEPTH) ** (1/3)))

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FISH TRAITS (FIXED AT BIRTH)                ║
# ╚══════════════════════════════════════════════════════════════╝

MOUTH_SIZE_RANGE = (3.0, 8.0)
BODY_SIZE_RANGE = (4.0, 10.0)
VELOCITY_RANGE = (4.0, 10.0)

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

OXYGEN_DECAY = 0.25
OXYGEN_DECAY_NH3_MULT = 3.0
OXYGEN_PASSIVE_REGEN = 0.03
FULLNESS_DECAY = 0.05
FULLNESS_COST_MOVE = 0.10

# ╔══════════════════════════════════════════════════════════════╗
# ║                 HEALTH DECAY & REGEN                        ║
# ╚══════════════════════════════════════════════════════════════╝

HEALTH_DECAY_NO_FULLNESS = 1.0
HEALTH_DECAY_INFECTED = 0.6
HEALTH_DECAY_PARASITE = 0.8
HEALTH_DECAY_IN_NH3 = 0.3
HEALTH_REGEN = 0.02

# ╔══════════════════════════════════════════════════════════════╗
# ║                 VELOCITY REDUCTION                          ║
# ╚══════════════════════════════════════════════════════════════╝

VELOCITY_HEALTH_THRESHOLD = 0.40
VELOCITY_FULLNESS_THRESHOLD = 0.33

# ╔══════════════════════════════════════════════════════════════╗
# ║                 DISEASE & PARASITE                          ║
# ╚══════════════════════════════════════════════════════════════╝

IMMUNITY_DECAY_IN_DISEASE = 18.0
IMMUNITY_DECAY_IN_NH3 = 6.0
IMMUNITY_REGEN = 0.02
DISEASE_SELF_CURE_CHANCE = 0.05
PARASITE_CONTACT_CHANCE = 0.25
PARASITE_FULLNESS_EFFICIENCY = 0.3
PARASITE_EXTRA_FULLNESS_DRAIN = 1.5
PARASITE_VELOCITY_MULT = 0.75

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FOOD & CONSUMABLES                          ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_VALUE = 5.0
FOOD_FULLNESS_GAIN = 5.0
FOOD_DRIFT_SPEED = 0.15

PROBIOTIC_VALUE = 3.0
PROBIOTIC_IMMUNITY_GAIN = 30.0
PROBIOTIC_DRIFT_SPEED = 0.12

OXYGEN_BUBBLE_GAIN = 20.0
OXYGEN_BUBBLE_SPEED = 0.5
OXYGEN_BUBBLES_PER_PUMP = 10

# ╔══════════════════════════════════════════════════════════════╗
# ║                 ECONOMIC (PRICES)                           ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_PRICE = 0.10
PROBIOTIC_PRICE = 0.50
OXYGEN_PRICE = 1.50
MAX_BUDGET = 1000

# ╔══════════════════════════════════════════════════════════════╗
# ║                 OBJECT LIFETIMES (TIMESTEPS)                ║
# ║  Scaled for 30-day simulation (~720 timesteps).             ║
# ║  Halved from original 60-day design to see 2-3 full         ║
# ║  object lifecycles within the simulation window.            ║
# ╚══════════════════════════════════════════════════════════════╝

FOOD_EXPIRE_TIMESTEPS = 12          # 1 day  (was 48)
PROBIOTIC_EXPIRE_TIMESTEPS = 6     # 12h    (was 18)
FECAL_EXPIRE_TIMESTEPS = 18         # 18h    (was 36)
DEAD_FISH_DECAY_TIMESTEPS = 12      # 18h    (was 24)
NH3_EXPIRE_TIMESTEPS = 36           # 1.5 days (was 60)
DISEASE_AREA_DECAY = 24             # 1 day  (was 36)
PARASITE_AREA_DECAY = 24            # 1 day  (was 36)
POLLUTANT_TO_HAZARD_TIMESTEPS = 18  # 1 day  (was 48)
DISEASE_AREA_RADIUS_DECAY = 0.990

# ╔══════════════════════════════════════════════════════════════╗
# ║                 SINKING & FLOATING                          ║
# ╚══════════════════════════════════════════════════════════════╝

SINK_SPEED = 0.4
SINK_SPEED_HEAVY = 0.8

# ╔══════════════════════════════════════════════════════════════╗
# ║                 FECAL                                       ║
# ╚══════════════════════════════════════════════════════════════╝

FECAL_DROP_INTERVAL = 3
FECAL_BASE_CHANCE = 0.07
FECAL_VALUE = 3.0
FECAL_SINK_SPEED = SINK_SPEED
MAX_SINKING_FECAL = 100

# ╔══════════════════════════════════════════════════════════════╗
# ║                 DEAD FISH                                   ║
# ╚══════════════════════════════════════════════════════════════╝

DEAD_FISH_NH3_RADIUS = 12.0
DEAD_FISH_FLOAT_CHANCE = 0.45
DEAD_FISH_FLOAT_DURATION_RANGE = (6, 36)   # Halved (was 12, 72)
DEAD_FISH_FLOAT_SPEED = 0.4
DEAD_FISH_POLLUTANT_MULT = 3.0
INFECTED_FISH_DISEASE_RADIUS_MULT = 5.0

# ╔══════════════════════════════════════════════════════════════╗
# ║                 CANNIBALISM                                 ║
# ╚══════════════════════════════════════════════════════════════╝

CANNIBAL_FULLNESS_THRESHOLD = 0.7
CANNIBAL_BASE_CHANCE = 0.25
CANNIBAL_HUNGER_MULT = 0.80
CANNIBAL_FULLNESS_GAIN_MULT = 3.0
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
# ║  Slightly increased for 30-day simulation to see more       ║
# ║  environmental dynamics within the shorter window.          ║
# ╚══════════════════════════════════════════════════════════════╝

NATURAL_OXYGEN_SPAWN_RATE = 0.15    # was 0.12
NATURAL_NH3_SPAWN_RATE = 0.06       # was 0.04

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

PSO_PROBIOTIC_WEIGHT = 1.8

PSO_OXYGEN_WEIGHT = 2.2
PSO_OXYGEN_CRITICAL_MULT = 2.0
PSO_OXYGEN_THRESHOLD = 0.7
PSO_OXYGEN_CRITICAL_THRESHOLD = 0.3
PSO_OXYGEN_INTERCEPT_STEPS = 3

PSO_SOCIAL_WEIGHT = 2.0
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
