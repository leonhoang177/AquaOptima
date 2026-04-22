"""Fish — a single PSO particle representing one fish in the tank."""

import numpy as np
from . import config


class Fish:
    def __init__(self, x: float, y: float, species_id: int, school_id: int,
                 w: float, c1: float, c2: float, sensory_radius: float):
        self.x = float(x)
        self.y = float(y)
        self.vx = np.random.uniform(-2.0, 2.0)
        self.vy = np.random.uniform(-2.0, 2.0)

        self.species_id = int(species_id)
        self.school_id = int(school_id)

        # PSO coefficients — inherited from the parent school
        self.w = float(w)
        self.c1 = float(c1)
        self.c2 = float(c2)
        self.sensory_radius = float(sensory_radius)

        # Personal best
        self.pbest_x = self.x
        self.pbest_y = self.y
        self.pbest_fitness = float('-inf')
        self.fitness = float('-inf')

        # Starvation tracking
        self.steps_since_food = 0
        self.food_collected = 0.0

    # ------------------------------------------------------------------
    def update(self, gbest_x: float, gbest_y: float,
               tank_width: int, tank_height: int,
               food_sources: list, env_stress: float):
        """Standard PSO velocity update, then position clamp with elastic bounce."""
        r1, r2 = np.random.random(), np.random.random()

        self.vx = (self.w * self.vx
                   + self.c1 * r1 * (self.pbest_x - self.x)
                   + self.c2 * r2 * (gbest_x - self.x))
        self.vy = (self.w * self.vy
                   + self.c1 * r1 * (self.pbest_y - self.y)
                   + self.c2 * r2 * (gbest_y - self.y))

        # Environmental stress reduces effective max speed
        speed_cap = config.MAX_SPEED * max(0.2, env_stress)
        speed = np.hypot(self.vx, self.vy)
        if speed > speed_cap:
            self.vx *= speed_cap / speed
            self.vy *= speed_cap / speed

        self.x += self.vx
        self.y += self.vy

        # Elastic wall bounce
        if self.x < 0.0:
            self.x = -self.x
            self.vx = abs(self.vx)
        elif self.x > tank_width:
            self.x = 2.0 * tank_width - self.x
            self.vx = -abs(self.vx)
        if self.y < 0.0:
            self.y = -self.y
            self.vy = abs(self.vy)
        elif self.y > tank_height:
            self.y = 2.0 * tank_height - self.y
            self.vy = -abs(self.vy)

        # Hard clamp in case of numerical overshoot
        self.x = max(0.0, min(float(tank_width), self.x))
        self.y = max(0.0, min(float(tank_height), self.y))

        # Evaluate and update personal best
        self.fitness = self._compute_fitness(food_sources)
        if self.fitness > self.pbest_fitness:
            self.pbest_fitness = self.fitness
            self.pbest_x = self.x
            self.pbest_y = self.y

        # Starvation counter: fitness > -30 means fish is within ~30 px of food
        if self.fitness > -30.0:
            self.food_collected += (30.0 + self.fitness) / 30.0
            self.steps_since_food = 0
        else:
            self.steps_since_food += 1

    def _compute_fitness(self, food_sources: list) -> float:
        """Negative distance to nearest visible food, weighted by food amount."""
        if not food_sources:
            return -1000.0

        best = float('-inf')
        nearest_dist = float('inf')

        for fx, fy, amount in food_sources:
            dist = np.hypot(self.x - fx, self.y - fy)
            nearest_dist = min(nearest_dist, dist)
            if dist <= self.sensory_radius and amount > 0:
                # Closer and more abundant = higher fitness
                f = -(dist / (amount + 1e-8))
                best = max(best, f)

        # If nothing in sensory range, fall back to raw negative distance
        return best if best > float('-inf') else -nearest_dist

    # ------------------------------------------------------------------
    @property
    def is_starving(self) -> bool:
        return self.steps_since_food > config.STARVATION_STEPS

    @property
    def angle(self) -> float:
        return float(np.arctan2(self.vy, self.vx))

    def sync_params(self, w: float, c1: float, c2: float, sensory_radius: float):
        """Update PSO coefficients when assimilating into a new school."""
        self.w = float(w)
        self.c1 = float(c1)
        self.c2 = float(c2)
        self.sensory_radius = float(sensory_radius)
