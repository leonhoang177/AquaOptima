# AquaOptima PSO module — simulation hyperparameters

# Tank
TANK_WIDTH = 800
TANK_HEIGHT = 600
MAX_SPEED = 5.0

# Multi-swarm structure
NUM_SCHOOLS = 5        # Initial number of fish schools (swarms)
FISH_PER_SCHOOL = 8    # Fish per school at start
NUM_SPECIES = 3        # Distinct species (0=cool-water, 1=warm-water, 2=flexible)

# Simulation timing
TIMESTEPS_PER_SEASON = 80   # PSO steps per season
NUM_SEASONS = 8              # Seasons per outer-EA individual evaluation

# PSO hyperparameter bounds (used as school gene ranges)
W_BOUNDS = (0.1, 0.9)
C1_BOUNDS = (0.5, 2.5)
C2_BOUNDS = (0.5, 2.5)
SENSORY_RADIUS_BOUNDS = (20.0, 120.0)

# Assimilation — Dynamic Multi-Swarm PSO
STARVATION_STEPS = 15           # Steps without reaching food → fish is starving
ASSIMILATION_RADIUS = 130.0     # Max distance fish can "see" another school's gbest
ASSIMILATION_BENEFIT = 25.0     # Min fitness improvement needed to trigger switch
ASSIMILATION_PROB = 0.35        # Probability of switching when eligible

# Season-end EA (school competition and reproduction)
MIN_SCHOOLS_ALIVE = 2
SEASON_SURVIVAL_FRACTION = 0.5  # Top fraction that survive each season
SEASON_MUTATION_RATE = 0.20
SEASON_MUTATION_SCALE = 0.08    # Sigma as fraction of gene range
SEASON_CROSSOVER_PROB = 0.70

# Outer EA (environmental parameter evolution)
OUTER_POP_SIZE = 8
OUTER_GENERATIONS = 12
OUTER_TOURNAMENT_SIZE = 3
OUTER_MUTATION_RATE = 0.15
OUTER_MUTATION_SCALE = 0.10
OUTER_CROSSOVER_PROB = 0.70
OUTER_ELITISM = 2

# Environmental parameter bounds
ENV_FOOD_DENSITY = (0.2, 1.0)   # Maps to 1–5 food sources
ENV_TEMPERATURE = (15.0, 35.0)  # °C
ENV_OXYGEN = (4.0, 12.0)        # mg/L
ENV_PH = (6.0, 9.0)

# Optimization targets (overridable from main.py CLI)
TARGET_POPULATION = 30
TARGET_DIVERSITY = 0.6
