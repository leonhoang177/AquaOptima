"""
AquaOptima — PSO module entry point.

Usage (from project root):
    python -m PSO.main
    python -m PSO.main --pop 40 --div 0.7
    python -m PSO.main --pop 25 --div 0.5 --seasons 10 --generations 15

The outer EA evolves tank environmental parameters (food density, temperature,
oxygen level, pH) to produce a fish population that matches the supplied targets.
A final visualization run with the best parameters is recorded to simulation_data.json
in the PSO/ directory.
"""

import argparse
import json
import os
import time
import numpy as np

from .simulation import run_simulation, compute_diversity
from .ea_engine import outer_ea
from . import config


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description='AquaOptima PSO/EA optimizer')
    p.add_argument('--pop',         type=int,   default=config.TARGET_POPULATION,
                   help='Target fish population')
    p.add_argument('--div',         type=float, default=config.TARGET_DIVERSITY,
                   help='Target species diversity (0–1, Shannon normalized)')
    p.add_argument('--seasons',     type=int,   default=config.NUM_SEASONS,
                   help='Seasons per inner simulation')
    p.add_argument('--generations', type=int,   default=config.OUTER_GENERATIONS,
                   help='Outer EA generations')
    p.add_argument('--seed',        type=int,   default=None,
                   help='Random seed for reproducibility')
    return p.parse_args()


def main() -> None:
    args = _parse_args()

    if args.seed is not None:
        np.random.seed(args.seed)

    target_pop = args.pop
    target_div = args.div

    print('=' * 62)
    print('  AquaOptima — Nested EA + PSO Aquaculture Optimizer')
    print('=' * 62)
    print(f'  Target population : {target_pop}')
    print(f'  Target diversity  : {target_div:.2f}  (Shannon normalized)')
    print(f'  Outer EA          : {config.OUTER_POP_SIZE} individuals '
          f'× {args.generations} generations')
    print(f'  Inner simulation  : {args.seasons} seasons '
          f'× {config.TIMESTEPS_PER_SEASON} timesteps')
    print(f'  Schools/season    : {config.NUM_SCHOOLS} schools '
          f'× {config.FISH_PER_SCHOOL} fish/school')
    print(f'  Species           : {config.NUM_SPECIES}')
    print()

    # Override config values that might have been supplied as CLI args
    config.NUM_SEASONS = args.seasons
    config.OUTER_GENERATIONS = args.generations

    # ── Outer EA ──────────────────────────────────────────────────────
    def eval_fn(env_params: dict):
        pop, div, _, _ = run_simulation(env_params, record_frames=False)
        return pop, div

    print('Running outer EA to find optimal environment parameters...')
    t0 = time.time()

    best_params, ea_history = outer_ea(
        target_pop, target_div, eval_fn, verbose=True
    )

    elapsed = time.time() - t0
    print(f'\nOuter EA complete in {elapsed:.1f}s')
    print()
    print('Optimal environment parameters:')
    print(f"  food_density  : {best_params['food_density']:.4f}")
    print(f"  temperature   : {best_params['temperature']:.2f} °C")
    print(f"  oxygen_level  : {best_params['oxygen_level']:.3f} mg/L")
    print(f"  ph_level      : {best_params['ph_level']:.3f}")

    # ── Final recorded simulation ──────────────────────────────────────
    print()
    print('Running final simulation with optimal parameters (recording frames)...')
    t1 = time.time()

    final_pop, final_div, frames, season_summaries = run_simulation(
        best_params, record_frames=True, verbose=True
    )

    print(f'\nFinal simulation complete in {time.time() - t1:.1f}s')
    print(f'  Final population : {final_pop}  (target: {target_pop})')
    print(f'  Final diversity  : {final_div:.4f}  (target: {target_div:.2f})')

    # ── Export JSON ────────────────────────────────────────────────────
    output = {
        'metadata': {
            'tank_width':          config.TANK_WIDTH,
            'tank_height':         config.TANK_HEIGHT,
            'num_seasons':         config.NUM_SEASONS,
            'timesteps_per_season': config.TIMESTEPS_PER_SEASON,
            'num_schools':         config.NUM_SCHOOLS,
            'fish_per_school':     config.FISH_PER_SCHOOL,
            'num_species':         config.NUM_SPECIES,
            'target_population':   target_pop,
            'target_diversity':    target_div,
            'optimal_env_params':  best_params,
            'final_population':    final_pop,
            'final_diversity':     round(final_div, 6),
        },
        'ea_history':       ea_history,
        'season_summaries': season_summaries,
        'frames':           frames,
    }

    out_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            'simulation_data.json')
    with open(out_path, 'w') as f:
        json.dump(output, f, separators=(',', ':'))

    print()
    print(f'Simulation data → {out_path}')
    print('Serve with:  python -m http.server 8000  (in the PSO/ directory)')
    print('Then open:   http://localhost:8000')


if __name__ == '__main__':
    main()
