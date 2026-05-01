#!/usr/bin/env python3
"""
helpers.py -- Pure utility functions and fish factory (3D).
"""

import math
import random

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH, DropLocation,
    MOUTH_SIZE_RANGE, BODY_SIZE_RANGE,
    HEALTH_RANGE, FULLNESS_RANGE, IMMUNITY_RANGE, OXYGEN_RANGE,
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
    """Return (x, y) for a drop location. Z is handled by caller."""
    W, H = POND_WIDTH, POND_HEIGHT
    mx, my = W * 0.15, H * 0.15
    jx = random.uniform(-mx * 0.3, mx * 0.3)
    jy = random.uniform(-my * 0.3, my * 0.3)

    if loc == DropLocation.CENTER:
        return W / 2 + jx, H / 2 + jy
    elif loc == DropLocation.TOP_LEFT:
        return mx + jx, my + jy
    elif loc == DropLocation.TOP_RIGHT:
        return W - mx + jx, my + jy
    elif loc == DropLocation.BOT_LEFT:
        return mx + jx, H - my + jy
    elif loc == DropLocation.BOT_RIGHT:
        return W - mx + jx, H - my + jy
    elif loc == DropLocation.TOP_CENTER:
        return W / 2 + jx, my + jy
    elif loc == DropLocation.BOT_CENTER:
        return W / 2 + jx, H - my + jy
    elif loc == DropLocation.LEFT_CENTER:
        return mx + jx, H / 2 + jy
    elif loc == DropLocation.RIGHT_CENTER:
        return W - mx + jx, H / 2 + jy
    else:
        return random.uniform(10, W - 10), random.uniform(5, H - 5)


def _make_fish(fid: int) -> Fish:
    f = Fish(fid=fid)
    f.x = random.uniform(15, POND_WIDTH - 15)
    f.y = random.uniform(10, POND_HEIGHT - 10)
    f.z = random.uniform(5, POND_DEPTH - 5)
    f.mouth_size = random.uniform(*MOUTH_SIZE_RANGE)
    f.body_size = random.uniform(*BODY_SIZE_RANGE)
    f.max_health = random.uniform(*HEALTH_RANGE); f.health = f.max_health
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
    'health', 'max_health', 'fullness', 'max_fullness',
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


class SpatialGrid:
    """3D spatial hash grid for fast neighbor lookups."""

    def __init__(self, cell_size=30.0):
        self.cell_size = cell_size
        self.cells = {}

    def clear(self):
        self.cells.clear()

    def _key(self, x, y, z):
        return (int(x // self.cell_size),
                int(y // self.cell_size),
                int(z // self.cell_size))

    def insert(self, obj):
        k = self._key(obj.x, obj.y, obj.z)
        if k not in self.cells:
            self.cells[k] = []
        self.cells[k].append(obj)

    def insert_all(self, objects):
        self.clear()
        for obj in objects:
            self.insert(obj)

    def get_nearby(self, x, y, z, radius):
        cs = self.cell_size
        r_cells = int(radius // cs) + 1
        cx, cy, cz = int(x // cs), int(y // cs), int(z // cs)
        r2 = radius * radius
        for dx in range(-r_cells, r_cells + 1):
            for dy in range(-r_cells, r_cells + 1):
                for dz in range(-r_cells, r_cells + 1):
                    cell = self.cells.get((cx + dx, cy + dy, cz + dz))
                    if cell:
                        for obj in cell:
                            ddx = obj.x - x
                            ddy = obj.y - y
                            ddz = obj.z - z
                            if ddx * ddx + ddy * ddy + ddz * ddz <= r2:
                                yield obj