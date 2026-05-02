#!/usr/bin/env python3
"""
behavior.py -- Fish behavior: PSO movement, eating, decay, cannibalism,
               fecal production, death.
"""

import random, math

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH, BODY_SIZE_RANGE,
    OXYGEN_DECAY, OXYGEN_DECAY_NH3_MULT, OXYGEN_PASSIVE_REGEN,
    FULLNESS_DECAY, FULLNESS_COST_MOVE,
    HEALTH_DECAY_NO_FULLNESS, HEALTH_DECAY_INFECTED, HEALTH_DECAY_PARASITE,
    HEALTH_DECAY_IN_NH3, HEALTH_REGEN, DISEASE_SELF_CURE_CHANCE,
    IMMUNITY_DECAY_IN_DISEASE, IMMUNITY_DECAY_IN_NH3, IMMUNITY_REGEN,
    PARASITE_CONTACT_CHANCE,
    PARASITE_FULLNESS_EFFICIENCY, PARASITE_EXTRA_FULLNESS_DRAIN,
    FOOD_FULLNESS_GAIN, PROBIOTIC_IMMUNITY_GAIN, OXYGEN_BUBBLE_GAIN,
    FISH_EAT_RANGE, INFECTED_FISH_DISEASE_RADIUS_MULT,
    SENSITIVE_DISTANCE, SOCIAL_DISTANCE, SELFISH_DISTANCE,
    PSO_INERTIA, PSO_FOOD_WEIGHT, PSO_FOOD_URGENT_MULT,
    PSO_FOOD_URGENT_THRESHOLD,
    PSO_PROBIOTIC_WEIGHT,
    PSO_OXYGEN_WEIGHT, PSO_OXYGEN_CRITICAL_MULT,
    PSO_OXYGEN_THRESHOLD, PSO_OXYGEN_CRITICAL_THRESHOLD,
    PSO_SOCIAL_WEIGHT, PSO_SELFISH_WEIGHT,
    PSO_NH3_WEIGHT, PSO_NH3_HUNGRY_OVERRIDE,
    PSO_DISEASE_WEIGHT, PSO_PARASITE_WEIGHT,
    PSO_RUN_WEIGHT, PSO_OBSTACLE_WEIGHT,
    PSO_SWARM_HUNGRY_WEIGHT, PSO_SWARM_HUNGRY_THRESHOLD,
    CANNIBAL_FULLNESS_THRESHOLD, CANNIBAL_BASE_CHANCE, CANNIBAL_HUNGER_MULT,
    CANNIBAL_FULLNESS_GAIN_MULT, CANNIBAL_COLLISION_RADIUS_MULT,
    FECAL_DROP_INTERVAL, FECAL_BASE_CHANCE, FECAL_VALUE, FECAL_SINK_SPEED,
    FECAL_EXPIRE_TIMESTEPS, MAX_SINKING_FECAL,
    DEAD_FISH_DECAY_TIMESTEPS, DEAD_FISH_NH3_RADIUS,
    DEAD_FISH_FLOAT_CHANCE, DEAD_FISH_FLOAT_DURATION_RANGE,
    DISEASE_AREA_DECAY, PARASITE_AREA_DECAY,
    PARASITE_VELOCITY_MULT,
)
from entities import DynObj, Hazard
from helpers import _dist, _clamp, _norm

_WALL = 2.0
_FLOOR_Z = POND_DEPTH - _WALL


def decay(sim):
    """Apply per-tick stat decay, environmental effects, disease/parasite mechanics."""
    for f in sim.fish:
        if not f.alive: continue

        f.oxygen -= OXYGEN_DECAY
        f.fullness -= FULLNESS_DECAY * (PARASITE_EXTRA_FULLNESS_DRAIN if f.has_parasite else 1.0)

        in_nh3 = any(h.kind == 'nh3' and h.contains(f.x, f.y, f.z) for h in sim.hazards)
        if not in_nh3 and f.oxygen < f.max_oxygen:
            f.oxygen = min(f.max_oxygen, f.oxygen + OXYGEN_PASSIVE_REGEN)

        for h in sim.hazards:
            if h.kind == 'nh3' and h.contains(f.x, f.y, f.z):
                f.oxygen -= OXYGEN_DECAY * OXYGEN_DECAY_NH3_MULT
                f.health -= HEALTH_DECAY_IN_NH3
                f.immunity -= IMMUNITY_DECAY_IN_NH3

        if f.fullness <= 0: f.health -= HEALTH_DECAY_NO_FULLNESS
        if f.is_infected: f.health -= HEALTH_DECAY_INFECTED
        if f.has_parasite and sim.ts % 3 == 0: f.health -= HEALTH_DECAY_PARASITE

        fr = f.fullness / f.max_fullness
        or_ = f.oxygen / f.max_oxygen
        ir = f.immunity / f.max_immunity
        if (not f.is_infected and not f.has_parasite and
                fr >= 0.7 and or_ >= 0.7 and ir > 0.7):
            f.health = min(f.max_health, f.health + HEALTH_REGEN)

        if not f.is_infected and f.immunity < f.max_immunity:
            f.immunity = min(f.max_immunity, f.immunity + IMMUNITY_REGEN)

        if f.is_infected:
            if fr >= 0.8 and or_ >= 0.8 and ir >= 0.9:
                if random.random() < DISEASE_SELF_CURE_CHANCE:
                    f.is_infected = False

        for h in sim.hazards:
            if h.kind == 'disease' and h.contains(f.x, f.y, f.z):
                f.immunity -= IMMUNITY_DECAY_IN_DISEASE
                if f.immunity <= 0: f.is_infected = True; f.immunity = 0
            if h.kind == 'parasite' and h.contains(f.x, f.y, f.z):
                if random.random() < PARASITE_CONTACT_CHANCE: f.has_parasite = True

        f.health = max(0, f.health)
        f.oxygen = max(0, f.oxygen)
        f.fullness = max(0, f.fullness)
        f.immunity = max(0, f.immunity)


def eat(sim):
    """Fish consume nearby food, probiotic, and oxygen objects."""
    sim._obj_grid.insert_all([o for o in sim.objs if o.alive and o.kind != 'plant'])
    for f in sim.fish:
        if not f.alive: continue
        for o in sim._obj_grid.get_nearby(f.x, f.y, f.z, f.body_size + FISH_EAT_RANGE):
            if not o.alive or o.value <= 0: continue
            if o.kind == 'food' and f.fullness < f.max_fullness:
                o.value -= 1
                g = FOOD_FULLNESS_GAIN * (PARASITE_FULLNESS_EFFICIENCY if f.has_parasite else 1.0)
                f.fullness = min(f.max_fullness, f.fullness + g)
                if o.value <= 0: o.alive = False
            elif o.kind == 'probiotic' and f.immunity < f.max_immunity:
                o.value -= 1
                f.immunity = min(f.max_immunity, f.immunity + PROBIOTIC_IMMUNITY_GAIN)
                if o.value <= 0: o.alive = False
            elif o.kind == 'oxygen':
                f.oxygen = min(f.max_oxygen, f.oxygen + OXYGEN_BUBBLE_GAIN)
                o.alive = False


def _intercept_pos(f, o):
    """Predict where a moving object will be when the fish can reach it."""
    vel = f.eff_vel()
    if vel < 0.01:
        return o.x, o.y, o.z
    tx, ty, tz = o.x, o.y, o.z
    for _ in range(2):
        d = math.sqrt((f.x - tx)**2 + (f.y - ty)**2 + (f.z - tz)**2)
        eta = d / vel
        tx = o.x + o.vx * eta
        ty = o.y + o.vy * eta
        tz = o.z + o.vz * eta
        tx = _clamp(tx, _WALL, POND_WIDTH - _WALL)
        ty = _clamp(ty, _WALL, POND_HEIGHT - _WALL)
        tz = _clamp(tz, _WALL, POND_DEPTH - _WALL)
    return tx, ty, tz


def _vecs(f, sim, alive, swarm_cx, swarm_cy, swarm_cz):
    """Compute all PSO steering vectors for a single fish."""
    vecs = []; fr = max(0, f.fullness) / f.max_fullness

    if fr < 1.0:
        fw = PSO_FOOD_WEIGHT * math.sqrt(1.0 - fr)
        if fr < PSO_FOOD_URGENT_THRESHOLD: fw *= PSO_FOOD_URGENT_MULT
        nd, no = float('inf'), None
        for o in sim._obj_grid.get_nearby(f.x, f.y, f.z, SENSITIVE_DISTANCE):
            if o.alive and o.kind == 'food' and o.value > 0:
                tx, ty, tz = _intercept_pos(f, o)
                d = _dist(f.x, f.y, f.z, tx, ty, tz)
                if d < nd: nd, no = d, o
        if no:
            tx, ty, tz = _intercept_pos(f, no)
            dx,dy,dz = _norm(tx-f.x,ty-f.y,tz-f.z); vecs.append((fw,dx,dy,dz))

    ir = max(0, f.immunity)/f.max_immunity
    if ir < 1.0:
        pw = PSO_PROBIOTIC_WEIGHT*(1.0-ir)
        nd, no = float('inf'), None
        for o in sim._obj_grid.get_nearby(f.x, f.y, f.z, SENSITIVE_DISTANCE):
            if o.alive and o.kind == 'probiotic' and o.value > 0:
                tx, ty, tz = _intercept_pos(f, o)
                d = _dist(f.x, f.y, f.z, tx, ty, tz)
                if d < nd: nd, no = d, o
        if no:
            tx, ty, tz = _intercept_pos(f, no)
            dx,dy,dz = _norm(tx-f.x,ty-f.y,tz-f.z); vecs.append((pw,dx,dy,dz))

    orr = max(0, f.oxygen)/f.max_oxygen
    if orr < PSO_OXYGEN_THRESHOLD:
        ow = PSO_OXYGEN_WEIGHT*(1.0-orr)
        if orr < PSO_OXYGEN_CRITICAL_THRESHOLD: ow *= PSO_OXYGEN_CRITICAL_MULT
        nd, no = float('inf'), None
        for o in sim._obj_grid.get_nearby(f.x, f.y, f.z, SENSITIVE_DISTANCE):
            if o.alive and o.kind == 'oxygen':
                tx, ty, tz = _intercept_pos(f, o)
                d = _dist(f.x, f.y, f.z, tx, ty, tz)
                if d < nd: nd, no = d, o
        if no:
            tx, ty, tz = _intercept_pos(f, no)
            dx,dy,dz = _norm(tx-f.x,ty-f.y,tz-f.z); vecs.append((ow,dx,dy,dz))

    svx,svy,svz,sc = 0,0,0,0; rvx,rvy,rvz,rc = 0,0,0,0
    for o in sim._fish_grid.get_nearby(f.x, f.y, f.z, SOCIAL_DISTANCE):
        if o.fid == f.fid: continue
        d = _dist(f.x,f.y,f.z,o.x,o.y,o.z)
        if d < SELFISH_DISTANCE and d > 0.1:
            dx,dy,dz = _norm(f.x-o.x,f.y-o.y,f.z-o.z)
            rvx += dx/d; rvy += dy/d; rvz += dz/d; rc += 1
        elif d < SOCIAL_DISTANCE:
            svx += o.x-f.x; svy += o.y-f.y; svz += o.z-f.z; sc += 1
    if sc > 0:
        dx,dy,dz = _norm(svx/sc,svy/sc,svz/sc); vecs.append((PSO_SOCIAL_WEIGHT,dx,dy,dz))
    if rc > 0:
        dx,dy,dz = _norm(rvx,rvy,rvz); vecs.append((PSO_SELFISH_WEIGHT,dx,dy,dz))

    for h in sim.hazards:
        if h.kind == 'nh3':
            d = _dist(f.x,f.y,f.z,h.x,h.y,h.z)
            if d < h.radius+SENSITIVE_DISTANCE*0.5:
                w = PSO_NH3_WEIGHT
                if fr < 0.1 and any(o.alive and o.kind=='food' and h.contains(o.x,o.y,o.z) for o in sim.objs):
                    w = PSO_NH3_HUNGRY_OVERRIDE
                dx,dy,dz = _norm(f.x-h.x,f.y-h.y,f.z-h.z); vecs.append((w,dx,dy,dz))
    for h in sim.hazards:
        if h.kind == 'disease':
            d = _dist(f.x,f.y,f.z,h.x,h.y,h.z)
            if d < h.radius+SENSITIVE_DISTANCE*0.5:
                dx,dy,dz = _norm(f.x-h.x,f.y-h.y,f.z-h.z); vecs.append((PSO_DISEASE_WEIGHT,dx,dy,dz))
    for h in sim.hazards:
        if h.kind == 'parasite':
            d = _dist(f.x,f.y,f.z,h.x,h.y,h.z)
            if d < h.radius+SENSITIVE_DISTANCE*0.5:
                dx,dy,dz = _norm(f.x-h.x,f.y-h.y,f.z-h.z); vecs.append((PSO_PARASITE_WEIGHT,dx,dy,dz))

    for o in sim._fish_grid.get_nearby(f.x, f.y, f.z, SENSITIVE_DISTANCE):
        if o.fid == f.fid: continue
        if o.mouth_size > f.body_size:
            d = _dist(f.x,f.y,f.z,o.x,o.y,o.z)
            if 0.1 < d < SENSITIVE_DISTANCE:
                w = PSO_RUN_WEIGHT*(SENSITIVE_DISTANCE/(d+1))
                dx,dy,dz = _norm(f.x-o.x,f.y-o.y,f.z-o.z); vecs.append((w,dx,dy,dz))

    for obs in sim.obstacles:
        ssx,ssy,ssz = obs.nearest_surface(f.x,f.y,f.z)
        d = _dist(f.x,f.y,f.z,ssx,ssy,ssz)
        if 0 < d < SENSITIVE_DISTANCE:
            w = PSO_OBSTACLE_WEIGHT*(1.0-d/SENSITIVE_DISTANCE)
            dx,dy,dz = _norm(f.x-ssx,f.y-ssy,f.z-ssz); vecs.append((w,dx,dy,dz))
        elif d < 0.01:
            ocx,ocy,ocz = obs.center()
            dx,dy,dz = _norm(f.x-ocx,f.y-ocy,f.z-ocz); vecs.append((PSO_OBSTACLE_WEIGHT,dx,dy,dz))

    if sc == 0 and rc == 0:
        if fr < PSO_SWARM_HUNGRY_THRESHOLD:
            urgency = PSO_SWARM_HUNGRY_WEIGHT * math.sqrt(1.0 - fr)
            dx,dy,dz = _norm(swarm_cx - f.x, swarm_cy - f.y, swarm_cz - f.z)
            vecs.append((urgency, dx, dy, dz))
        else:
            cx, cy, cz = POND_WIDTH/2, POND_HEIGHT/2, POND_DEPTH*0.4
            dx,dy,dz = _norm(cx-f.x, cy-f.y, cz-f.z)
            vecs.append((PSO_SOCIAL_WEIGHT * 0.5, dx, dy, dz))
        wx = random.uniform(-1, 1)
        wy = random.uniform(-1, 1)
        wz = random.uniform(-0.5, 0.5)
        dx,dy,dz = _norm(wx, wy, wz)
        vecs.append((0.3, dx, dy, dz))

    return vecs


def pso(sim):
    """PSO-based fish movement with obstacle/wall collision."""
    alive = [f for f in sim.fish if f.alive]
    if not alive: return
    sim._fish_grid.insert_all(alive)
    sim._obj_grid.insert_all([o for o in sim.objs if o.alive and o.kind != 'plant'])

    n = len(alive)
    swarm_cx = sum(a.x for a in alive) / n
    swarm_cy = sum(a.y for a in alive) / n
    swarm_cz = sum(a.z for a in alive) / n

    for f in alive:
        vel = f.eff_vel()
        nvx, nvy, nvz = PSO_INERTIA*f.vx, PSO_INERTIA*f.vy, PSO_INERTIA*f.vz
        for w, dx, dy, dz in _vecs(f, sim, alive, swarm_cx, swarm_cy, swarm_cz):
            nvx += w*dx; nvy += w*dy; nvz += w*dz
        m = math.sqrt(nvx**2 + nvy**2 + nvz**2)
        if m > 0.01: nvx = nvx/m*vel; nvy = nvy/m*vel; nvz = nvz/m*vel
        f.vx, f.vy, f.vz = nvx, nvy, nvz
        nx, ny, nz = f.x+f.vx, f.y+f.vy, f.z+f.vz

        for obs in sim.obstacles:
            if obs.contains(nx, ny, nz):
                ssx, ssy, ssz = obs.nearest_surface(nx, ny, nz)
                norm_x, norm_y, norm_z = _norm(nx-ssx, ny-ssy, nz-ssz)
                if abs(norm_x)<1e-8 and abs(norm_y)<1e-8 and abs(norm_z)<1e-8:
                    ocx, ocy, ocz = obs.center()
                    norm_x, norm_y, norm_z = _norm(f.x-ocx, f.y-ocy, f.z-ocz)
                    if abs(norm_x)<1e-8 and abs(norm_y)<1e-8 and abs(norm_z)<1e-8:
                        norm_x, norm_y, norm_z = _norm(random.uniform(-1,1), random.uniform(-1,1), random.uniform(-1,1))
                nx = ssx+norm_x*0.5; ny = ssy+norm_y*0.5; nz = ssz+norm_z*0.5
                dot = f.vx*norm_x + f.vy*norm_y + f.vz*norm_z
                f.vx -= dot*norm_x; f.vy -= dot*norm_y; f.vz -= dot*norm_z

        if nx < _WALL:
            nx = _WALL; f.vx = 0
        elif nx > POND_WIDTH-_WALL:
            nx = POND_WIDTH-_WALL; f.vx = 0
        if ny < _WALL:
            ny = _WALL; f.vy = 0
        elif ny > POND_HEIGHT-_WALL:
            ny = POND_HEIGHT-_WALL; f.vy = 0
        if nz < _WALL:
            nz = _WALL; f.vz = 0
        elif nz > POND_DEPTH-_WALL:
            nz = POND_DEPTH-_WALL; f.vz = 0

        f.x, f.y, f.z = sim._cp(nx, ny, nz)
        mc = FULLNESS_COST_MOVE * vel
        if f.has_parasite: mc *= PARASITE_EXTRA_FULLNESS_DRAIN
        f.fullness -= mc


def cannibal(sim):
    """Hungry fish may eat smaller fish."""
    alive = [f for f in sim.fish if f.alive]
    sim._fish_grid.insert_all(alive)
    for f in alive:
        if not f.alive: continue
        fr = f.fullness / f.max_fullness if f.max_fullness > 0 else 1.0
        if fr >= CANNIBAL_FULLNESS_THRESHOLD: continue
        eat_range = f.body_size + FISH_EAT_RANGE
        has_food = False
        for o in sim._obj_grid.get_nearby(f.x, f.y, f.z, eat_range * 2):
            if o.alive and o.kind == 'food' and o.value > 0:
                has_food = True; break
        if has_food: continue
        chance = CANNIBAL_BASE_CHANCE + (1.0 - fr) * CANNIBAL_HUNGER_MULT
        if random.random() > chance: continue
        for t in sim._fish_grid.get_nearby(f.x, f.y, f.z,
                    max(BODY_SIZE_RANGE[1] * CANNIBAL_COLLISION_RADIUS_MULT, 20)):
            if t.fid == f.fid or not t.alive: continue
            if f.mouth_size > t.body_size:
                d = _dist(f.x, f.y, f.z, t.x, t.y, t.z)
                if d <= t.body_size * CANNIBAL_COLLISION_RADIUS_MULT:
                    t.health = 0; t.alive = False
                    f.fullness = min(f.max_fullness, f.fullness + t.body_size * CANNIBAL_FULLNESS_GAIN_MULT)
                    sim.cannibal_events.append({'x':t.x,'y':t.y,'z':t.z,'predator':f.fid,'prey':t.fid})
                    break


def fecal(sim):
    """Fish produce fecal waste, capped by MAX_SINKING_FECAL."""
    sinking_count = sum(1 for o in sim.objs if o.alive and o.kind == 'fecal' and not o.on_floor)

    for f in sim.fish:
        if not f.alive: continue
        f.fecal_timer += 1
        if f.fecal_timer >= FECAL_DROP_INTERVAL and f.fullness > 0:
            f.fecal_timer = 0
            if sinking_count >= MAX_SINKING_FECAL:
                continue
            if random.random() < (f.fullness/f.max_fullness)*FECAL_BASE_CHANCE:
                sim.objs.append(DynObj(
                    f.x + random.uniform(-3, 3),
                    f.y + random.uniform(-2, 2),
                    f.z + random.uniform(-1, 1),
                    'fecal', FECAL_VALUE,
                    max_age=FECAL_EXPIRE_TIMESTEPS,
                    vz=FECAL_SINK_SPEED))
                sinking_count += 1


def death(sim):
    """Detect dead fish, spawn dead body + NH3 + disease/parasite zones."""
    for f in sim.fish:
        if not f.alive: continue
        if f.health <= 0 or f.oxygen <= 0:
            f.alive = False

            will_float = random.random() < DEAD_FISH_FLOAT_CHANCE
            ft = random.randint(*DEAD_FISH_FLOAT_DURATION_RANGE) if will_float else 0

            link_id = sim._new_obj_id()

            sim.objs.append(DynObj(f.x, f.y, f.z, 'dead_fish', f.body_size,
                                    max_age=DEAD_FISH_DECAY_TIMESTEPS,
                                    float_timer=ft,
                                    obj_id=link_id))

            sim.hazards.append(Hazard(f.x, f.y, f.z, DEAD_FISH_NH3_RADIUS, 'nh3',
                max_age=999999, follow_dead_fish=True, follow_id=link_id))

            if f.is_infected:
                sim.hazards.append(Hazard(f.x, f.y, f.z,
                    f.body_size*INFECTED_FISH_DISEASE_RADIUS_MULT, 'disease',
                    max_age=DISEASE_AREA_DECAY, is_floor=True))

            if f.has_parasite:
                sim.hazards.append(Hazard(f.x, f.y, f.z,
                    f.body_size*INFECTED_FISH_DISEASE_RADIUS_MULT*0.8, 'parasite',
                    max_age=PARASITE_AREA_DECAY, is_floor=True))