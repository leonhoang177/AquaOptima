#!/usr/bin/env python3
"""
ea.py -- Evolutionary Algorithm: pond configuration evolution with parallel timelines.
Parallelism is at the pond level within each generation.
Last pond champion = best pond in the LAST generation of each timeline.
"""

import random, copy, csv, time as _time, multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

from constants import (
    MAX_BUDGET, MAX_FISH_COUNT, AQUACULTURE_DAYS,
    POND_GENERATIONS, RUN_TIMELINES, POND_POPULATION,
    FRAME_SKIP, NUM_WORKERS, RUNTIME, RESULTS_CSV_PATH,
    EA_ELITISM_COUNT, EA_TOURNAMENT_K,
    EA_CROSSOVER_RATE, EA_MUTATION_RATE,
    FOOD_INTERVAL_RANGE, FOOD_QUANTITY_RANGE,
    PROBIOTIC_QUANTITY_RANGE, PROBIOTIC_INTERVAL_STEPS,
    OXYGEN_INTERVAL_RANGE, OXYGEN_DURATION_RANGE,
)

from entities import PondGenotype
from simulate import run_single_pond
from log import _print_champion_detail, _print_champions_summary

# ════════════════════════════════════════════════════════════════
# EA GENOTYPE OPERATIONS
# ════════════════════════════════════════════════════════════════

def random_genotype() -> PondGenotype:
    return PondGenotype(
        fish_count=random.randint(10, MAX_FISH_COUNT),
        food_interval=random.randint(*FOOD_INTERVAL_RANGE),
        food_quantity=random.randint(*FOOD_QUANTITY_RANGE),
        food_location=random.randint(0, 9),
        probiotic_interval=random.choice(PROBIOTIC_INTERVAL_STEPS),
        probiotic_quantity=random.randint(*PROBIOTIC_QUANTITY_RANGE),
        probiotic_location=random.randint(0, 9),
        oxygen_interval=random.randint(*OXYGEN_INTERVAL_RANGE),
        oxygen_duration=random.randint(*OXYGEN_DURATION_RANGE),
        oxygen_location=random.randint(0, 9))


def crossover(a: PondGenotype, b: PondGenotype) -> PondGenotype:
    child = PondGenotype()
    for attr in a.to_dict():
        setattr(child, attr, getattr(a if random.random() < 0.5 else b, attr))
    return child


def mutate(geno: PondGenotype):
    r = EA_MUTATION_RATE
    if random.random() < r: geno.fish_count = random.randint(10, MAX_FISH_COUNT)
    if random.random() < r: geno.food_interval = random.randint(*FOOD_INTERVAL_RANGE)
    if random.random() < r: geno.food_quantity = random.randint(*FOOD_QUANTITY_RANGE)
    if random.random() < r: geno.food_location = random.randint(0, 9)
    if random.random() < r: geno.probiotic_interval = random.choice(PROBIOTIC_INTERVAL_STEPS)
    if random.random() < r: geno.probiotic_quantity = random.randint(*PROBIOTIC_QUANTITY_RANGE)
    if random.random() < r: geno.probiotic_location = random.randint(0, 9)
    if random.random() < r: geno.oxygen_interval = random.randint(*OXYGEN_INTERVAL_RANGE)
    if random.random() < r: geno.oxygen_duration = random.randint(*OXYGEN_DURATION_RANGE)
    if random.random() < r: geno.oxygen_location = random.randint(0, 9)


# ════════════════════════════════════════════════════════════════
# CSV / HELPERS
# ════════════════════════════════════════════════════════════════

CSV_HEADER = [
    'timeline', 'generation', 'pond', 'status',
    'fitness', 'survival_rate', 'healthiness', 'cost',
    'saving', 'yield', 'alive_count', 'initial_count',
    'fish_count',
    'food_interval', 'food_quantity', 'food_location',
    'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
    'oxygen_interval', 'oxygen_duration', 'oxygen_location',
]

def _csv_row_data(tl_idx, gen_idx, pond_idx, status, result, geno_dict):
    return [
        tl_idx+1, gen_idx+1, pond_idx, status,
        f"{result.get('fitness',0):.4f}", f"{result.get('survival_rate',0):.4f}",
        f"{result.get('avg_healthiness',0):.4f}", f"{result.get('cost',0):.2f}",
        f"{result.get('saving',0):.2f}", f"{result.get('yield',0):.4f}",
        result.get('alive_count',0), result.get('initial_count',0),
        geno_dict.get('fish_count',''),
        geno_dict.get('food_interval',''), geno_dict.get('food_quantity',''),
        geno_dict.get('food_location',''), geno_dict.get('probiotic_interval',''),
        geno_dict.get('probiotic_quantity',''), geno_dict.get('probiotic_location',''),
        geno_dict.get('oxygen_interval',''), geno_dict.get('oxygen_duration',''),
        geno_dict.get('oxygen_location',''),
    ]

def _tournament_select(gen_results, k):
    candidates = random.sample(gen_results, min(k, len(gen_results)))
    winner = max(candidates, key=lambda r: r['fitness'])
    return winner['genotype_obj']

def _run_pond_worker(args):
    """Multiprocessing target — thin wrapper around simulate.run_single_pond."""
    geno_dict, runtime, max_budget, do_rec, frame_skip, seed = args
    return run_single_pond(geno_dict, runtime, max_budget, do_rec, frame_skip, seed)


# ════════════════════════════════════════════════════════════════
# EA CLASS
# ════════════════════════════════════════════════════════════════

class EA:
    def __init__(self):
        self.runtime = RUNTIME

    def run(self, record_best=True):
        wall_start = _time.time()
        workers = NUM_WORKERS or max(1, multiprocessing.cpu_count())
        print(f"\n{'='*72}")
        print(f"  LARGEMOUTH BASS AQUACULTURE OPTIMIZER -- PSO + EA")
        print(f"{'='*72}")
        print(f"  Fish: 10-{MAX_FISH_COUNT} (evolved)  |  Days: {AQUACULTURE_DAYS}  |  "
              f"Budget: ${MAX_BUDGET:.2f}  |  Workers: {workers}")
        print(f"  Ponds/gen: {POND_POPULATION}  |  Generations: {POND_GENERATIONS}  |  "
              f"Timelines: {RUN_TIMELINES}")
        print(f"  Selection: Elitism({EA_ELITISM_COUNT}) + Tournament(K={EA_TOURNAMENT_K})")
        print(f"  Parallelism: {workers} cores per generation")
        print(f"  Champion: Best pond in last generation")
        print(f"{'='*72}")

        all_csv_rows = []
        timeline_champions = []

        for tl_idx in range(RUN_TIMELINES):
            tl_start = _time.time()
            print(f"\n  --- Timeline {tl_idx+1}/{RUN_TIMELINES} ---\n")

            tl_seed = random.randint(0, 2**31)
            random.seed(tl_seed)

            ponds = [random_genotype() for _ in range(POND_POPULATION)]
            last_gen_results = None
            csv_rows = []

            for gen in range(POND_GENERATIONS):
                if len(ponds) <= 1 and last_gen_results is not None: break
                is_last = (gen == POND_GENERATIONS - 1)
                do_rec = record_best and is_last
                gen_start = _time.time()

                gen_results = []
                sim_tasks = []
                sim_indices = []

                for p_idx, geno in enumerate(ponds):
                    if geno.per_cycle_cost() > MAX_BUDGET:
                        r = {'fitness':0.0,'survival_rate':0,'avg_healthiness':0,
                             'saving':0,'cost':geno.total_cost(self.runtime),'yield':0,
                             'genotype_obj':geno,'genotype':geno.to_dict(),
                             'frames':[],'budget_exceeded':True,
                             'alive_count':0,'initial_count':geno.fish_count,'status':'GATEKEEPER'}
                        gen_results.append((p_idx, r))
                        csv_rows.append(_csv_row_data(tl_idx,gen,p_idx,'GATEKEEPER',r,geno.to_dict()))
                    else:
                        sim_seed = random.randint(0, 2**31)
                        sim_tasks.append((geno.to_dict(), self.runtime, MAX_BUDGET,
                                         do_rec, FRAME_SKIP, sim_seed))
                        sim_indices.append((p_idx, geno))

                if sim_tasks:
                    with ProcessPoolExecutor(max_workers=workers) as pool:
                        futures = {}
                        for i, task in enumerate(sim_tasks):
                            fut = pool.submit(_run_pond_worker, task)
                            futures[fut] = i

                        for fut in as_completed(futures):
                            i = futures[fut]
                            p_idx, geno = sim_indices[i]
                            r = fut.result()
                            r['genotype_obj'] = geno
                            if r.get('budget_exceeded'):
                                r['status'] = 'OVER-BUDGET'; r['fitness'] = 0.0
                            elif r.get('alive_count', 0) == 0:
                                r['status'] = 'ALL-DEAD'
                            else:
                                r['status'] = 'OK'
                            gen_results.append((p_idx, r))
                            csv_rows.append(_csv_row_data(tl_idx,gen,p_idx,r['status'],r,r['genotype']))

                gen_results.sort(key=lambda x: x[1]['fitness'], reverse=True)
                sorted_results = [r for _, r in gen_results]
                last_gen_results = sorted_results

                best_gen_fit = sorted_results[0]['fitness'] if sorted_results else 0
                n_ok = sum(1 for r in sorted_results if r.get('status') == 'OK')
                n_dead = sum(1 for r in sorted_results if r.get('status') == 'ALL-DEAD')
                n_over = sum(1 for r in sorted_results if r.get('status') == 'OVER-BUDGET')
                n_gate = sum(1 for r in sorted_results if r.get('status') == 'GATEKEEPER')
                gen_elapsed = _time.time() - gen_start
                print(f"    TL {tl_idx+1} | Gen {gen+1:>2}/{POND_GENERATIONS} | "
                      f"Best: {best_gen_fit:.4f} | OK: {n_ok:>2} | Dead: {n_dead:>2} | "
                      f"Over$: {n_over:>2} | Reject: {n_gate:>2} | {gen_elapsed:.1f}s")

                if not is_last:
                    if len(sorted_results) <= EA_ELITISM_COUNT:
                        break
                    elite_genos = [r['genotype_obj'] for r in sorted_results[:EA_ELITISM_COUNT]]
                    new_ponds = [copy.deepcopy(g) for g in elite_genos]
                    while len(new_ponds) < len(ponds):
                        parent_a = _tournament_select(sorted_results, EA_TOURNAMENT_K)
                        parent_b = _tournament_select(sorted_results, EA_TOURNAMENT_K)
                        if random.random() < EA_CROSSOVER_RATE:
                            child = crossover(parent_a, parent_b)
                        else:
                            child = copy.deepcopy(parent_a)
                        mutate(child)
                        new_ponds.append(child)
                    ponds = new_ponds

            # ── Last pond champion = best in last generation ──
            last_champ = None
            if last_gen_results:
                for r in last_gen_results:
                    if r.get('fitness', 0) > 0:
                        last_champ = r
                        break
                if last_champ is None:
                    last_champ = last_gen_results[0]
                    last_champ['is_latest_dead'] = True
                    print(f"    TL {tl_idx+1} | No valid last pond champion -- using Latest Dead")

            if last_champ:
                last_champ['timeline_idx'] = tl_idx
                last_champ.pop('genotype_obj', None)
            else:
                last_champ = {
                    'timeline_idx':tl_idx,'fitness':0,'survival_rate':0,
                    'avg_healthiness':0,'saving':0,'cost':0,'yield':0,
                    'genotype':random_genotype().to_dict(),'frames':[],'alive_count':0,
                    'initial_count':0,'is_latest_dead':True}

            tl_elapsed = _time.time() - tl_start
            tag = " [LATEST DEAD]" if last_champ.get('is_latest_dead') else ""
            print(f"\n  Timeline {tl_idx+1} finished ({tl_elapsed:.1f}s) | "
                  f"Fitness={last_champ['fitness']:.4f} | "
                  f"Alive={last_champ.get('alive_count',0)}/{last_champ.get('initial_count',0)}{tag}")

            all_csv_rows.extend(csv_rows)
            timeline_champions.append(last_champ)

        # ── Save CSV ──
        with open(RESULTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f); writer.writerow(CSV_HEADER); writer.writerows(all_csv_rows)
        print(f"\n  Saved {RESULTS_CSV_PATH} ({len(all_csv_rows)} rows)")

        # ── Print last pond champions ──
        for champ in timeline_champions:
            tl = champ.get('timeline_idx', 0)
            tag = " [LATEST DEAD]" if champ.get('is_latest_dead') else ""
            if champ['fitness'] > 0 or champ.get('is_latest_dead'):
                _print_champion_detail(f"TL {tl+1} Last Pond Champion{tag}", champ)
            else:
                print(f"\n  Timeline {tl+1}: No survivors.")

        real_champs = [c for c in timeline_champions if c.get('fitness',0) > 0 and not c.get('is_latest_dead')]
        if real_champs:
            valid = real_champs
        else:
            valid = [c for c in timeline_champions if c.get('genotype')]

        if not valid:
            print(f"\n{'='*72}\n  No valid champions across all {RUN_TIMELINES} timelines.\n{'='*72}")
            return None

        print(f"\n{'='*72}")
        best_idx = _print_champions_summary(timeline_champions)
        champ = timeline_champions[best_idx]

        # ── Re-run best pond champion with recording if needed ──
        if record_best and not champ.get('frames'):
            tag = " [LATEST DEAD]" if champ.get('is_latest_dead') else ""
            print(f"\n  Re-running last pond champion{tag} (TL {champ['timeline_idx']+1}) with frame recording...")
            res = run_single_pond(champ['genotype'], self.runtime, MAX_BUDGET, True, FRAME_SKIP)
            champ['frames'] = res['frames']

        wall_elapsed = _time.time() - wall_start
        tag = " [LATEST DEAD]" if champ.get('is_latest_dead') else ""
        _print_champion_detail(f"BEST POND CHAMPION{tag}  (TL {champ['timeline_idx']+1})", champ)
        print(f"\n  Total wall time: {wall_elapsed:.1f}s")
        return champ