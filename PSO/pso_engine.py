"""PSO engine — runs one season of multi-swarm foraging with assimilation."""

import numpy as np
from typing import List, Tuple, Dict
from .fish import Fish
from .school import School
from .tank import Tank
from . import config


def run_season(schools: List[School], tank: Tank,
               record_frames: bool = False) -> Tuple[List[dict], List[dict]]:
    """
    Advance all schools through TIMESTEPS_PER_SEASON PSO steps.

    Each step:
      1. Every school executes one PSO tick (all fish update velocity + position).
      2. Assimilation is checked: starving fish may defect to a better nearby school
         (Dynamic Multi-Swarm PSO mechanic).
      3. Food sources regenerate.

    Returns:
        frames           — list of per-timestep snapshots (empty if not recording)
        assimilation_log — list of assimilation event dicts
    """
    frames: List[dict] = []
    assimilation_log: List[dict] = []

    for t in range(config.TIMESTEPS_PER_SEASON):
        food = tank.get_food_tuples()

        for school in schools:
            if school.alive and school.size > 0:
                school.step(food, tank.width, tank.height,
                            env_stress_fn=tank.env_stress)

        events = _handle_assimilation(schools)
        assimilation_log.extend(events)

        tank.update()

        if record_frames:
            frames.append(_build_frame(t, schools, tank))

    return frames, assimilation_log


def _handle_assimilation(schools: List[School]) -> List[dict]:
    """
    Dynamic Multi-Swarm assimilation: a starving fish may switch to a better school
    that is within ASSIMILATION_RADIUS of the fish's current position.

    Condition to switch: target school's gbest_fitness is at least ASSIMILATION_BENEFIT
    units better than the current school's gbest_fitness.
    """
    active = [s for s in schools if s.alive and s.size > 0]
    if len(active) < 2:
        return []

    # Collect moves first to avoid mutating lists during iteration
    to_move: List[Tuple[Fish, School, School]] = []

    for school in active:
        for fish in school.fish:
            if not fish.is_starving:
                continue

            best_other: School | None = None
            best_gain = config.ASSIMILATION_BENEFIT  # must exceed this threshold

            for other in active:
                if other.school_id == school.school_id:
                    continue
                dist = np.hypot(fish.x - other.gbest_x, fish.y - other.gbest_y)
                if dist > config.ASSIMILATION_RADIUS:
                    continue
                gain = other.gbest_fitness - school.gbest_fitness
                if gain > best_gain:
                    best_gain = gain
                    best_other = other

            if best_other is not None and np.random.random() < config.ASSIMILATION_PROB:
                to_move.append((fish, school, best_other))

    events = []
    for fish, from_school, to_school in to_move:
        from_school.remove_fish(fish)
        to_school.add_fish(fish)
        events.append({
            'fish_species': fish.species_id,
            'from_school': from_school.school_id,
            'to_school': to_school.school_id,
        })

    return events


def _build_frame(t: int, schools: List[School], tank: Tank) -> dict:
    fish_data = []
    for school in schools:
        if not school.alive:
            continue
        for fish in school.fish:
            fish_data.append({
                'x': round(fish.x, 2),
                'y': round(fish.y, 2),
                'angle': round(fish.angle, 4),
                'school_id': school.school_id,
                'species_id': fish.species_id,
            })

    return {
        'timestep': t,
        'fish': fish_data,
        'schools': [s.get_snapshot() for s in schools if s.alive],
        'food': [
            {'x': round(fs.x, 2), 'y': round(fs.y, 2),
             'amount': round(fs.amount, 3)}
            for fs in tank.food_sources
        ],
    }
