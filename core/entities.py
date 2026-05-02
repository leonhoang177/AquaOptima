#!/usr/bin/env python3
"""
entities.py -- Simulation entity dataclasses (3D).
PondGenotype is a pure data container -- EA operations live in ea.py.
"""

from dataclasses import dataclass
from typing import Tuple

from constants import (
    FOOD_PRICE, PROBIOTIC_PRICE, OXYGEN_PRICE,
    VELOCITY_HEALTH_THRESHOLD, VELOCITY_FULLNESS_THRESHOLD,
    PARASITE_VELOCITY_MULT, FLOOR_HAZARD_HEIGHT,
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
    obj_id: int = -1


@dataclass
class Hazard:
    x: float; y: float; z: float; radius: float; kind: str
    age: int = 0; max_age: int = 50; alive: bool = True
    vx: float = 0.0; vy: float = 0.0; vz: float = 0.0
    is_floor: bool = False
    follow_dead_fish: bool = False
    follow_id: int = -1

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
    health: float = 100.0; max_health: float = 100.0
    fullness: float = 60.0; max_fullness: float = 60.0
    immunity: float = 80.0; max_immunity: float = 80.0
    oxygen: float = 90.0; max_oxygen: float = 90.0
    base_velocity: float = 2.0
    is_infected: bool = False; has_parasite: bool = False
    alive: bool = True; fecal_timer: int = 0

    def eff_vel(self) -> float:
        v = self.base_velocity
        if self.health <= self.max_health * VELOCITY_HEALTH_THRESHOLD: v *= 0.5
        if self.fullness <= self.max_fullness * VELOCITY_FULLNESS_THRESHOLD: v *= 0.5
        if self.has_parasite: v *= PARASITE_VELOCITY_MULT
        return v

    def norm_stats(self) -> float:
        h_n = max(0, self.health) / self.max_health
        fu_n = max(0, self.fullness) / self.max_fullness
        im_n = max(0, self.immunity) / self.max_immunity
        vl_n = min(1.0, self.eff_vel() / (self.base_velocity + 1e-9))
        return (h_n + fu_n + im_n + vl_n) / 4.0

    def snapshot(self) -> dict:
        return {
            'id': self.fid,
            'x': round(self.x, 1), 'y': round(self.y, 1), 'z': round(self.z, 1),
            'health': round(self.health, 1), 'max_health': round(self.max_health, 1),
            'fullness': round(self.fullness, 1), 'max_fullness': round(self.max_fullness, 1),
            'immunity': round(self.immunity, 1), 'max_immunity': round(self.max_immunity, 1),
            'oxygen': round(self.oxygen, 1), 'max_oxygen': round(self.max_oxygen, 1),
            'alive': self.alive,
            'is_infected': self.is_infected, 'has_parasite': self.has_parasite,
            'body_size': round(self.body_size, 1), 'mouth_size': round(self.mouth_size, 1),
            'base_velocity': round(self.base_velocity, 2),
            'vx': round(self.vx, 2), 'vy': round(self.vy, 2), 'vz': round(self.vz, 2),
        }