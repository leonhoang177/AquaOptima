#!/usr/bin/env python3
"""
simulate.py -- Run a single pond simulation.
This is the interface point for any decision-maker (EA, LLM, etc.).
"""

import random

from constants import MAX_BUDGET, FRAME_SKIP, RUNTIME
from entities import PondGenotype
from helpers import _make_fish
from pond import PondSim


def run_single_pond(geno_dict, runtime=None, max_budget=None,
                    record=False, frame_skip=None, seed=None):
    """Run one pond simulation from a genotype dictionary. Returns result dict."""
    if seed is not None:
        random.seed(seed)
    if runtime is None:
        runtime = RUNTIME
    if max_budget is None:
        max_budget = MAX_BUDGET
    if frame_skip is None:
        frame_skip = FRAME_SKIP

    geno = PondGenotype(**geno_dict)
    fishes = [_make_fish(i) for i in range(geno.fish_count)]
    sim = PondSim(geno, fishes, runtime, max_budget, record=record, fskip=frame_skip)
    r = sim.run()
    r['genotype'] = geno_dict
    return r