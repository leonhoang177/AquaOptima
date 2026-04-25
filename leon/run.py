#!/usr/bin/env python3
"""
run.py -- Entry point for the Largemouth Bass Aquaculture Optimizer.

Runs the EA, saves simulation_data.json, then automatically runs plot.py.

Usage:  python run.py
"""

import sys
import json
import subprocess

from constants import (
    POND_WIDTH, POND_HEIGHT, INITIAL_FISH_POPULATION, AQUACULTURE_DAYS,
)
from ea import EA


def main():
    ea = EA()
    champ = ea.run(record_best=True)

    if champ and champ.get('frames'):
        viz = {
            'pond_width': POND_WIDTH,
            'pond_height': POND_HEIGHT,
            'genotype': champ['genotype'],
            'fitness': champ['fitness'],
            'survival_rate': champ['survival_rate'],
            'avg_healthiness': champ.get('avg_healthiness', 0),
            'cost': champ['cost'],
            'efficiency': champ['efficiency'],
            'initial_fish': INITIAL_FISH_POPULATION,
            'aquaculture_days': AQUACULTURE_DAYS,
            'frames': champ['frames'],
        }

        with open('simulation_data.json', 'w') as fp:
            json.dump(viz, fp)
        print(f"\n  Saved simulation_data.json ({len(champ['frames'])} frames)")
        print(f"  Open visualization.html in browser (via: python -m http.server)")
    else:
        print("\n  No frames to export.")

    # Automatically run plot.py
    print(f"\n  Running plot.py...")
    result = subprocess.run([sys.executable, 'plot.py'])
    if result.returncode != 0:
        print(f"  Warning: plot.py exited with code {result.returncode}")


if __name__ == '__main__':
    main()