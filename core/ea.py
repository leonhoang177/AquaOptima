#!/usr/bin/env python3
"""
ea.py -- Evolutionary Algorithm: pond configuration evolution with parallel timelines.
"""

import random, copy, csv, time as _time, multiprocessing
from concurrent.futures import ProcessPoolExecutor, as_completed

from constants import (
    MAX_BUDGET, INITIAL_FISH_POPULATION, AQUACULTURE_DAYS,
    POND_GENERATIONS, RUN_TIMELINES, INITIAL_POND_COUNT,
    FRAME_SKIP, NUM_WORKERS, RUNTIME, RESULTS_CSV_PATH,
)
from entities import PondGenotype
from helpers import _make_fish, _fish_to_dict, _dict_to_fish
from pond import PondSim
from log import _print_champion_detail, _print_champions_summary

CSV_HEADER = [
    'timeline', 'generation', 'pond', 'status',
    'fitness', 'survival_rate', 'healthiness', 'cost',
    'efficiency', 'alive_count', 'initial_count',
    'food_interval', 'food_quantity', 'food_location',
    'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
    'oxygen_interval', 'oxygen_duration', 'oxygen_location',
]

def _csv_row_data(tl_idx, gen_idx, pond_idx, status, result, geno_dict):
    return [
        tl_idx+1, gen_idx+1, pond_idx, status,
        f"{result.get('fitness',0):.4f}", f"{result.get('survival_rate',0):.4f}",
        f"{result.get('avg_healthiness',0):.4f}", f"{result.get('cost',0):.2f}",
        f"{result.get('efficiency',0):.4f}", result.get('alive_count',0),
        result.get('initial_count',0),
        geno_dict.get('food_interval',''), geno_dict.get('food_quantity',''),
        geno_dict.get('food_location',''), geno_dict.get('probiotic_interval',''),
        geno_dict.get('probiotic_quantity',''), geno_dict.get('probiotic_location',''),
        geno_dict.get('oxygen_interval',''), geno_dict.get('oxygen_duration',''),
        geno_dict.get('oxygen_location',''),
    ]

def _run_timeline_worker(args):
    tl_idx, fish_data, runtime, max_budget, pond_generations, \
        initial_pond_count, record_best, frame_skip, seed = args
    random.seed(seed)

    ponds = [PondGenotype.random() for _ in range(initial_pond_count)]
    best_result = None
    csv_rows = []

    for gen in range(pond_generations):
        if len(ponds) <= 1 and best_result is not None: break
        is_last = (gen == pond_generations - 1)
        do_rec = record_best and is_last and len(ponds) <= 4

        gen_results = []
        for p_idx, geno in enumerate(ponds):
            if geno.per_cycle_cost() > max_budget:
                r = {'fitness':0.0,'survival_rate':0,'avg_healthiness':0,
                     'efficiency':0,'cost':geno.total_cost(runtime),
                     'genotype_obj':geno,'genotype':geno.to_dict(),
                     'frames':[],'budget_exceeded':True,
                     'alive_count':0,'initial_count':len(fish_data),'status':'GATEKEEPER'}
                gen_results.append(r)
                csv_rows.append(_csv_row_data(tl_idx,gen,p_idx,'GATEKEEPER',r,geno.to_dict()))
                continue
            sim_seed = random.randint(0, 2**31)
            random.seed(sim_seed)
            geno_obj = PondGenotype(**geno.to_dict())
            fishes = [_dict_to_fish(fd) for fd in fish_data]
            sim = PondSim(geno_obj, fishes, runtime, max_budget, record=do_rec, fskip=frame_skip)
            r = sim.run()
            r['genotype_obj'] = geno
            if r.get('budget_exceeded'):
                r['status'] = 'OVER-BUDGET'; r['fitness'] = 0.0
            elif r.get('survival_rate',0) == 0:
                r['status'] = 'ALL-DEAD'
            else:
                r['status'] = 'OK'
            gen_results.append(r)
            csv_rows.append(_csv_row_data(tl_idx,gen,p_idx,r['status'],r,r['genotype']))

        gen_results.sort(key=lambda x: x['fitness'], reverse=True)

        # ── Progress log ──
        best_gen_fit = gen_results[0]['fitness'] if gen_results else 0
        ok_count = sum(1 for r in gen_results if r.get('status') == 'OK')
        print(f"    TL {tl_idx+1} | Gen {gen+1:>2}/{pond_generations} | "
              f"Best: {best_gen_fit:.4f} | OK: {ok_count}/{len(gen_results)}")

        if gen_results and gen_results[0]['fitness'] > 0:
            if best_result is None or gen_results[0]['fitness'] > best_result['fitness']:
                best_result = gen_results[0]

        half = max(1, len(gen_results) // 2)
        survivors = gen_results[:half]
        if len(survivors) <= 1: break

        surv_genos = [r['genotype_obj'] for r in survivors]
        new_ponds = [copy.deepcopy(g) for g in surv_genos]
        while len(new_ponds) < len(ponds):
            child = random.choice(surv_genos).crossover(random.choice(surv_genos))
            child.mutate(); new_ponds.append(child)
        ponds = new_ponds

    if best_result:
        best_result['timeline_idx'] = tl_idx
        best_result['fish_data'] = fish_data
        best_result.pop('genotype_obj', None)
    else:
        best_result = {
            'timeline_idx':tl_idx,'fitness':0,'survival_rate':0,
            'avg_healthiness':0,'efficiency':0,'cost':0,
            'genotype':{},'frames':[],'alive_count':0,
            'initial_count':len(fish_data),'fish_data':fish_data}
    return {'champion': best_result, 'csv_rows': csv_rows}

class EA:
    def __init__(self):
        self.runtime = RUNTIME

    def run(self, record_best=True):
        wall_start = _time.time()
        workers = NUM_WORKERS or max(1, multiprocessing.cpu_count())
        print(f"\n{'='*72}")
        print(f"  LARGEMOUTH BASS AQUACULTURE OPTIMIZER -- PSO + EA")
        print(f"{'='*72}")
        print(f"  Fish: {INITIAL_FISH_POPULATION}  |  Days: {AQUACULTURE_DAYS}  |  "
              f"Budget: ${MAX_BUDGET:.2f}  |  Workers: {workers}")
        print(f"  Ponds/gen: {INITIAL_POND_COUNT}  |  Generations: {POND_GENERATIONS}  |  "
              f"Timelines: {RUN_TIMELINES}")
        print(f"{'='*72}")

        timeline_tasks = []
        for tl_idx in range(RUN_TIMELINES):
            base_fishes = [_make_fish(i) for i in range(INITIAL_FISH_POPULATION)]
            fish_data = [_fish_to_dict(f) for f in base_fishes]
            seed = random.randint(0, 2**31)
            timeline_tasks.append((tl_idx, fish_data, self.runtime, MAX_BUDGET,
                POND_GENERATIONS, INITIAL_POND_COUNT, record_best, FRAME_SKIP, seed))

        print(f"\n  Launching {RUN_TIMELINES} timelines in parallel...\n")
        timeline_results = [None] * RUN_TIMELINES
        with ProcessPoolExecutor(max_workers=min(workers, RUN_TIMELINES)) as pool:
            futures = {pool.submit(_run_timeline_worker, t): t[0] for t in timeline_tasks}
            for fut in as_completed(futures):
                tl_idx = futures[fut]
                result = fut.result()
                timeline_results[tl_idx] = result
                champ = result['champion']
                elapsed = _time.time() - wall_start
                print(f"\n  Timeline {tl_idx+1} finished ({elapsed:.1f}s) | "
                      f"Fitness={champ['fitness']:.4f} | "
                      f"Survival={champ['survival_rate']*100:.2f}%")

        all_csv_rows = []
        timeline_champions = []
        for tl_idx in range(RUN_TIMELINES):
            res = timeline_results[tl_idx]
            all_csv_rows.extend(res['csv_rows'])
            timeline_champions.append(res['champion'])

        with open(RESULTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f); writer.writerow(CSV_HEADER); writer.writerows(all_csv_rows)
        print(f"\n  Saved {RESULTS_CSV_PATH} ({len(all_csv_rows)} rows)")

        for champ in timeline_champions:
            tl = champ.get('timeline_idx', 0)
            if champ['fitness'] > 0:
                _print_champion_detail(f"Timeline {tl+1} Champion", champ)
            else:
                print(f"\n  Timeline {tl+1}: No survivors.")

        valid = [c for c in timeline_champions if c.get('fitness',0) > 0]
        if not valid:
            print(f"\n{'='*72}\n  No valid champions across all {RUN_TIMELINES} timelines.\n{'='*72}")
            return None

        print(f"\n{'='*72}")
        best_idx = _print_champions_summary(timeline_champions)
        champ = timeline_champions[best_idx]

        if record_best and not champ.get('frames'):
            print(f"\n  Re-running champion (Timeline {champ['timeline_idx']+1}) with frame recording...")
            stored_fish_data = champ.get('fish_data', [])
            if stored_fish_data:
                fishes = [_dict_to_fish(fd) for fd in stored_fish_data]
            else:
                fishes = [_make_fish(i) for i in range(INITIAL_FISH_POPULATION)]
            geno = PondGenotype(**champ['genotype'])
            sim = PondSim(geno, fishes, self.runtime, MAX_BUDGET, record=True, fskip=FRAME_SKIP)
            res = sim.run()
            champ['frames'] = res['frames']

        wall_elapsed = _time.time() - wall_start
        _print_champion_detail(f"GRAND CHAMPION  (Timeline {champ['timeline_idx']+1})", champ)
        print(f"\n  Total wall time: {wall_elapsed:.1f}s")
        return champ