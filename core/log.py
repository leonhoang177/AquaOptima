#!/usr/bin/env python3
"""
log.py -- Print/table formatting helpers for console output.
Option A: fish_count is now displayed as a fixed constant, not from genotype.
"""

from constants import LOC_NAMES, FISH_COUNT


def _print_gen_table(gen, max_gen, n_ponds, gen_results):
    print(f"\n  Gen {gen + 1:>2}/{max_gen} | {n_ponds} ponds")
    print(f"  +-----+----------+-----------+-------------+--------------+------------+")
    print(f"  |  #  | Fitness  | Survival  | Healthiness |     Cost     |   Status   |")
    print(f"  +-----+----------+-----------+-------------+--------------+------------+")
    for i, r in enumerate(gen_results):
        st = r.get('status', '?')
        if st == 'GATEKEEPER':    st_s = 'REJECT'
        elif st == 'OVER-BUDGET': st_s = 'OVER$'
        elif st == 'ALL-DEAD':    st_s = 'DEAD'
        else:                     st_s = 'OK'
        print(f"  | {i:>3} | {r['fitness']:>8.4f} | {r['survival_rate'] * 100:>8.2f}% | "
              f"{r.get('avg_healthiness', 0):>11.4f} | ${r['cost']:>10.2f} | {st_s:>10} |")
    print(f"  +-----+----------+-----------+-------------+--------------+------------+")


def _print_champion_detail(label: str, result: dict):
    g = result.get('genotype', {})
    fit = result.get('fitness', 0)
    sr = result.get('survival_rate', 0)
    hlth = result.get('avg_healthiness', 0)
    sav = result.get('saving', 0)
    cost = result.get('cost', 0)
    yld = result.get('yield', 0)
    ac = result.get('alive_count', 0)
    ic = result.get('initial_count', 0)
    W = 56; LW = 24; RW = W - LW - 3
    print(f"\n  +{'-' * W}+")
    print(f"  | {label:^{W - 2}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")
    print(f"  | {'Metric':<{LW - 2}} | {'Value':>{RW}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")
    print(f"  | {'Fitness':<{LW - 2}} | {fit:>{RW}.4f} |")
    print(f"  | {'Yield':<{LW - 2}} | {yld:>{RW}.4f} |")
    print(f"  | {'Survival Rate':<{LW - 2}} | {sr * 100:>{RW - 1}.2f}% |")
    print(f"  | {'Healthiness':<{LW - 2}} | {hlth:>{RW}.4f} |")
    print(f"  | {'Saving':<{LW - 2}} | {'${:.2f}'.format(sav):>{RW}} |")
    print(f"  | {'Cost':<{LW - 2}} | {'${:.2f}'.format(cost):>{RW}} |")
    print(f"  | {'Alive / Initial':<{LW - 2}} | {'{} / {}'.format(ac, ic):>{RW}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")
    print(f"  | {'Fish Count (fixed)':<{LW - 2}} | {FISH_COUNT:>{RW}} |")
    print(f"  | {'Food Interval':<{LW - 2}} | {'{} h'.format(g.get('food_interval', '?')):>{RW}} |")
    print(f"  | {'Food Quantity':<{LW - 2}} | {'{} pellets'.format(g.get('food_quantity', '?')):>{RW}} |")
    print(f"  | {'Food Location':<{LW - 2}} | {LOC_NAMES.get(g.get('food_location', -1), '?'):>{RW}} |")
    print(f"  | {'Probiotic Interval':<{LW - 2}} | {'{} h'.format(g.get('probiotic_interval', '?')):>{RW}} |")
    print(f"  | {'Probiotic Quantity':<{LW - 2}} | {'{} pellets'.format(g.get('probiotic_quantity', '?')):>{RW}} |")
    print(f"  | {'Probiotic Location':<{LW - 2}} | {LOC_NAMES.get(g.get('probiotic_location', -1), '?'):>{RW}} |")
    print(f"  | {'O2 Interval':<{LW - 2}} | {'{} h'.format(g.get('oxygen_interval', '?')):>{RW}} |")
    print(f"  | {'O2 Duration':<{LW - 2}} | {'{} h'.format(g.get('oxygen_duration', '?')):>{RW}} |")
    print(f"  | {'O2 Location':<{LW - 2}} | {LOC_NAMES.get(g.get('oxygen_location', -1), '?'):>{RW}} |")
    print(f"  +{'-' * LW}+{'-' * (W - LW - 1)}+")


def _print_champions_summary(champions: list) -> int:
    print(f"\n  +{'=' * 80}+")
    print(f"  | {'ALL TIMELINE CHAMPIONS -- SUMMARY':^78} |")
    print(f"  +{'-' * 12}+{'-' * 10}+{'-' * 8}+{'-' * 11}+{'-' * 13}+{'-' * 14}+")
    print(f"  | {'Timeline':>10} | {'Fitness':>8} | {'Yield':>6} | {'Survival':>9} | {'Healthiness':>11} | {'Saving':>12} |")
    print(f"  +{'-' * 12}+{'-' * 10}+{'-' * 8}+{'-' * 11}+{'-' * 13}+{'-' * 14}+")
    best_idx = 0; best_fit = -1.0
    for i, c in enumerate(champions):
        tl = c.get('timeline_idx', i) + 1
        fit = c.get('fitness', 0)
        yld = c.get('yield', 0)
        sr = c.get('survival_rate', 0)
        hlth = c.get('avg_healthiness', 0)
        sav = c.get('saving', 0)
        if fit > best_fit:
            best_fit = fit; best_idx = i
        tag = " *" if c.get('is_latest_dead') else ""
        print(f"  | {tl:>10} | {fit:>8.4f} | {yld:>6.4f} | {sr * 100:>8.2f}% | {hlth:>11.4f} | ${sav:>11.2f} |{tag}")
    print(f"  +{'-' * 12}+{'-' * 10}+{'-' * 8}+{'-' * 11}+{'-' * 13}+{'-' * 14}+")
    winner = champions[best_idx]
    print(f"\n  >>> Best overall: Timeline {winner.get('timeline_idx', best_idx) + 1} with Fitness = {winner['fitness']:.4f}")
    return best_idx
