#!/usr/bin/env python3
"""
run.py -- Entry point for the Largemouth Bass Aquaculture Optimizer.
"""

import sys, json, subprocess
from pathlib import Path

from constants import (
    POND_WIDTH, POND_HEIGHT, POND_DEPTH,
    AQUACULTURE_DAYS, SIMULATION_JSON_PATH, PROJECT_ROOT,
    FISH_COUNT,
)
from ea import EA


def main():
    ea = EA()
    champ = ea.run(record_best=True)

    if champ and champ.get('frames'):
        viz = {
            'pond_width': POND_WIDTH,
            'pond_height': POND_HEIGHT,
            'pond_depth': POND_DEPTH,
            'genotype': champ['genotype'],
            'fish_count': FISH_COUNT,
            'fitness': champ['fitness'],
            'survival_rate': champ['survival_rate'],
            'avg_healthiness': champ.get('avg_healthiness', 0),
            'cost': champ['cost'],
            'saving': champ.get('saving', 0),
            'yield': champ.get('yield', 0),
            'aquaculture_days': AQUACULTURE_DAYS,
            'frames': champ['frames'],
        }
        with open(SIMULATION_JSON_PATH, 'w') as fp:
            json.dump(viz, fp)
        print(f"\n  Saved {SIMULATION_JSON_PATH} ({len(champ['frames'])} frames)")
        print(f"  Open visuals/index.html in browser")
        print(f"  (serve from project root: python -m http.server)")
    else:
        print("\n  No frames to export.")

    plot_path = str(PROJECT_ROOT / 'core' / 'plot.py')
    print(f"\n  Running plot.py...")
    result = subprocess.run([sys.executable, plot_path])
    if result.returncode != 0:
        print(f"  Warning: plot.py exited with code {result.returncode}")


if __name__ == '__main__':
    main()
