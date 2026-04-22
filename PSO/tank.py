"""Tank — the aquaculture environment containing food sources and physical parameters."""

import numpy as np
from typing import List, Dict, Tuple


class FoodSource:
    def __init__(self, x: float, y: float, amount: float, regen_rate: float = 0.02):
        self.x = float(x)
        self.y = float(y)
        self.amount = float(amount)
        self.max_amount = float(amount)
        self.regen_rate = float(regen_rate)

    def regenerate(self) -> None:
        self.amount = min(self.max_amount,
                         self.amount + self.regen_rate * self.max_amount)

    def as_tuple(self) -> Tuple[float, float, float]:
        return (self.x, self.y, self.amount)


class Tank:
    # Per-species environmental preferences: (ideal_temp, ideal_o2, ideal_ph)
    _SPECIES_PREFS: Dict[int, Dict[str, float]] = {
        0: {'temp': 22.0, 'o2': 8.5, 'ph': 7.2},   # Cool-water species
        1: {'temp': 28.0, 'o2': 7.0, 'ph': 7.8},   # Warm-water species
        2: {'temp': 25.0, 'o2': 9.0, 'ph': 6.8},   # Flexible species
    }

    def __init__(self, width: int, height: int, env_params: Dict):
        self.width = int(width)
        self.height = int(height)

        # Environmental parameters — these are what the outer EA evolves
        self.food_density = float(env_params.get('food_density', 0.5))
        self.temperature = float(env_params.get('temperature', 25.0))
        self.oxygen_level = float(env_params.get('oxygen_level', 8.0))
        self.ph_level = float(env_params.get('ph_level', 7.0))

        self.food_sources: List[FoodSource] = self._init_food(env_params)

    def _init_food(self, env_params: Dict) -> List[FoodSource]:
        n = max(1, round(self.food_density * 5))
        locs = env_params.get('food_locations', None)
        amounts = env_params.get('food_amounts', [1.0] * n)

        sources = []
        if locs and len(locs) >= n:
            for i in range(n):
                x, y = float(locs[i][0]), float(locs[i][1])
                amt = float(amounts[i]) if i < len(amounts) else 1.0
                sources.append(FoodSource(x, y, amt))
        else:
            for i in range(n):
                x = np.random.uniform(60.0, self.width - 60.0)
                y = np.random.uniform(60.0, self.height - 60.0)
                amt = float(amounts[i]) if i < len(amounts) else 1.0
                sources.append(FoodSource(x, y, amt))

        return sources

    def update(self) -> None:
        """Regenerate food each timestep."""
        for fs in self.food_sources:
            fs.regenerate()

    def get_food_tuples(self) -> List[Tuple[float, float, float]]:
        return [fs.as_tuple() for fs in self.food_sources]

    def env_stress(self, species_id: int) -> float:
        """
        Vitality score in [0, 1] for a given species under current conditions.
        A score of 1.0 means ideal conditions; lower values reduce fish speed.
        """
        prefs = self._SPECIES_PREFS.get(species_id % 3,
                                        self._SPECIES_PREFS[2])

        t_score = max(0.0, 1.0 - abs(self.temperature - prefs['temp']) / 15.0)
        o2_score = max(0.0, 1.0 - abs(self.oxygen_level - prefs['o2']) / 6.0)
        ph_score = max(0.0, 1.0 - abs(self.ph_level - prefs['ph']) / 3.0)

        return (t_score + o2_score + ph_score) / 3.0

    def get_state(self) -> dict:
        return {
            'width': self.width,
            'height': self.height,
            'food_density': round(self.food_density, 4),
            'temperature': round(self.temperature, 2),
            'oxygen_level': round(self.oxygen_level, 3),
            'ph_level': round(self.ph_level, 3),
            'food_sources': [
                {'x': round(fs.x, 2), 'y': round(fs.y, 2),
                 'amount': round(fs.amount, 3)}
                for fs in self.food_sources
            ],
        }
