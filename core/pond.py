#!/usr/bin/env python3
"""
pond.py -- PondSim: the aquaculture simulation orchestrator (3D).
Delegates physics to physics.py and fish behavior to behavior.py.
"""

import random, math, copy

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH,
    W1_YIELD, W2_SAVING, W3_HEALTHINESS, MAX_FISH_COUNT,
    NUM_OBSTACLES, OBSTACLE_AREA_RANGE, OBSTACLE_ASPECT_RANGE,
    OBSTACLE_MAX_WIDTH, OBSTACLE_MAX_HEIGHT, OBSTACLE_MAX_DEPTH,
    OBSTACLE_DEPTH_RANGE,
    OXYGEN_BUBBLE_SPEED, NH3_BUBBLE_SPEED, NH3_AREA_RADIUS_RANGE,
    FOOD_PRICE, PROBIOTIC_PRICE, OXYGEN_PRICE,
    FOOD_VALUE, PROBIOTIC_VALUE,
    FOOD_EXPIRE_TIMESTEPS, PROBIOTIC_EXPIRE_TIMESTEPS,
    NH3_EXPIRE_TIMESTEPS,
    NATURAL_OXYGEN_SPAWN_RATE, NATURAL_NH3_SPAWN_RATE, OXYGEN_BUBBLES_PER_PUMP,
    SINK_SPEED,
    SENSITIVE_DISTANCE, SOCIAL_DISTANCE,
    FOOD_DRIFT_SPEED, PROBIOTIC_DRIFT_SPEED,
)
from entities import Obstacle, DynObj, Hazard
from helpers import _clamp, _drop_pos, SpatialGrid
from physics import upd_objs, upd_haz, stack_floor_objs
from behavior import decay, eat, pso, cannibal, fecal, death

_WALL = 2.0
_FLOOR_Z = POND_DEPTH - _WALL


class PondSim:
    __slots__ = ('geno', 'runtime', 'max_budget', 'record', 'fskip',
                 'fish', 'n0', 'ts', 'objs', 'hazards', 'obstacles',
                 'oxy_pump', 'frames', 'accum_cost', 'budget_exceeded',
                 'cannibal_events', '_fish_grid', '_obj_grid', '_next_obj_id')

    def __init__(self, geno, fish_templates, runtime, max_budget, record=False, fskip=1):
        self.geno = geno; self.runtime = runtime; self.max_budget = max_budget
        self.record = record; self.fskip = fskip
        self.fish = copy.deepcopy(fish_templates); self.n0 = len(self.fish)
        self.ts = 0; self.objs = []; self.hazards = []; self.obstacles = []
        self.oxy_pump = 0; self.frames = []; self.accum_cost = 0.0
        self.budget_exceeded = False; self.cannibal_events = []
        self._fish_grid = SpatialGrid(cell_size=max(SOCIAL_DISTANCE, SENSITIVE_DISTANCE))
        self._obj_grid = SpatialGrid(cell_size=SENSITIVE_DISTANCE)
        self._make_obs()
        self._next_obj_id = 0
        
    def _new_obj_id(self):
        self._next_obj_id += 1
        return self._next_obj_id

    def _make_obs(self):
        for _ in range(NUM_OBSTACLES):
            area = random.uniform(*OBSTACLE_AREA_RANGE)
            aspect = random.uniform(*OBSTACLE_ASPECT_RANGE)
            w = math.sqrt(area * aspect)
            h = area / w if w > 0 else math.sqrt(area)
            w = min(w, OBSTACLE_MAX_WIDTH); h = min(h, OBSTACLE_MAX_HEIGHT)
            d = random.uniform(*OBSTACLE_DEPTH_RANGE); d = min(d, OBSTACLE_MAX_DEPTH)
            x = random.uniform(5, POND_WIDTH - 5 - w)
            y = random.uniform(3, POND_HEIGHT - 3 - h)
            z = _FLOOR_Z - d
            self.obstacles.append(Obstacle(x, y, z, w, h, d))

    def _cp(self, x, y, z):
        return (_clamp(x, _WALL, POND_WIDTH - _WALL),
                _clamp(y, _WALL, POND_HEIGHT - _WALL),
                _clamp(z, _WALL, POND_DEPTH - _WALL))

    def _resting_z(self, ox, oy):
        best_z = _FLOOR_Z
        for obs in self.obstacles:
            if obs.xy_contains(ox, oy):
                top = obs.top_z()
                if top < best_z:
                    best_z = top
        return best_z

    def run(self):
        for t in range(self.runtime):
            self.ts = t; self.cannibal_events = []
            self._step()
            if self.record and t % self.fskip == 0:
                self.frames.append(self._frame())
            if self.budget_exceeded: break
            if not any(f.alive for f in self.fish): break
        alive = [f for f in self.fish if f.alive]
        sr = len(alive) / self.n0 if self.n0 else 0
        hlth = sum(f.norm_stats() for f in alive) / len(alive) if alive else 0
        cost = self.accum_cost
        saving = max(0, self.max_budget - cost) if not self.budget_exceeded else 0
        saving_ratio = saving / self.max_budget if self.max_budget > 0 else 0
        yld = len(alive) / MAX_FISH_COUNT
        fit = (W1_YIELD * yld + W2_SAVING * saving_ratio + W3_HEALTHINESS * hlth) if not self.budget_exceeded else 0
        return {'survival_rate': sr, 'avg_healthiness': hlth, 'saving': saving,
                'fitness': fit, 'cost': cost, 'alive_count': len(alive),
                'initial_count': self.n0, 'yield': yld, 'frames': self.frames,
                'genotype': self.geno.to_dict(), 'budget_exceeded': self.budget_exceeded}

    def _step(self):
        t = self.ts
        self._spawn_food(t); self._spawn_prob(t); self._pump_oxy(t); self._nat_spawn()
        upd_objs(self); upd_haz(self)
        decay(self); eat(self); pso(self); cannibal(self); fecal(self); death(self)
        stack_floor_objs(self)

    def _add_cost(self, a):
        self.accum_cost += a
        if self.accum_cost > self.max_budget: self.budget_exceeded = True

    def _spawn_food(self, t):
        if t % self.geno.food_interval == 0:
            self._add_cost(self.geno.food_quantity * FOOD_PRICE)
            if self.budget_exceeded: return
            for _ in range(self.geno.food_quantity):
                x, y = _drop_pos(self.geno.food_location)
                self.objs.append(DynObj(x, y, _WALL, 'food', FOOD_VALUE,
                    max_age=FOOD_EXPIRE_TIMESTEPS,
                    vx=random.uniform(-FOOD_DRIFT_SPEED, FOOD_DRIFT_SPEED),
                    vy=random.uniform(-FOOD_DRIFT_SPEED, FOOD_DRIFT_SPEED),
                    vz=SINK_SPEED))

    def _spawn_prob(self, t):
        if t % self.geno.probiotic_interval == 0:
            self._add_cost(self.geno.probiotic_quantity * PROBIOTIC_PRICE)
            if self.budget_exceeded: return
            for _ in range(self.geno.probiotic_quantity):
                x, y = _drop_pos(self.geno.probiotic_location)
                self.objs.append(DynObj(x, y, _WALL, 'probiotic', PROBIOTIC_VALUE,
                    max_age=PROBIOTIC_EXPIRE_TIMESTEPS,
                    vx=random.uniform(-PROBIOTIC_DRIFT_SPEED, PROBIOTIC_DRIFT_SPEED),
                    vy=random.uniform(-PROBIOTIC_DRIFT_SPEED, PROBIOTIC_DRIFT_SPEED),
                    vz=SINK_SPEED))

    def _pump_oxy(self, t):
        if t % self.geno.oxygen_interval == 0:
            self.oxy_pump = self.geno.oxygen_duration
        if self.oxy_pump > 0:
            self._add_cost(OXYGEN_PRICE)
            if self.budget_exceeded: return
            for _ in range(OXYGEN_BUBBLES_PER_PUMP):
                x, y = _drop_pos(self.geno.oxygen_location)
                z = random.uniform(_WALL, POND_DEPTH * 0.5)
                self.objs.append(DynObj(x, y, z, 'oxygen', 1.0, max_age=99999,
                    vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                    vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                    vz=random.uniform(-OXYGEN_BUBBLE_SPEED*0.5, OXYGEN_BUBBLE_SPEED*0.5)))
            self.oxy_pump -= 1

    def _nat_spawn(self):
        if random.random() < NATURAL_OXYGEN_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH-10), random.uniform(5, POND_HEIGHT-5)
            z = random.uniform(5, POND_DEPTH-5)
            self.objs.append(DynObj(x, y, z, 'oxygen', 1.0, max_age=99999,
                vx=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                vy=random.uniform(-OXYGEN_BUBBLE_SPEED, OXYGEN_BUBBLE_SPEED),
                vz=random.uniform(-OXYGEN_BUBBLE_SPEED*0.5, OXYGEN_BUBBLE_SPEED*0.5)))
        if random.random() < NATURAL_NH3_SPAWN_RATE:
            x, y = random.uniform(10, POND_WIDTH-10), random.uniform(5, POND_HEIGHT-5)
            z = random.uniform(5, POND_DEPTH-5)
            self.hazards.append(Hazard(x, y, z, random.uniform(*NH3_AREA_RADIUS_RANGE), 'nh3',
                max_age=NH3_EXPIRE_TIMESTEPS,
                vx=random.uniform(-NH3_BUBBLE_SPEED, NH3_BUBBLE_SPEED),
                vy=random.uniform(-NH3_BUBBLE_SPEED, NH3_BUBBLE_SPEED),
                vz=random.uniform(-NH3_BUBBLE_SPEED*0.5, NH3_BUBBLE_SPEED*0.5)))

    def _frame(self):
        alive = [f for f in self.fish if f.alive]
        return {
            't': self.ts, 'day': self.ts//24, 'hour': self.ts%24,
            'fish': [f.snapshot() for f in alive],
            'objects': [{'x':round(o.x,1),'y':round(o.y,1),'z':round(o.z,1),
                         'type':o.kind,'value':round(o.value,1)} for o in self.objs if o.alive],
            'hazards': [{'x':round(h.x,1),'y':round(h.y,1),'z':round(h.z,1),
                         'r':round(h.radius,1),'type':h.kind,'is_floor':h.is_floor}
                        for h in self.hazards],
            'obstacles': [{'x':round(o.x,1),'y':round(o.y,1),'z':round(o.z,1),
                           'w':round(o.w,1),'h':round(o.h,1),'d':round(o.d,1)}
                          for o in self.obstacles],
            'alive_count': len(alive), 'total_count': self.n0,
            'cannibal_events': list(self.cannibal_events)}