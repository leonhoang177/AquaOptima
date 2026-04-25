#!/usr/bin/env python3
"""
helpers.py -- Pure utility functions and fish factory (3D).
"""

import math
import random

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH, DropLocation,
    MOUTH_SIZE_RANGE, BODY_SIZE_RANGE,
    HP_RANGE, ENERGY_RANGE, FULLNESS_RANGE, IMMUNITY_RANGE, OXYGEN_RANGE,
    VELOCITY_RANGE,
)
from entities import Fish


def _dist(x1, y1, z1, x2, y2, z2):
    return math.sqrt((x1 - x2) ** 2 + (y1 - y2) ** 2 + (z1 - z2) ** 2)


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _norm(vx, vy, vz):
    m = math.sqrt(vx * vx + vy * vy + vz * vz)
    return (vx / m, vy / m, vz / m) if m > 1e-8 else (0.0, 0.0, 0.0)


def _drop_pos(loc: int):
    z = random.uniform(3, POND_DEPTH * 0.3)
    if loc == DropLocation.MIDDLE:
        return (POND_WIDTH / 2 + random.uniform(-15, 15),
                POND_HEIGHT / 2 + random.uniform(-10, 10), z)
    elif loc == DropLocation.CORNER:
        cx, cy = random.choice([
            (15, 15), (POND_WIDTH - 15, 15),
            (15, POND_HEIGHT - 15), (POND_WIDTH - 15, POND_HEIGHT - 15)])
        return (cx + random.uniform(-8, 8), cy + random.uniform(-5, 5), z)
    return (random.uniform(10, POND_WIDTH - 10),
            random.uniform(5, POND_HEIGHT - 5), z)


def _make_fish(fid: int) -> Fish:
    f = Fish(fid=fid)
    f.x = random.uniform(15, POND_WIDTH - 15)
    f.y = random.uniform(10, POND_HEIGHT - 10)
    f.z = random.uniform(5, POND_DEPTH - 5)
    f.mouth_size = random.uniform(*MOUTH_SIZE_RANGE)
    f.body_size = random.uniform(*BODY_SIZE_RANGE)
    f.max_hp = random.uniform(*HP_RANGE); f.hp = f.max_hp
    f.max_energy = random.uniform(*ENERGY_RANGE); f.energy = f.max_energy
    f.max_fullness = random.uniform(*FULLNESS_RANGE); f.fullness = f.max_fullness * 0.8
    f.max_immunity = random.uniform(*IMMUNITY_RANGE); f.immunity = f.max_immunity
    f.max_oxygen = random.uniform(*OXYGEN_RANGE); f.oxygen = f.max_oxygen
    f.base_velocity = random.uniform(*VELOCITY_RANGE)
    f.vx = random.uniform(-1, 1)
    f.vy = random.uniform(-1, 1)
    f.vz = random.uniform(-0.5, 0.5)
    return f


FISH_DICT_KEYS = [
    'fid', 'x', 'y', 'z', 'vx', 'vy', 'vz', 'mouth_size', 'body_size',
    'hp', 'max_hp', 'energy', 'max_energy', 'fullness', 'max_fullness',
    'immunity', 'max_immunity', 'oxygen', 'max_oxygen', 'base_velocity',
    'is_infected', 'has_parasite', 'alive', 'fecal_timer']


def _fish_to_dict(f: Fish) -> dict:
    return {s: getattr(f, s) for s in FISH_DICT_KEYS}


def _dict_to_fish(d: dict) -> Fish:
    f = Fish()
    for k, v in d.items():
        if hasattr(f, k):
            setattr(f, k, v)
    return f