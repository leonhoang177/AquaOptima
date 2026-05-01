#!/usr/bin/env python3
"""
entities.py -- Simulation entity dataclasses (3D).
"""

import random
from dataclasses import dataclass
from typing import Tuple

from constants import (
    EA_MUTATION_RATE, FOOD_INTERVAL_RANGE, FOOD_QUANTITY_RANGE,
    FOOD_PRICE, PROBIOTIC_PRICE, OXYGEN_PRICE,
    VELOCITY_HP_THRESHOLD, VELOCITY_FULLNESS_THRESHOLD,
    PARASITE_VELOCITY_MULT, FLOOR_HAZARD_HEIGHT,
    PROBIOTIC_QUANTITY_RANGE, PROBIOTIC_INTERVAL_STEPS,
    MAX_FISH_COUNT,
)


@dataclass
class PondGenotype:
    fish_count: int = 30
    food_interval: int = 6
    food_quantity: int = 3
    food_location: int = 0
    probiotic_interval: int = 24
    probiotic_quantity: int = 2
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
            'fish_count',
            'food_interval', 'food_quantity', 'food_location',
            'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
            'oxygen_interval', 'oxygen_duration', 'oxygen_location']}

    @staticmethod
    def random() -> 'PondGenotype':
        return PondGenotype(
            fish_count=random.randint(10, MAX_FISH_COUNT),
            food_interval=random.randint(*FOOD_INTERVAL_RANGE),
            food_quantity=random.randint(*FOOD_QUANTITY_RANGE),
            food_location=random.randint(0, 9),
            probiotic_interval=random.choice(PROBIOTIC_INTERVAL_STEPS),
            probiotic_quantity=random.randint(*PROBIOTIC_QUANTITY_RANGE),
            probiotic_location=random.randint(0, 9),
            oxygen_interval=random.randint(1, 24),
            oxygen_duration=random.randint(1, 4),
            oxygen_location=random.randint(0, 9))

    def crossover(self, other: 'PondGenotype') -> 'PondGenotype':
        child = PondGenotype()
        for attr in self.to_dict():
            setattr(child, attr, getattr(self if random.random() < 0.5 else other, attr))
        return child

    def mutate(self):
        r = EA_MUTATION_RATE
        if random.random() < r: self.fish_count = random.randint(10, MAX_FISH_COUNT)
        if random.random() < r: self.food_interval = random.randint(*FOOD_INTERVAL_RANGE)
        if random.random() < r: self.food_quantity = random.randint(*FOOD_QUANTITY_RANGE)
        if random.random() < r: self.food_location = random.randint(0, 9)
        if random.random() < r: self.probiotic_interval = random.choice(PROBIOTIC_INTERVAL_STEPS)
        if random.random() < r: self.probiotic_quantity = random.randint(*PROBIOTIC_QUANTITY_RANGE)
        if random.random() < r: self.probiotic_location = random.randint(0, 9)
        if random.random() < r: self.oxygen_interval = random.randint(1, 24)
        if random.random() < r: self.oxygen_duration = random.randint(1, 4)
        if random.random() < r: self.oxygen_location = random.randint(0, 9)


@dataclass
class Obstacle:
    x: float; y: float; z: float; w: float; h: float; d: float

    def contains(self, px, py, pz) -> bool:
        return (self.x <= px <= self.x + self.w and
                self.y <= py <= self.y + self.h and
                self.z <= pz <= self.z + self.d)

    def nearest_surface(self, px, py, pz) -> Tuple[float, float, float]:
        cx = max(self.x, min(px, self.x + self.w))
        cy = max(self.y, min(py, self.y + self.h))
        cz = max(self.z, min(pz, self.z + self.d))
        return cx, cy, cz

    def center(self) -> Tuple[float, float, float]:
        return self.x + self.w / 2, self.y + self.h / 2, self.z + self.d / 2

    def top_z(self) -> float:
        return self.z

    def xy_contains(self, px, py) -> bool:
        return self.x <= px <= self.x + self.w and self.y <= py <= self.y + self.h


@dataclass
class DynObj:
    x: float; y: float; z: float; kind: str; value: float = 5.0
    age: int = 0; max_age: int = 30
    vx: float = 0.0; vy: float = 0.0; vz: float = 0.0
    alive: bool = True
    on_floor: bool = False
    float_timer: int = 0


@dataclass
class Hazard:
    x: float; y: float; z: float; radius: float; kind: str
    age: int = 0; max_age: int = 50; alive: bool = True
    vx: float = 0.0; vy: float = 0.0; vz: float = 0.0
    is_floor: bool = False
    follow_dead_fish: bool = False

    def contains(self, px, py, pz) -> bool:
        if self.is_floor:
            if pz < self.z - FLOOR_HAZARD_HEIGHT:
                return False
            return (px - self.x) ** 2 + (py - self.y) ** 2 <= self.radius ** 2
        return ((px - self.x) ** 2 + (py - self.y) ** 2 +
                (pz - self.z) ** 2) <= self.radius ** 2


@dataclass
class Fish:
    fid: int = 0
    x: float = 0.0; y: float = 0.0; z: float = 0.0
    vx: float = 0.0; vy: float = 0.0; vz: float = 0.0
    mouth_size: float = 5.0; body_size: float = 6.0
    hp: float = 100.0; max_hp: float = 100.0
    fullness: float = 60.0; max_fullness: float = 60.0
    immunity: float = 80.0; max_immunity: float = 80.0
    oxygen: float = 90.0; max_oxygen: float = 90.0
    base_velocity: float = 2.0
    is_infected: bool = False; has_parasite: bool = False
    alive: bool = True; fecal_timer: int = 0

    def eff_vel(self) -> float:
        v = self.base_velocity
        if self.hp <= self.max_hp * VELOCITY_HP_THRESHOLD: v *= 0.5
        if self.fullness <= self.max_fullness * VELOCITY_FULLNESS_THRESHOLD: v *= 0.5
        if self.has_parasite: v *= PARASITE_VELOCITY_MULT
        return v

    def norm_stats(self) -> float:
        hp_n = max(0, self.hp) / self.max_hp
        fu_n = max(0, self.fullness) / self.max_fullness
        im_n = max(0, self.immunity) / self.max_immunity
        vl_n = min(1.0, self.eff_vel() / (self.base_velocity + 1e-9))
        return (hp_n + fu_n + im_n + vl_n) / 4.0

    def snapshot(self) -> dict:
        return {
            'id': self.fid,
            'x': round(self.x, 1), 'y': round(self.y, 1), 'z': round(self.z, 1),
            'hp': round(self.hp, 1), 'max_hp': round(self.max_hp, 1),
            'fullness': round(self.fullness, 1), 'max_fullness': round(self.max_fullness, 1),
            'immunity': round(self.immunity, 1), 'max_immunity': round(self.max_immunity, 1),
            'oxygen': round(self.oxygen, 1), 'max_oxygen': round(self.max_oxygen, 1),
            'alive': self.alive,
            'is_infected': self.is_infected, 'has_parasite': self.has_parasite,
            'body_size': round(self.body_size, 1), 'mouth_size': round(self.mouth_size, 1),
            'base_velocity': round(self.base_velocity, 2),
            'vx': round(self.vx, 2), 'vy': round(self.vy, 2), 'vz': round(self.vz, 2),
        }