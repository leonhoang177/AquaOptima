"""School — a PSO swarm representing a fish school with shared behavioral traits."""

import numpy as np
from typing import List, Dict, Optional
from .fish import Fish


class School:
    _counter: int = 0

    @classmethod
    def next_id(cls) -> int:
        cls._counter += 1
        return cls._counter

    @classmethod
    def reset_counter(cls, value: int = 0) -> None:
        cls._counter = value

    # ------------------------------------------------------------------
    def __init__(self, fish_list: List[Fish],
                 w: float, c1: float, c2: float, sensory_radius: float,
                 species_composition: Dict[int, int],
                 school_id: Optional[int] = None):
        self.school_id = school_id if school_id is not None else School.next_id()
        self.fish: List[Fish] = list(fish_list)

        # Evolvable PSO hyperparameters (the school's "genes")
        self.w = float(w)
        self.c1 = float(c1)
        self.c2 = float(c2)
        self.sensory_radius = float(sensory_radius)

        # Species composition evolves alongside PSO params
        self.species_composition: Dict[int, int] = dict(species_composition)

        # Group best (gbest) — best position found by any fish in this school
        self.gbest_x: float = fish_list[0].x if fish_list else 400.0
        self.gbest_y: float = fish_list[0].y if fish_list else 300.0
        self.gbest_fitness: float = float('-inf')

        # Fitness accumulator for the current season
        self.step_fitnesses: List[float] = []
        self.seasonal_fitness: float = 0.0
        self.alive: bool = True

        # Sync params to every fish on construction
        for f in self.fish:
            f.school_id = self.school_id
            f.sync_params(w, c1, c2, sensory_radius)

    # ------------------------------------------------------------------
    def step(self, food_sources: list, tank_width: int, tank_height: int,
             env_stress_fn=None) -> None:
        for fish in self.fish:
            stress = env_stress_fn(fish.species_id) if env_stress_fn else 1.0
            fish.update(self.gbest_x, self.gbest_y,
                        tank_width, tank_height, food_sources, stress)
        self._update_gbest()

        if self.fish:
            mean_f = float(np.mean([f.fitness for f in self.fish]))
            self.step_fitnesses.append(mean_f)
            self.seasonal_fitness += mean_f

    def _update_gbest(self) -> None:
        for f in self.fish:
            if f.pbest_fitness > self.gbest_fitness:
                self.gbest_fitness = f.pbest_fitness
                self.gbest_x = f.pbest_x
                self.gbest_y = f.pbest_y

    # ------------------------------------------------------------------
    def add_fish(self, fish: Fish) -> None:
        fish.school_id = self.school_id
        fish.sync_params(self.w, self.c1, self.c2, self.sensory_radius)
        self.fish.append(fish)
        sp = fish.species_id
        self.species_composition[sp] = self.species_composition.get(sp, 0) + 1

    def remove_fish(self, fish: Fish) -> None:
        if fish in self.fish:
            self.fish.remove(fish)
            sp = fish.species_id
            if self.species_composition.get(sp, 0) > 0:
                self.species_composition[sp] -= 1

    def reset_season(self) -> None:
        self.step_fitnesses = []
        self.seasonal_fitness = 0.0

    # ------------------------------------------------------------------
    @property
    def size(self) -> int:
        return len(self.fish)

    @property
    def is_starving(self) -> bool:
        if not self.fish:
            return True
        n_starving = sum(1 for f in self.fish if f.is_starving)
        return n_starving / len(self.fish) > 0.5

    # ------------------------------------------------------------------
    def gene_vector(self) -> List[float]:
        """Encode evolvable behavioral traits as a flat list for EA operators."""
        return [self.w, self.c1, self.c2, self.sensory_radius]

    @classmethod
    def from_gene_vector(cls, genes: List[float], fish_list: List[Fish],
                         species_composition: Dict[int, int]) -> 'School':
        w, c1, c2, sr = genes
        return cls(fish_list, w, c1, c2, sr, species_composition)

    # ------------------------------------------------------------------
    def get_snapshot(self) -> dict:
        return {
            'school_id': self.school_id,
            'size': self.size,
            'w': round(self.w, 4),
            'c1': round(self.c1, 4),
            'c2': round(self.c2, 4),
            'sensory_radius': round(self.sensory_radius, 2),
            'gbest_x': round(self.gbest_x, 2),
            'gbest_y': round(self.gbest_y, 2),
            'gbest_fitness': round(self.gbest_fitness, 4),
            'seasonal_fitness': round(self.seasonal_fitness, 4),
            'species_composition': dict(self.species_composition),
        }
