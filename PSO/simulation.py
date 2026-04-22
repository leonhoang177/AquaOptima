"""
Simulation orchestrator — one full evaluation of a set of environmental parameters.

run_simulation(env_params) runs NUM_SEASONS seasons where each season is:
  1. PSO Phase  : schools forage; starving fish may assimilate into better schools.
  2. Season EA  : failing schools are eliminated; survivors reproduce.

Returns final population count, diversity, recorded frames, and season summaries.
"""

import numpy as np
from typing import List, Dict, Tuple
from .fish import Fish
from .school import School
from .tank import Tank
from .pso_engine import run_season
from .ea_engine import season_ea
from . import config


def run_simulation(env_params: Dict,
                   record_frames: bool = False,
                   num_seasons: int = None,
                   verbose: bool = False) -> Tuple[int, float, List[dict], List[dict]]:
    """
    Full nested simulation: PSO foraging inside an EA season loop.

    Args:
        env_params     : dict with food_density, temperature, oxygen_level, ph_level
        record_frames  : if True, capture per-timestep snapshots for visualization
        num_seasons    : number of PSO+EA cycles to run
        verbose        : print per-season progress

    Returns:
        (final_population, final_diversity, frames, season_summaries)
        frames and season_summaries are empty when record_frames=False.
    """
    if num_seasons is None:
        num_seasons = config.NUM_SEASONS

    tank = Tank(config.TANK_WIDTH, config.TANK_HEIGHT, env_params)
    schools = _init_schools(tank)

    all_frames: List[dict] = []
    season_summaries: List[dict] = []

    for season in range(num_seasons):
        # ── PSO Phase ──────────────────────────────────────────────────
        frames, assimilations = run_season(schools, tank,
                                           record_frames=record_frames)
        if record_frames:
            for f in frames:
                f['season'] = season
            all_frames.extend(frames)

        # ── Season EA Phase ────────────────────────────────────────────
        schools = season_ea(schools, tank)

        total_fish = sum(s.size for s in schools if s.alive)
        div = compute_diversity(schools)

        summary = {
            'season': season,
            'schools_alive': sum(1 for s in schools if s.alive),
            'total_fish': total_fish,
            'diversity': round(div, 4),
            'assimilations': len(assimilations),
        }
        season_summaries.append(summary)

        if verbose:
            print(f"    Season {season + 1:2d} | fish={total_fish:3d}  "
                  f"schools={summary['schools_alive']}  "
                  f"diversity={div:.3f}  "
                  f"assimilations={len(assimilations)}")

    final_pop = sum(s.size for s in schools if s.alive)
    final_div = compute_diversity(schools)

    return final_pop, final_div, all_frames, season_summaries


def compute_diversity(schools: List[School]) -> float:
    """
    Normalized Shannon diversity index across all species in living schools.
    Returns 0.0 (mono-culture) to 1.0 (perfectly even distribution).
    """
    counts: Dict[int, int] = {}
    for school in schools:
        if not school.alive:
            continue
        for sp_id, cnt in school.species_composition.items():
            counts[sp_id] = counts.get(sp_id, 0) + cnt

    total = sum(counts.values())
    if total == 0:
        return 0.0

    entropy = 0.0
    for cnt in counts.values():
        if cnt > 0:
            p = cnt / total
            entropy -= p * np.log(p)

    n_present = sum(1 for c in counts.values() if c > 0)
    max_entropy = np.log(max(n_present, 2))
    return float(entropy / max_entropy) if max_entropy > 0 else 0.0


# ─── Initialization helpers ───────────────────────────────────────────────────

def _init_schools(tank: Tank,
                  num_schools: int = config.NUM_SCHOOLS,
                  fish_per_school: int = config.FISH_PER_SCHOOL,
                  num_species: int = config.NUM_SPECIES) -> List[School]:
    School.reset_counter()

    schools: List[School] = []
    for _ in range(num_schools):
        w  = float(np.random.uniform(*config.W_BOUNDS))
        c1 = float(np.random.uniform(*config.C1_BOUNDS))
        c2 = float(np.random.uniform(*config.C2_BOUNDS))
        sr = float(np.random.uniform(*config.SENSORY_RADIUS_BOUNDS))

        # Random species composition that sums to fish_per_school
        raw = np.random.dirichlet(np.ones(num_species))
        counts = np.round(raw * fish_per_school).astype(int)
        diff = fish_per_school - int(counts.sum())
        counts[np.argmax(raw)] += diff  # fix rounding remainder

        comp = {i: int(counts[i]) for i in range(num_species)}

        fish_list: List[Fish] = []
        for sp_id, cnt in comp.items():
            for _ in range(max(0, cnt)):
                x = float(np.random.uniform(20.0, tank.width - 20.0))
                y = float(np.random.uniform(20.0, tank.height - 20.0))
                fish_list.append(Fish(x, y, sp_id, -1, w, c1, c2, sr))

        schools.append(School(fish_list, w, c1, c2, sr, comp))

    return schools
