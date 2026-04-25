#!/usr/bin/env python3
"""
pond.py -- PondSim: the aquaculture simulation engine (3D).
"""

import random
import math
import copy

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH,
    W1_SURVIVAL, W2_HEALTHINESS, W3_EFFICIENCY,
    NUM_OBSTACLES, OBSTACLE_MAX_DIM_FRAC, OBSTACLE_AREA_RANGE,
    OBSTACLE_ASPECT_RANGE, OBSTACLE_STATIC_CHANCE, OBSTACLE_SPEED_RANGE,
    OBSTACLE_MAX_WIDTH, OBSTACLE_MAX_HEIGHT, OBSTACLE_MAX_DEPTH,
    OBSTACLE_DEPTH_RANGE,
    OXYGEN_BUBBLE_SPEED, NH3_AREA_RADIUS_RANGE, NH3_AREA_SPEED,
    FOOD_PRICE, PROBIOTIC_PRICE, OXYGEN_PRICE,
    FOOD_VALUE, PROBIOTIC_VALUE, OXYGEN_BUBBLE_GAIN,
    FOOD_EXPIRE_TIMESTEPS, PROBIOTIC_EXPIRE_TIMESTEPS,
    FECAL_EXPIRE_TIMESTEPS, DEAD_FISH_DECAY_TIMESTEPS,
    NH3_EXPIRE_TIMESTEPS, DISEASE_AREA_DECAY, PARASITE_AREA_DECAY,
    POLLUTANT_TO_HAZARD_TIMESTEPS, DISEASE_AREA_RADIUS_DECAY,
    POLLUTANT_TO_DISEASE_CHANCE, POLLUTANT_TO_PARASITE_CHANCE,
    POLLUTANT_RADIUS_SCALE, DEAD_FISH_POLLUTANT_MULT,
    FOOD_ENERGY_GAIN, FOOD_FULLNESS_GAIN, PROBIOTIC_IMMUNITY_BOOST,
    BOOSTING_DURATION,
    NATURAL_OXYGEN_SPAWN_RATE, NATURAL_NH3_SPAWN_RATE, OXYGEN_BUBBLES_PER_PUMP,
    OXYGEN_DECAY, OXYGEN_DECAY_NH3_MULT, ENERGY_DECAY, FULLNESS_DECAY,
    ENERGY_COST_MOVE,
    HP_DECAY_NO_ENERGY, HP_DECAY_NO_FULLNESS, HP_DECAY_INFECTED, HP_DECAY_PARASITE,
    IMMUNITY_DECAY_IN_DISEASE, PARASITE_CONTACT_CHANCE,
    PARASITE_FULLNESS_EFFICIENCY, PARASITE_EXTRA_FULLNESS_DRAIN,
    PARASITE_EXTRA_ENERGY_DRAIN, PARASITE_SCRUB_CHANCE,
    FECAL_DROP_INTERVAL, FECAL_BASE_CHANCE, FECAL_VALUE, FECAL_STACK_RADIUS,
    CANNIBAL_TRIGGER_CHANCE, CANNIBAL_FULLNESS_GAIN_MULT, CANNIBAL_COLLISION_RADIUS_MULT,
    FISH_EAT_RANGE, INFECTED_FISH_DISEASE_RADIUS_MULT,
    SENSITIVE_DISTANCE, SOCIAL_DISTANCE, SELFISH_DISTANCE,
    PSO_INERTIA, PSO_FOOD_WEIGHT, PSO_FOOD_URGENT_MULT,
    PSO_PROBIOTIC_WEIGHT, PSO_OXYGEN_WEIGHT, PSO_OXYGEN_CRITICAL_MULT,
    PSO_OXYGEN_THRESHOLD, PSO_OXYGEN_CRITICAL_THRESHOLD, PSO_OXYGEN_INTERCEPT_STEPS,
    PSO_SOCIAL_WEIGHT, PSO_SELFISH_WEIGHT,
    PSO_NH3_WEIGHT, PSO_NH3_HUNGRY_OVERRIDE,
    PSO_DISEASE_WEIGHT, PSO_DISEASE_BOOSTING_WEIGHT,
    PSO_PARASITE_WEIGHT, PSO_RELIEF_WEIGHT, PSO_RUN_WEIGHT,
    PSO_OBSTACLE_WEIGHT, PSO_OBSTACLE_ANTICIPATION_STEPS,
    STATE_OVERRIDE_PARASITE_CHANCE,
)
from entities import Obstacle, DynObj, Hazard, Fish
from helpers import _dist, _clamp, _norm, _drop_pos


# ════════════════════════════════════════════════════════════════
# WALL MARGIN — fish cannot enter this border zone
# ════════════════════════════════════════════════════════════════

_WALL = 2.0


class PondSim:
    __slots__ = ('geno', 'runtime', 'max_budget', 'record', 'fskip',
                 'fish', 'n0', 'ts', 'objs', 'hazards', 'obstacles',
                 'oxy_pump', 'frames', 'accum_cost', 'budget_exceeded',
                 'cannibal_events')

    def __init__(self, geno, fish_templates, runtime, max_budget, record=False, fskip=1):
        self.geno = geno
        self.runtime = runtime
        self.max_budget = max_budget
        self.record = record
        self.fskip = fskip
        self.fish = copy.deepcopy(fish_templates)
        self.n0 = len(self.fish)
        self.ts = 0
        self.objs = []
        self.hazards = []
        self.obstacles = []
        self.oxy_pump = 0
        self.frames = []
        self.accum_cost = 0.0
        self.budget_exceeded = False
        self.cannibal_events = []
        self._make_obs()

    # ────────────────────────────────────────────────────────────
    # Obstacle generation (3D: area/aspect + 10% dim cap + depth)
    # ────────────────────────────────────────────────────────────

    def _make_obs(self):
        for _ in range(NUM_OBSTACLES):
            area = random.uniform(*OBSTACLE_AREA_RANGE)
            aspect = random.uniform(*OBSTACLE_ASPECT_RANGE)
            w = math.sqrt(area * aspect)
            h = area / w if w > 0 else math.sqrt(area)
            w = min(w, OBSTACLE_MAX_WIDTH)
            h = min(h, OBSTACLE_MAX_HEIGHT)
            d = random.uniform(*OBSTACLE_DEPTH_RANGE)
            d = min(d, OBSTACLE_MAX_DEPTH)
            x = random.uniform(5, POND_WIDTH - 5 - w)
            y = random.uniform(3, POND_HEIGHT - 3 - h)
            z = random.uniform(3, POND_DEPTH - 3 - d)
            is_static = random.random() < OBSTACLE_STATIC_CHANCE
            if is_static:
                vx, vy, vz = 0.0, 0.0, 0.0
            else:
                speed = random.uniform(*OBSTACLE_SPEED_RANGE)
                # Random 3D direction
                theta = random.uniform(0, 2 * math.pi)
                phi = random.uniform(-math.pi / 4, math.pi / 4)  # bias toward horizontal
                cos_phi = math.cos(phi)
                vx = speed * cos_phi * math.cos(theta)
                vy = speed * cos_phi * math.sin(theta)
                vz = speed * math.sin(phi)
            self.obstacles.append(Obstacle(x, y, z, w, h, d, is_static, vx, vy, vz))

    # ────────────────────────────────────────────────────────────
    # Clamp to pond (3D)
    # ────────────────────────────────────────────────────────────

    def _cp(self, x, y, z):
        return (_clamp(x, _WALL, POND_WIDTH - _WALL),
                _clamp(y, _WALL, POND_HEIGHT - _WALL),
                _clamp(z, _WALL, POND_DEPTH - _WALL))

    # ────────────────────────────────────────────────────────────
    # Main run loop
    # ────────────────────────────────────────────────────────────

    def run(self):
        for t in range(self.runtime):
            self.ts = t
            self.cannibal_events = []
            self._step()
            if self.record and t % self.fskip == 0:
                self.frames.append(self._frame())
            if self.budget_exceeded:
                break
            if not any(f.alive for f in self.fish):
                break
        alive = [f for f in self.fish if f.alive]
        sr = len(alive) / self.n0 if self.n0 else 0
        hlth = sum(f.norm_stats() for f in alive) / len(alive) if alive else 0
        cost = self.accum_cost
        eff = max(0, (self.max_budget - cost) / self.max_budget) if not self.budget_exceeded else 0
        fit = (W1_SURVIVAL * sr + W2_HEALTHINESS * hlth + W3_EFFICIENCY * eff) if not self.budget_exceeded else 0
        return {'survival_rate': sr, 'avg_healthiness': hlth, 'efficiency': eff,
                'fitness': fit, 'cost': cost, 'alive_count': len(alive),
                'initial_count': self.n0, 'frames': self.frames,
                'genotype': self.geno.to_dict(), 'budget_exceeded': self.budget_exceeded}

    def _step(self):
        t = self.ts
        self._spawn_food(t)
        self._spawn_prob(t)
        self._pump_oxy(t)
        self._nat_spawn()
        self._upd_objs()
        self._upd_haz()
        self._upd_obs()
        self._decay()
        self._eat()
        self._pso()
        self._cannibal()
        self._fecal()
        self._death()

    # ────────────────────────────────────────────────────────────
    # Cost tracking
    # ────────────────────────────────────────────────────────────

    def _add_cost(self, a):
        self.accum_cost += a
        if self.accum_cost > self.max_budget:
            self.budget_exceeded = True

    # ────────────────────────────────────────────────────────────
    # Spawning (3D)
    # ────────────────────────────────────────────────────────────

    def _spawn_food(self, t):
        if t % self.geno.food_interval == 0:
            self._add_cost(self.geno.food_quantity * FOOD_PRICE)
            if self.budget_exceeded:
                return
            for _ in range(self.geno.food_quantity):
                x, y, z = _drop_pos(self.geno.food_location)
                self.objs.append(DynObj(x, y, z, 'food', FOOD_VALUE,
                                        max_age=FOOD_EXPIRE_TIMESTEPS))

    def _spawn_prob(self, t):
        if t % self.geno.probiotic_interval == 0:
            self._add_cost(self.geno.probiotic_quantity * PROBIOTIC_PRICE)
            if self.budget_exceeded:
                return
            for _ in range(self.geno.probiotic_quantity):
                x, y, z = _drop_pos(self.geno.probiotic_location)
                self.objs.append(DynObj(x, y, z, 'probiotic', PROBIOTIC_VALUE,
                                        max_age=PROBIOTIC_EXPIRE_TIMESTEPS))

    def _pump_oxy(self, t):
        if t % self.geno.oxygen_interval == 0:
            self.oxy_pump = self.geno.oxygen_duration
        if self.oxy_pump > 0:
            self._add_cost(OXYGEN_PRICE)
            if self.budget_exceeded:
                return
            for _ in range(OXYGEN_BUBBLES_PER_PUMP):
                x, y, z = _drop_pos(self.geno.oxygen_location)
                self.objs.append(DynObj(x, y, z, 'oxygen', 1.0, max_age=99999,
                    vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                    vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                    vz=random.uniform(-OXYGEN_BUBBLE_SPEED * 0.5, OXYGEN_BUBBLE_SPEED * 0.5)))
            self.oxy_pump -= 1

    def _nat_spawn(self):
        if random.random() < NATURAL_OXYGEN_SPAWN_RATE:
            x = random.uniform(10, POND_WIDTH - 10)
            y = random.uniform(5, POND_HEIGHT - 5)
            z = random.uniform(5, POND_DEPTH - 5)
            self.objs.append(DynObj(x, y, z, 'oxygen', 1.0, max_age=99999,
                vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                vz=random.uniform(-OXYGEN_BUBBLE_SPEED * 0.5, OXYGEN_BUBBLE_SPEED * 0.5)))
        if random.random() < NATURAL_NH3_SPAWN_RATE:
            x = random.uniform(10, POND_WIDTH - 10)
            y = random.uniform(5, POND_HEIGHT - 5)
            z = random.uniform(5, POND_DEPTH - 5)
            self.hazards.append(Hazard(x, y, z, random.uniform(*NH3_AREA_RADIUS_RANGE), 'nh3',
                max_age=NH3_EXPIRE_TIMESTEPS,
                vx=random.uniform(-NH3_AREA_SPEED, NH3_AREA_SPEED),
                vy=random.uniform(-NH3_AREA_SPEED, NH3_AREA_SPEED),
                vz=random.uniform(-NH3_AREA_SPEED * 0.5, NH3_AREA_SPEED * 0.5)))

    # ────────────────────────────────────────────────────────────
    # Update objects, hazards, obstacles (3D)
    # ────────────────────────────────────────────────────────────

    def _upd_objs(self):
        keep = []
        for o in self.objs:
            o.age += 1
            if o.kind == 'oxygen':
                o.x += o.vx; o.y += o.vy; o.z += o.vz
                if o.x < _WALL or o.x > POND_WIDTH - _WALL: o.vx *= -1
                if o.y < _WALL or o.y > POND_HEIGHT - _WALL: o.vy *= -1
                if o.z < _WALL or o.z > POND_DEPTH - _WALL: o.vz *= -1
                o.x, o.y, o.z = self._cp(o.x, o.y, o.z)
                if any(h.contains(o.x, o.y, o.z) and h.kind == 'nh3' and h.alive
                       for h in self.hazards):
                    continue
                keep.append(o)
                continue
            if o.age >= o.max_age and o.alive:
                if o.kind in ('food', 'probiotic', 'fecal', 'dead_fish'):
                    if o.value > 0:
                        pv = o.value * (DEAD_FISH_POLLUTANT_MULT if o.kind == 'dead_fish' else 1.0)
                        if not any(h.contains(o.x, o.y, o.z) and h.kind == 'nh3' and h.alive
                                   for h in self.hazards):
                            keep.append(DynObj(o.x, o.y, o.z, 'pollutant', pv,
                                               max_age=POLLUTANT_TO_HAZARD_TIMESTEPS))
                    continue
                elif o.kind == 'pollutant':
                    r = o.value * POLLUTANT_RADIUS_SCALE
                    if random.random() < POLLUTANT_TO_DISEASE_CHANCE:
                        self.hazards.append(Hazard(o.x, o.y, o.z, r, 'disease',
                                                   max_age=DISEASE_AREA_DECAY))
                    if random.random() < POLLUTANT_TO_PARASITE_CHANCE:
                        self.hazards.append(Hazard(o.x, o.y, o.z, r, 'parasite',
                                                   max_age=PARASITE_AREA_DECAY))
                    continue
            if o.alive:
                keep.append(o)
        self.objs = keep

    def _upd_haz(self):
        keep = []
        for h in self.hazards:
            h.age += 1
            if h.kind == 'nh3':
                h.x += h.vx; h.y += h.vy; h.z += h.vz
                if h.x < 5 or h.x > POND_WIDTH - 5: h.vx *= -1
                if h.y < 3 or h.y > POND_HEIGHT - 3: h.vy *= -1
                if h.z < 3 or h.z > POND_DEPTH - 3: h.vz *= -1
                h.x = _clamp(h.x, 5, POND_WIDTH - 5)
                h.y = _clamp(h.y, 3, POND_HEIGHT - 3)
                h.z = _clamp(h.z, 3, POND_DEPTH - 3)
            if h.age >= h.max_age:
                if h.kind == 'nh3':
                    self.objs.append(DynObj(h.x, h.y, h.z, 'pollutant', h.radius * 0.5,
                                            max_age=POLLUTANT_TO_HAZARD_TIMESTEPS))
                continue
            if h.kind in ('disease', 'parasite'):
                h.radius = max(0.5, h.radius * DISEASE_AREA_RADIUS_DECAY)
            keep.append(h)
        self.hazards = keep

    def _upd_obs(self):
        for o in self.obstacles:
            if not o.is_static:
                o.x += o.vx; o.y += o.vy; o.z += o.vz
                if o.x < _WALL or o.x + o.w > POND_WIDTH - _WALL: o.vx *= -1
                if o.y < _WALL or o.y + o.h > POND_HEIGHT - _WALL: o.vy *= -1
                if o.z < _WALL or o.z + o.d > POND_DEPTH - _WALL: o.vz *= -1
                o.x = _clamp(o.x, _WALL, POND_WIDTH - _WALL - o.w)
                o.y = _clamp(o.y, _WALL, POND_HEIGHT - _WALL - o.h)
                o.z = _clamp(o.z, _WALL, POND_DEPTH - _WALL - o.d)

    # ────────────────────────────────────────────────────────────
    # Stat decay (3D — uses 3D contains)
    # ────────────────────────────────────────────────────────────

    def _decay(self):
        for f in self.fish:
            if not f.alive:
                continue
            f.oxygen -= OXYGEN_DECAY
            for h in self.hazards:
                if h.kind == 'nh3' and h.contains(f.x, f.y, f.z):
                    f.oxygen -= OXYGEN_DECAY * OXYGEN_DECAY_NH3_MULT
            ec = ENERGY_DECAY
            if f.has_parasite: ec *= PARASITE_EXTRA_ENERGY_DRAIN
            f.energy -= ec
            fd = FULLNESS_DECAY
            if f.has_parasite: fd *= PARASITE_EXTRA_FULLNESS_DRAIN
            f.fullness -= fd
            if f.energy <= 0: f.hp -= HP_DECAY_NO_ENERGY
            if f.fullness <= 0: f.hp -= HP_DECAY_NO_FULLNESS
            if f.is_infected: f.hp -= HP_DECAY_INFECTED
            if f.has_parasite and self.ts % 3 == 0: f.hp -= HP_DECAY_PARASITE
            if f.is_boosting:
                f.boost_timer -= 1
                if f.boost_timer <= 0: f.is_boosting = False
            for h in self.hazards:
                if h.kind == 'disease' and h.contains(f.x, f.y, f.z):
                    f.immunity -= IMMUNITY_DECAY_IN_DISEASE
                    if f.immunity <= 0:
                        f.is_infected = True
                        f.immunity = 0
                if h.kind == 'parasite' and h.contains(f.x, f.y, f.z):
                    if random.random() < PARASITE_CONTACT_CHANCE:
                        f.has_parasite = True

    # ────────────────────────────────────────────────────────────
    # Eating (3D)
    # ────────────────────────────────────────────────────────────

    def _eat(self):
        for f in self.fish:
            if not f.alive:
                continue
            for o in self.objs:
                if not o.alive or o.value <= 0:
                    continue
                if _dist(f.x, f.y, f.z, o.x, o.y, o.z) > f.body_size + FISH_EAT_RANGE:
                    continue
                if o.kind == 'food' and f.fullness < f.max_fullness:
                    o.value -= 1
                    g = FOOD_FULLNESS_GAIN * (PARASITE_FULLNESS_EFFICIENCY if f.has_parasite else 1.0)
                    f.fullness = min(f.max_fullness, f.fullness + g)
                    f.energy = min(f.max_energy, f.energy + FOOD_ENERGY_GAIN)
                    if o.value <= 0: o.alive = False
                elif o.kind == 'probiotic' and not f.is_boosting:
                    o.value -= 1
                    f.immunity = min(f.max_immunity, f.immunity + PROBIOTIC_IMMUNITY_BOOST)
                    f.is_boosting = True
                    f.boost_timer = BOOSTING_DURATION
                    if o.value <= 0: o.alive = False
                elif o.kind == 'oxygen':
                    f.oxygen = min(f.max_oxygen, f.oxygen + OXYGEN_BUBBLE_GAIN)
                    o.alive = False

    # ────────────────────────────────────────────────────────────
    # PSO movement (3D with obstacle avoidance + tangential sliding)
    # ────────────────────────────────────────────────────────────

    def _pso(self):
        alive = [f for f in self.fish if f.alive]
        if not alive:
            return
        for f in alive:
            vel = f.eff_vel()
            nvx = PSO_INERTIA * f.vx
            nvy = PSO_INERTIA * f.vy
            nvz = PSO_INERTIA * f.vz

            for w, dx, dy, dz in self._vecs(f, alive):
                nvx += w * dx
                nvy += w * dy
                nvz += w * dz

            m = math.sqrt(nvx ** 2 + nvy ** 2 + nvz ** 2)
            if m > 0.01:
                nvx = nvx / m * vel
                nvy = nvy / m * vel
                nvz = nvz / m * vel

            # Parasite scrubbing override
            if f.has_parasite and random.random() < STATE_OVERRIDE_PARASITE_CHANCE:
                sv = self._scrub(f)
                if sv:
                    nvx, nvy, nvz = sv[0] * vel, sv[1] * vel, sv[2] * vel

            f.vx, f.vy, f.vz = nvx, nvy, nvz
            nx, ny, nz = f.x + f.vx, f.y + f.vy, f.z + f.vz

            # ── Tangential sliding against obstacles (3D) ──
            for obs in self.obstacles:
                if obs.contains(nx, ny, nz):
                    # Find nearest surface point
                    ssx, ssy, ssz = obs.nearest_surface(nx, ny, nz)

                    # Surface normal: direction from surface outward
                    norm_x, norm_y, norm_z = _norm(nx - ssx, ny - ssy, nz - ssz)

                    # If deep inside (norm is zero), push from center
                    if abs(norm_x) < 1e-8 and abs(norm_y) < 1e-8 and abs(norm_z) < 1e-8:
                        ocx, ocy, ocz = obs.center()
                        norm_x, norm_y, norm_z = _norm(f.x - ocx, f.y - ocy, f.z - ocz)
                        if abs(norm_x) < 1e-8 and abs(norm_y) < 1e-8 and abs(norm_z) < 1e-8:
                            norm_x, norm_y, norm_z = _norm(
                                random.uniform(-1, 1),
                                random.uniform(-1, 1),
                                random.uniform(-1, 1))

                    # Place fish just outside the surface
                    epsilon = 0.5
                    nx = ssx + norm_x * epsilon
                    ny = ssy + norm_y * epsilon
                    nz = ssz + norm_z * epsilon

                    # Decompose velocity: remove normal component, keep tangential
                    dot = f.vx * norm_x + f.vy * norm_y + f.vz * norm_z
                    f.vx -= dot * norm_x
                    f.vy -= dot * norm_y
                    f.vz -= dot * norm_z

                    # Parasite scrubbing on contact
                    if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                        f.has_parasite = False

            # ── Tangential sliding against 6 walls (3D) ──
            # Left wall (x min)
            if nx < _WALL:
                nx = _WALL
                f.vx = 0.0
                if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                    f.has_parasite = False
            # Right wall (x max)
            elif nx > POND_WIDTH - _WALL:
                nx = POND_WIDTH - _WALL
                f.vx = 0.0
                if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                    f.has_parasite = False

            # Front wall (y min)
            if ny < _WALL:
                ny = _WALL
                f.vy = 0.0
                if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                    f.has_parasite = False
            # Back wall (y max)
            elif ny > POND_HEIGHT - _WALL:
                ny = POND_HEIGHT - _WALL
                f.vy = 0.0
                if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                    f.has_parasite = False

            # Surface (z min — top of water)
            if nz < _WALL:
                nz = _WALL
                f.vz = 0.0
                if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                    f.has_parasite = False
            # Floor (z max — bottom of pond)
            elif nz > POND_DEPTH - _WALL:
                nz = POND_DEPTH - _WALL
                f.vz = 0.0
                if f.has_parasite and random.random() < PARASITE_SCRUB_CHANCE:
                    f.has_parasite = False

            f.x, f.y, f.z = self._cp(nx, ny, nz)
            mc = ENERGY_COST_MOVE * vel
            if f.has_parasite: mc *= PARASITE_EXTRA_ENERGY_DRAIN
            f.energy -= mc

    # ────────────────────────────────────────────────────────────
    # PSO vectors (3D — returns (weight, dx, dy, dz) tuples)
    # ────────────────────────────────────────────────────────────

    def _vecs(self, f, alive):
        vecs = []
        fr = max(0, f.fullness) / f.max_fullness

        # ── cFood ──
        if fr < 1.0:
            fw = PSO_FOOD_WEIGHT * (1.0 - fr)
            if max(0, f.energy) / f.max_energy < 0.3:
                fw *= PSO_FOOD_URGENT_MULT
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'food' and o.value > 0:
                    d = _dist(f.x, f.y, f.z, o.x, o.y, o.z)
                    if d < SENSITIVE_DISTANCE and d < nd:
                        nd, no = d, o
            if no:
                dx, dy, dz = _norm(no.x - f.x, no.y - f.y, no.z - f.z)
                vecs.append((fw, dx, dy, dz))

        # ── cProbiotic ──
        if not f.is_boosting:
            ir = max(0, f.immunity) / f.max_immunity
            pw = PSO_PROBIOTIC_WEIGHT * (1.0 - ir)
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'probiotic' and o.value > 0:
                    d = _dist(f.x, f.y, f.z, o.x, o.y, o.z)
                    if d < SENSITIVE_DISTANCE and d < nd:
                        nd, no = d, o
            if no:
                dx, dy, dz = _norm(no.x - f.x, no.y - f.y, no.z - f.z)
                vecs.append((pw, dx, dy, dz))

        # ── cOxygen ──
        orr = max(0, f.oxygen) / f.max_oxygen
        if orr < PSO_OXYGEN_THRESHOLD:
            ow = PSO_OXYGEN_WEIGHT * (1.0 - orr)
            if orr < PSO_OXYGEN_CRITICAL_THRESHOLD:
                ow *= PSO_OXYGEN_CRITICAL_MULT
            nd, no = float('inf'), None
            for o in self.objs:
                if o.alive and o.kind == 'oxygen':
                    fx2 = o.x + o.vx * PSO_OXYGEN_INTERCEPT_STEPS
                    fy2 = o.y + o.vy * PSO_OXYGEN_INTERCEPT_STEPS
                    fz2 = o.z + o.vz * PSO_OXYGEN_INTERCEPT_STEPS
                    d = min(_dist(f.x, f.y, f.z, o.x, o.y, o.z),
                            _dist(f.x, f.y, f.z, fx2, fy2, fz2))
                    if d < SENSITIVE_DISTANCE and d < nd:
                        nd, no = d, o
            if no:
                tx = no.x + no.vx * PSO_OXYGEN_INTERCEPT_STEPS
                ty = no.y + no.vy * PSO_OXYGEN_INTERCEPT_STEPS
                tz = no.z + no.vz * PSO_OXYGEN_INTERCEPT_STEPS
                dx, dy, dz = _norm(tx - f.x, ty - f.y, tz - f.z)
                vecs.append((ow, dx, dy, dz))

        # ── cSocial & cSelfish ──
        svx, svy, svz, sc = 0, 0, 0, 0
        rvx, rvy, rvz, rc = 0, 0, 0, 0
        for o in alive:
            if o.fid == f.fid:
                continue
            d = _dist(f.x, f.y, f.z, o.x, o.y, o.z)
            if d < SELFISH_DISTANCE and d > 0.1:
                dx, dy, dz = _norm(f.x - o.x, f.y - o.y, f.z - o.z)
                rvx += dx / d; rvy += dy / d; rvz += dz / d; rc += 1
            elif d < SOCIAL_DISTANCE:
                svx += o.x - f.x; svy += o.y - f.y; svz += o.z - f.z; sc += 1
        if sc > 0:
            dx, dy, dz = _norm(svx / sc, svy / sc, svz / sc)
            vecs.append((PSO_SOCIAL_WEIGHT, dx, dy, dz))
        if rc > 0:
            dx, dy, dz = _norm(rvx, rvy, rvz)
            vecs.append((PSO_SELFISH_WEIGHT, dx, dy, dz))

        # ── cNH3 ──
        for h in self.hazards:
            if h.kind == 'nh3':
                d = _dist(f.x, f.y, f.z, h.x, h.y, h.z)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    w = PSO_NH3_WEIGHT
                    if fr < 0.1 and any(o.alive and o.kind == 'food'
                                        and h.contains(o.x, o.y, o.z) for o in self.objs):
                        w = PSO_NH3_HUNGRY_OVERRIDE
                    dx, dy, dz = _norm(f.x - h.x, f.y - h.y, f.z - h.z)
                    vecs.append((w, dx, dy, dz))

        # ── cDisease ──
        for h in self.hazards:
            if h.kind == 'disease':
                d = _dist(f.x, f.y, f.z, h.x, h.y, h.z)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    w = PSO_DISEASE_BOOSTING_WEIGHT if f.is_boosting else PSO_DISEASE_WEIGHT
                    dx, dy, dz = _norm(f.x - h.x, f.y - h.y, f.z - h.z)
                    vecs.append((w, dx, dy, dz))

        # ── cParasite ──
        for h in self.hazards:
            if h.kind == 'parasite':
                d = _dist(f.x, f.y, f.z, h.x, h.y, h.z)
                if d < h.radius + SENSITIVE_DISTANCE * 0.5:
                    dx, dy, dz = _norm(f.x - h.x, f.y - h.y, f.z - h.z)
                    vecs.append((PSO_PARASITE_WEIGHT, dx, dy, dz))

        # ── cRun (flee from bigger fish) ──
        for o in alive:
            if o.fid == f.fid:
                continue
            if o.mouth_size > f.body_size:
                d = _dist(f.x, f.y, f.z, o.x, o.y, o.z)
                if 0.1 < d < SENSITIVE_DISTANCE:
                    w = PSO_RUN_WEIGHT * (SENSITIVE_DISTANCE / (d + 1))
                    dx, dy, dz = _norm(f.x - o.x, f.y - o.y, f.z - o.z)
                    vecs.append((w, dx, dy, dz))

        # ── cObstacle (avoidance — only for non-parasitized fish) ──
        if not f.has_parasite:
            for obs in self.obstacles:
                ssx, ssy, ssz = obs.nearest_surface_predicted(
                    f.x, f.y, f.z, PSO_OBSTACLE_ANTICIPATION_STEPS)
                d = _dist(f.x, f.y, f.z, ssx, ssy, ssz)
                if 0 < d < SENSITIVE_DISTANCE:
                    w = PSO_OBSTACLE_WEIGHT * (1.0 - d / SENSITIVE_DISTANCE)
                    dx, dy, dz = _norm(f.x - ssx, f.y - ssy, f.z - ssz)
                    vecs.append((w, dx, dy, dz))
                elif d < 0.01:
                    ocx, ocy, ocz = obs.center()
                    dx, dy, dz = _norm(f.x - ocx, f.y - ocy, f.z - ocz)
                    vecs.append((PSO_OBSTACLE_WEIGHT, dx, dy, dz))

        # ── cRelief (parasitized fish seek obstacles to scrub) ──
        if f.has_parasite:
            sv = self._scrub(f)
            if sv:
                vecs.append((PSO_RELIEF_WEIGHT, sv[0], sv[1], sv[2]))

        return vecs

    # ────────────────────────────────────────────────────────────
    # Scrub helper (3D — find nearest obstacle/wall surface)
    # ────────────────────────────────────────────────────────────

    def _scrub(self, f):
        bd, bo = float('inf'), None
        for o in self.obstacles:
            ssx, ssy, ssz = o.nearest_surface(f.x, f.y, f.z)
            d = _dist(f.x, f.y, f.z, ssx, ssy, ssz)
            if d < bd:
                bd, bo = d, o
        if bo:
            ssx, ssy, ssz = bo.nearest_surface(f.x, f.y, f.z)
            return _norm(ssx - f.x, ssy - f.y, ssz - f.z)
        # Also consider walls as scrub targets
        wall_targets = []
        if f.x > _WALL:
            wall_targets.append((_WALL, f.y, f.z, f.x - _WALL))
        if f.x < POND_WIDTH - _WALL:
            wall_targets.append((POND_WIDTH - _WALL, f.y, f.z, POND_WIDTH - _WALL - f.x))
        if f.y > _WALL:
            wall_targets.append((f.x, _WALL, f.z, f.y - _WALL))
        if f.y < POND_HEIGHT - _WALL:
            wall_targets.append((f.x, POND_HEIGHT - _WALL, f.z, POND_HEIGHT - _WALL - f.y))
        if f.z > _WALL:
            wall_targets.append((f.x, f.y, _WALL, f.z - _WALL))
        if f.z < POND_DEPTH - _WALL:
            wall_targets.append((f.x, f.y, POND_DEPTH - _WALL, POND_DEPTH - _WALL - f.z))
        if wall_targets:
            wall_targets.sort(key=lambda t: t[3])
            tx, ty, tz, _ = wall_targets[0]
            return _norm(tx - f.x, ty - f.y, tz - f.z)
        return None

    # ────────────────────────────────────────────────────────────
    # Cannibalism (3D)
    # ────────────────────────────────────────────────────────────

    def _cannibal(self):
        alive = [f for f in self.fish if f.alive]
        for f in alive:
            if not f.alive or f.fullness > 0:
                continue
            if random.random() > CANNIBAL_TRIGGER_CHANCE:
                continue
            for t in alive:
                if t.fid == f.fid or not t.alive:
                    continue
                if f.mouth_size > t.body_size:
                    d = _dist(f.x, f.y, f.z, t.x, t.y, t.z)
                    if d <= t.body_size * CANNIBAL_COLLISION_RADIUS_MULT:
                        t.hp = 0; t.alive = False
                        f.fullness = min(f.max_fullness,
                                         f.fullness + t.body_size * CANNIBAL_FULLNESS_GAIN_MULT)
                        self.cannibal_events.append({
                            'x': t.x, 'y': t.y, 'z': t.z,
                            'predator': f.fid, 'prey': t.fid})
                        break

    # ────────────────────────────────────────────────────────────
    # Fecal (3D)
    # ────────────────────────────────────────────────────────────

    def _fecal(self):
        for f in self.fish:
            if not f.alive:
                continue
            f.fecal_timer += 1
            if f.fecal_timer >= FECAL_DROP_INTERVAL and f.fullness > 0:
                f.fecal_timer = 0
                if random.random() < (f.fullness / f.max_fullness) * FECAL_BASE_CHANCE:
                    stacked = False
                    for o in self.objs:
                        if (o.alive and o.kind == 'fecal' and
                                _dist(f.x, f.y, f.z, o.x, o.y, o.z) < FECAL_STACK_RADIUS):
                            o.value += FECAL_VALUE
                            stacked = True
                            break
                    if not stacked:
                        self.objs.append(DynObj(
                            f.x + random.uniform(-3, 3),
                            f.y + random.uniform(-2, 2),
                            f.z + random.uniform(-1, 1),
                            'fecal', FECAL_VALUE, max_age=FECAL_EXPIRE_TIMESTEPS))

    # ────────────────────────────────────────────────────────────
    # Death (3D)
    # ────────────────────────────────────────────────────────────

    def _death(self):
        for f in self.fish:
            if not f.alive:
                continue
            if f.hp <= 0 or f.oxygen <= 0:
                f.alive = False
                self.objs.append(DynObj(f.x, f.y, f.z, 'dead_fish', f.body_size,
                                        max_age=DEAD_FISH_DECAY_TIMESTEPS))
                if f.is_infected:
                    self.hazards.append(Hazard(f.x, f.y, f.z,
                        f.body_size * INFECTED_FISH_DISEASE_RADIUS_MULT,
                        'disease', max_age=DISEASE_AREA_DECAY))

    # ────────────────────────────────────────────────────────────
    # Frame snapshot (3D)
    # ────────────────────────────────────────────────────────────

    def _frame(self):
        alive = [f for f in self.fish if f.alive]
        return {
            't': self.ts, 'day': self.ts // 24, 'hour': self.ts % 24,
            'fish': [f.snapshot() for f in alive],
            'objects': [{'x': round(o.x, 1), 'y': round(o.y, 1), 'z': round(o.z, 1),
                         'type': o.kind, 'value': round(o.value, 1)}
                        for o in self.objs if o.alive],
            'hazards': [{'x': round(h.x, 1), 'y': round(h.y, 1), 'z': round(h.z, 1),
                         'r': round(h.radius, 1), 'type': h.kind}
                        for h in self.hazards],
            'obstacles': [{'x': round(o.x, 1), 'y': round(o.y, 1), 'z': round(o.z, 1),
                           'w': round(o.w, 1), 'h': round(o.h, 1), 'd': round(o.d, 1)}
                          for o in self.obstacles],
            'alive_count': len(alive), 'total_count': self.n0,
            'cannibal_events': list(self.cannibal_events)}