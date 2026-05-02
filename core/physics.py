#!/usr/bin/env python3
"""
physics.py -- Environment physics: object movement, hazard updates,
              pollutant transformation, floor stacking.
"""

import random, math

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH,
    OXYGEN_BUBBLE_SPEED, NH3_BUBBLE_SPEED, NH3_AREA_RADIUS_RANGE,
    NH3_EXPIRE_TIMESTEPS, DISEASE_AREA_DECAY, PARASITE_AREA_DECAY,
    POLLUTANT_TO_HAZARD_TIMESTEPS, DISEASE_AREA_RADIUS_DECAY,
    POLLUTANT_TO_NH3_CHANCE, POLLUTANT_TO_DISEASE_CHANCE,
    POLLUTANT_TO_PARASITE_CHANCE, POLLUTANT_TO_BOTH_CHANCE,
    POLLUTANT_TO_PLANT_CHANCE, POLLUTANT_TO_OBSTACLE_CHANCE,
    POLLUTANT_RADIUS_SCALE, DEAD_FISH_POLLUTANT_MULT,
    POLLUTANT_OBSTACLE_AREA_RANGE,
    OBSTACLE_MAX_WIDTH, OBSTACLE_MAX_HEIGHT, OBSTACLE_MAX_DEPTH,
    SINK_SPEED, SINK_SPEED_HEAVY,
    DEAD_FISH_NH3_RADIUS, DEAD_FISH_FLOAT_SPEED,
    FECAL_SINK_SPEED,
    STACK_RADIUS,
)
from entities import Obstacle, DynObj, Hazard
from helpers import _dist, _clamp

_WALL = 2.0
_FLOOR_Z = POND_DEPTH - _WALL


def upd_objs(sim):
    """Move/age all dynamic objects. Handles sinking, drifting, expiry, pollutant conversion."""
    keep = []
    for o in sim.objs:
        if o.kind == 'oxygen':
            o.age += 1
            o.x += o.vx; o.y += o.vy; o.z += o.vz
            if o.x < _WALL or o.x > POND_WIDTH-_WALL: o.vx *= -1
            if o.y < _WALL or o.y > POND_HEIGHT-_WALL: o.vy *= -1
            if o.z < _WALL or o.z > POND_DEPTH-_WALL: o.vz *= -1
            o.x, o.y, o.z = sim._cp(o.x, o.y, o.z)
            if any(h.contains(o.x, o.y, o.z) and h.kind == 'nh3' and h.alive for h in sim.hazards):
                continue
            keep.append(o); continue

        if o.kind == 'plant':
            keep.append(o); continue

        if o.kind in ('food', 'probiotic'):
            rest_z = sim._resting_z(o.x, o.y)
            if not o.on_floor:
                o.x += o.vx; o.y += o.vy; o.z += o.vz
                if o.x < _WALL or o.x > POND_WIDTH-_WALL: o.vx *= -1
                if o.y < _WALL or o.y > POND_HEIGHT-_WALL: o.vy *= -1
                o.x = _clamp(o.x, _WALL, POND_WIDTH-_WALL)
                o.y = _clamp(o.y, _WALL, POND_HEIGHT-_WALL)
                o.z = max(o.z, _WALL)
                if o.z >= rest_z:
                    o.z = rest_z
                    o.on_floor = True
                    o.vx = 0.0; o.vy = 0.0; o.vz = 0.0
            if o.on_floor: o.age += 1

            if o.age >= o.max_age and o.alive:
                if o.value > 0:
                    keep.append(DynObj(o.x, o.y, o.z, 'pollutant', o.value,
                                       max_age=POLLUTANT_TO_HAZARD_TIMESTEPS, on_floor=True))
                continue
            if o.alive: keep.append(o)
            continue

        if o.kind == 'dead_fish':
            rest_z = sim._resting_z(o.x, o.y)

            if o.float_timer > 0:
                o.z = max(_WALL, o.z - DEAD_FISH_FLOAT_SPEED)
                if o.z <= _WALL:
                    o.z = _WALL
                o.float_timer -= 1
            elif o.z < rest_z:
                o.z = min(o.z + SINK_SPEED_HEAVY, rest_z)

            # Follower NH3 tracks this specific body via matching ID
            for h in sim.hazards:
                if h.follow_dead_fish and h.kind == 'nh3' and h.follow_id == o.obj_id:
                    h.x, h.y, h.z = o.x, o.y, o.z

            o.on_floor = o.z >= rest_z - 0.1
            if o.on_floor: o.age += 1

            if o.age >= o.max_age and o.alive:
                # Kill the linked follower NH3
                for h in sim.hazards:
                    if h.follow_dead_fish and h.kind == 'nh3' and h.follow_id == o.obj_id:
                        h.alive = False
                if o.value > 0:
                    pv = o.value * DEAD_FISH_POLLUTANT_MULT
                    if not any(h.contains(o.x, o.y, o.z) and h.kind == 'nh3' and h.alive for h in sim.hazards):
                        keep.append(DynObj(o.x, o.y, o.z, 'pollutant', pv,
                                           max_age=POLLUTANT_TO_HAZARD_TIMESTEPS, on_floor=True))
                continue
            if o.alive: keep.append(o)
            continue

        if o.kind == 'fecal':
            rest_z = sim._resting_z(o.x, o.y)
            if not o.on_floor:
                o.z = min(o.z + FECAL_SINK_SPEED, rest_z)
                if o.z >= rest_z:
                    o.z = rest_z
                    o.on_floor = True

            if o.on_floor: o.age += 1

            if o.age >= o.max_age and o.alive:
                if o.value > 0:
                    if not any(h.contains(o.x, o.y, o.z) and h.kind == 'nh3' and h.alive for h in sim.hazards):
                        keep.append(DynObj(o.x, o.y, o.z, 'pollutant', o.value,
                                           max_age=POLLUTANT_TO_HAZARD_TIMESTEPS, on_floor=True))
                continue
            if o.alive: keep.append(o)
            continue

        # pollutant and other kinds
        o.on_floor = o.z >= sim._resting_z(o.x, o.y) - 0.1
        if o.on_floor: o.age += 1

        if o.age >= o.max_age and o.alive:
            if o.kind == 'pollutant':
                transform_pollutant(sim, o)
                continue
        if o.alive: keep.append(o)
    sim.objs = keep


def transform_pollutant(sim, o):
    """Convert an expired pollutant into a hazard, plant, obstacle, or nothing."""
    r = o.value * POLLUTANT_RADIUS_SCALE
    roll = random.random()
    cumul = 0.0
    cumul += POLLUTANT_TO_NH3_CHANCE
    if roll < cumul:
        sim.hazards.append(Hazard(o.x, o.y, o.z, r, 'nh3', max_age=NH3_EXPIRE_TIMESTEPS,
            vx=random.uniform(-NH3_BUBBLE_SPEED, NH3_BUBBLE_SPEED),
            vy=random.uniform(-NH3_BUBBLE_SPEED, NH3_BUBBLE_SPEED),
            vz=random.uniform(-NH3_BUBBLE_SPEED*0.5, NH3_BUBBLE_SPEED*0.5)))
        return
    cumul += POLLUTANT_TO_DISEASE_CHANCE
    if roll < cumul:
        sim.hazards.append(Hazard(o.x, o.y, _FLOOR_Z, r, 'disease', max_age=DISEASE_AREA_DECAY, is_floor=True))
        return
    cumul += POLLUTANT_TO_PARASITE_CHANCE
    if roll < cumul:
        sim.hazards.append(Hazard(o.x, o.y, _FLOOR_Z, r, 'parasite', max_age=PARASITE_AREA_DECAY, is_floor=True))
        return
    cumul += POLLUTANT_TO_BOTH_CHANCE
    if roll < cumul:
        sim.hazards.append(Hazard(o.x, o.y, _FLOOR_Z, r, 'disease', max_age=DISEASE_AREA_DECAY, is_floor=True))
        sim.hazards.append(Hazard(o.x, o.y, _FLOOR_Z, r*0.8, 'parasite', max_age=PARASITE_AREA_DECAY, is_floor=True))
        return
    cumul += POLLUTANT_TO_PLANT_CHANCE
    if roll < cumul:
        sim.objs.append(DynObj(o.x, o.y, _FLOOR_Z, 'plant', 0, max_age=999999))
        return
    cumul += POLLUTANT_TO_OBSTACLE_CHANCE
    if roll < cumul:
        area = random.uniform(*POLLUTANT_OBSTACLE_AREA_RANGE)
        aspect = random.uniform(0.5, 2.0)
        w = math.sqrt(area * aspect)
        h = area / w if w > 0 else math.sqrt(area)
        w = min(w, OBSTACLE_MAX_WIDTH); h = min(h, OBSTACLE_MAX_HEIGHT)
        d = random.uniform(2, 5); d = min(d, OBSTACLE_MAX_DEPTH)
        ox = _clamp(o.x - w/2, _WALL, POND_WIDTH - _WALL - w)
        oy = _clamp(o.y - h/2, _WALL, POND_HEIGHT - _WALL - h)
        oz = _FLOOR_Z - d
        sim.obstacles.append(Obstacle(ox, oy, oz, w, h, d))
        return
    # Remaining POLLUTANT_TO_NOTHING_CHANCE: harmless decomposition


def upd_haz(sim):
    """Move/age all hazards. Expired NH3 becomes pollutant."""
    keep = []
    for h in sim.hazards:
        if not h.alive:
            continue
        h.age += 1
        if h.kind == 'nh3' and not h.follow_dead_fish:
            h.x += h.vx; h.y += h.vy; h.z += h.vz
            if h.x < 5 or h.x > POND_WIDTH-5: h.vx *= -1
            if h.y < 3 or h.y > POND_HEIGHT-3: h.vy *= -1
            if h.z < 3 or h.z > POND_DEPTH-3: h.vz *= -1
            h.x = _clamp(h.x, 5, POND_WIDTH-5)
            h.y = _clamp(h.y, 3, POND_HEIGHT-3)
            h.z = _clamp(h.z, 3, POND_DEPTH-3)
        if h.age >= h.max_age:
            if h.kind == 'nh3':
                sim.objs.append(DynObj(h.x, h.y, _FLOOR_Z, 'pollutant', h.radius*0.5,
                                        max_age=POLLUTANT_TO_HAZARD_TIMESTEPS, on_floor=True))
            continue
        if h.kind in ('disease', 'parasite'):
            h.radius = max(0.5, h.radius * DISEASE_AREA_RADIUS_DECAY)
        keep.append(h)
    sim.hazards = keep


def stack_floor_objs(sim):
    """Merge stackable objects (food, probiotic, fecal) on the floor within STACK_RADIUS."""
    floor_objs = [o for o in sim.objs if o.alive and o.on_floor and o.kind in ('food', 'probiotic', 'fecal')]
    if not floor_objs:
        return
    by_kind = {}
    for o in floor_objs:
        by_kind.setdefault(o.kind, []).append(o)

    for kind, group in by_kind.items():
        for i in range(len(group)):
            a = group[i]
            if not a.alive:
                continue
            for j in range(i + 1, len(group)):
                b = group[j]
                if not b.alive:
                    continue
                if _dist(a.x, a.y, a.z, b.x, b.y, b.z) < STACK_RADIUS:
                    a.value += b.value
                    b.alive = False