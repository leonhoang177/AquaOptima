import random
import math
import json

# ==========================================
# 1. HYPERPARAMETERS & CONFIGURATION
# ==========================================
TANK_WIDTH = 800
TANK_HEIGHT = 600
FOOD_SOURCE = [400, 300] # Target for the swarm to find
NUM_FISH = 30
TIMESTEPS = 150

# EA Parameters
POPULATION_SIZE = 10
GENERATIONS = 15
MUTATION_RATE = 0.1

# Trait Bounds: [w (inertia), c1 (cognitive), c2 (social), sensory_radius]
GENE_BOUNDS = [
    (0.1, 0.9),   # w
    (0.5, 3.0),   # c1
    (0.5, 3.0),   # c2
    (10.0, 100.0) # radius
]

# ==========================================
# 2. THE INNER LOOP (PSO: Fish Swarm)
# ==========================================
class Fish:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)
        self.vy = random.uniform(-2, 2)
        self.pbest_x = x
        self.pbest_y = y
        self.pbest_val = float('inf') # Lower is better (distance to food)

def run_pso(traits, record_frames=False):
    """
    Runs the swarm simulation. 
    If record_frames is True, it returns the frame-by-frame data for JS.
    Otherwise, it returns the fitness score for the EA.
    """
    w, c1, c2, radius = traits
    swarm = [Fish(random.uniform(0, TANK_WIDTH), random.uniform(0, TANK_HEIGHT)) for _ in range(NUM_FISH)]
    
    gbest_x, gbest_y = 0, 0
    gbest_val = float('inf')
    
    frames = []

    for t in range(TIMESTEPS):
        frame_data = []
        for fish in swarm:
            # 1. Calculate distance to food (if within sensory radius)
            dist_to_food = math.hypot(FOOD_SOURCE[0] - fish.x, FOOD_SOURCE[1] - fish.y)
            current_eval = dist_to_food if dist_to_food <= radius else float('inf')

            # 2. Update Personal Best
            if current_eval < fish.pbest_val:
                fish.pbest_val = current_eval
                fish.pbest_x = fish.x
                fish.pbest_y = fish.y

            # 3. Update Global Best
            if current_eval < gbest_val:
                gbest_val = current_eval
                gbest_x = fish.x
                gbest_y = fish.y

            # 4. PSO Velocity Update Formula
            r1, r2 = random.random(), random.random()
            fish.vx = (w * fish.vx) + (c1 * r1 * (fish.pbest_x - fish.x)) + (c2 * r2 * (gbest_x - fish.x))
            fish.vy = (w * fish.vy) + (c1 * r1 * (fish.pbest_y - fish.y)) + (c2 * r2 * (gbest_y - fish.y))

            # Limit speed to prevent erratic teleporting
            speed = math.hypot(fish.vx, fish.vy)
            if speed > 5.0:
                fish.vx = (fish.vx / speed) * 5.0
                fish.vy = (fish.vy / speed) * 5.0

            # 5. Position Update
            fish.x += fish.vx
            fish.y += fish.vy

            # Keep fish inside the tank (bounce off walls)
            if fish.x <= 0 or fish.x >= TANK_WIDTH: fish.vx *= -1
            if fish.y <= 0 or fish.y >= TANK_HEIGHT: fish.vy *= -1
            
            # Record data if this is the final presentation run
            if record_frames:
                angle = math.atan2(fish.vy, fish.vx)
                frame_data.append({"x": fish.x, "y": fish.y, "angle": angle})
                
        if record_frames:
            frames.append(frame_data)

    # Fitness is how close the swarm's best fish got to the food (lower is better)
    # We return negative gbest_val so the EA can MAXIMIZE the score
    if record_frames:
        return frames
    return -gbest_val 

# ==========================================
# 3. THE OUTER LOOP (EA: Trait Evolution)
# ==========================================
def init_population():
    return [[random.uniform(b[0], b[1]) for b in GENE_BOUNDS] for _ in range(POPULATION_SIZE)]

def tournament_selection(pop, fitnesses):
    idx1, idx2 = random.sample(range(POPULATION_SIZE), 2)
    return pop[idx1] if fitnesses[idx1] > fitnesses[idx2] else pop[idx2]

def crossover(p1, p2):
    return [g1 if random.random() < 0.5 else g2 for g1, g2 in zip(p1, p2)]

def mutate(ind):
    return [
        max(b[0], min(b[1], g + random.gauss(0, (b[1]-b[0])*0.1))) if random.random() < MUTATION_RATE else g 
        for g, b in zip(ind, GENE_BOUNDS)
    ]

def run_ea():
    print("Starting Evolution...")
    population = init_population()
    best_overall_traits = None
    best_overall_fitness = -float('inf')

    for gen in range(GENERATIONS):
        # Evaluate using the PSO simulator
        fitnesses = [run_pso(ind) for ind in population]
        
        gen_best_fit = max(fitnesses)
        gen_best_ind = population[fitnesses.index(gen_best_fit)]
        
        if gen_best_fit > best_overall_fitness:
            best_overall_fitness = gen_best_fit
            best_overall_traits = gen_best_ind
            
        print(f"Gen {gen}: Best Fitness (Distance) = {abs(gen_best_fit):.2f}")

        # Breed next generation
        next_gen = []
        for _ in range(POPULATION_SIZE // 2):
            p1 = tournament_selection(population, fitnesses)
            p2 = tournament_selection(population, fitnesses)
            next_gen.extend([mutate(crossover(p1, p2)), mutate(crossover(p1, p2))])
            
        population = next_gen

    return best_overall_traits

# ==========================================
# 4. EXECUTION & EXPORT
# ==========================================
if __name__ == "__main__":
    # 1. Run the EA to find the best behavioral traits
    optimal_traits = run_ea()
    print("\nEvolution Complete!")
    print(f"Optimal Traits Found: w={optimal_traits[0]:.2f}, c1={optimal_traits[1]:.2f}, c2={optimal_traits[2]:.2f}, radius={optimal_traits[3]:.2f}")
    
    # 2. Run ONE final simulation with these traits and record the frames
    print("Generating presentation data...")
    presentation_frames = run_pso(optimal_traits, record_frames=True)
    
    # 3. Export to JSON for the JavaScript visualizer
    export_data = {
        "metadata": {
            "tank_width": TANK_WIDTH,
            "tank_height": TANK_HEIGHT,
            "food_x": FOOD_SOURCE[0],
            "food_y": FOOD_SOURCE[1],
            "traits": optimal_traits
        },
        "frames": presentation_frames
    }
    
    with open('swarm_data.json', 'w') as f:
        json.dump(export_data, f)
    print("Data exported to swarm_data.json. Open index.html to view!")