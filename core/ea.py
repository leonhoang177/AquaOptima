#!/usr/bin/env python3
"""
ea.py -- Evolutionary Algorithm with fully parallel timelines,
         priority-based task scheduling, and async verified selection.

Priority model:
    (timeline, generation, task_type)
    - Lower timeline = higher priority (TL1 first)
    - Lower generation = higher priority
    - task_type: 0=Sim, 1=Ver  (Sim > Ver)

All timelines run concurrently through a single PriorityPool.
TL1 gets all cores; TL2/TL3 fill idle gaps.
Results are stored per-timeline and logged sequentially at the end.

Dual output:
    - Console: real-time interleaved progress (also mirrored to demo.txt)
    - Log file: demo.txt captures all terminal output

Fitness = W1_SURVIVAL_RATE * survival_rate
        + W2_SAVING_RATE   * saving_rate
        + W3_HEALTHINESS   * healthiness

Options:
    A: fish_count fixed at INITIAL_FISH_COUNT (not in genotype)
    E: Memory-based fitness accumulation per timeline
    F: Wilcoxon-verified tournament selection with cascade
"""

import random, copy, csv, time as _time, multiprocessing, hashlib, json, threading, os, sys
from collections import defaultdict
from queue import Queue, Empty
from concurrent.futures import ProcessPoolExecutor
import heapq

from scipy.stats import mannwhitneyu

from constants import (
    MAX_BUDGET, INITIAL_FISH_COUNT, AQUACULTURE_DAYS,
    POND_GENERATIONS, RUN_TIMELINES, POND_POPULATION,
    FRAME_SKIP, NUM_WORKERS, RUNTIME, RESULTS_CSV_PATH,
    EA_ELITISM_COUNT, EA_TOURNAMENT_K,
    EA_CROSSOVER_RATE, EA_MUTATION_RATE,
    FOOD_INTERVAL_RANGE, FOOD_QUANTITY_RANGE,
    PROBIOTIC_QUANTITY_RANGE, PROBIOTIC_INTERVAL_STEPS,
    OXYGEN_INTERVAL_RANGE, OXYGEN_DURATION_RANGE,
    VERIFY_MIN_SAMPLES, VERIFY_ALPHA,
    VERIFY_MAX_CASCADE_DEPTH, VERIFY_SKIP_THRESHOLD,
    DEMO_LOG_PATH, LOCATION_OPTIONS,
)

from entities import PondGenotype
from simulate import run_single_pond
from log import _print_champion_detail, _print_champions_summary


# ════════════════════════════════════════════════════════════════
# TEE LOGGER — mirrors all print output to demo.txt
# ════════════════════════════════════════════════════════════════

class TeeLogger:
    """Write to both stdout and a log file simultaneously."""
    def __init__(self, filepath):
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        self.file = open(filepath, 'w', encoding='utf-8')
        self.stdout = sys.stdout

    def write(self, msg):
        self.stdout.write(msg)
        self.file.write(msg)
        self.file.flush()

    def flush(self):
        self.stdout.flush()
        self.file.flush()

    def close(self):
        self.file.close()
        sys.stdout = self.stdout


# ════════════════════════════════════════════════════════════════
# GENOTYPE IDENTITY KEY
# ════════════════════════════════════════════════════════════════

def _geno_key(geno: PondGenotype) -> str:
    d = geno.to_dict()
    return hashlib.md5(json.dumps(d, sort_keys=True).encode()).hexdigest()


# ════════════════════════════════════════════════════════════════
# MUTATION HELPERS (Gaussian perturbation)
# ════════════════════════════════════════════════════════════════

def _perturb_int(value, lo, hi, step):
    """Perturb an integer value by ±step, clamped to [lo, hi]."""
    new_val = value + random.randint(-step, step)
    return max(lo, min(hi, new_val))


def _perturb_choice(value, choices, n_steps):
    """Perturb a value within an ordered list by ±n_steps positions."""
    if value not in choices:
        return random.choice(choices)
    idx = choices.index(value)
    new_idx = idx + random.randint(-n_steps, n_steps)
    new_idx = max(0, min(len(choices) - 1, new_idx))
    return choices[new_idx]


# ════════════════════════════════════════════════════════════════
# EA GENOTYPE OPERATIONS
# ════════════════════════════════════════════════════════════════

def random_genotype() -> PondGenotype:
    return PondGenotype(
        food_interval=random.randint(*FOOD_INTERVAL_RANGE),
        food_quantity=random.randint(*FOOD_QUANTITY_RANGE),
        food_location=random.choice(LOCATION_OPTIONS),
        probiotic_interval=random.choice(PROBIOTIC_INTERVAL_STEPS),
        probiotic_quantity=random.randint(*PROBIOTIC_QUANTITY_RANGE),
        probiotic_location=random.choice(LOCATION_OPTIONS),
        oxygen_interval=random.randint(*OXYGEN_INTERVAL_RANGE),
        oxygen_duration=random.randint(*OXYGEN_DURATION_RANGE),
        oxygen_location=random.choice(LOCATION_OPTIONS))


def crossover(a: PondGenotype, b: PondGenotype) -> PondGenotype:
    child = PondGenotype()
    for attr in a.to_dict():
        setattr(child, attr, getattr(a if random.random() < 0.5 else b, attr))
    return child


def mutate(geno: PondGenotype):
    """Gaussian perturbation mutation. Numeric genes get small adjustments.
    Location genes (binary: Center/Random) get flipped."""
    r = EA_MUTATION_RATE
    # Food policy
    if random.random() < r:
        geno.food_interval = _perturb_int(geno.food_interval, *FOOD_INTERVAL_RANGE, step=4)
    if random.random() < r:
        geno.food_quantity = _perturb_int(geno.food_quantity, *FOOD_QUANTITY_RANGE, step=2)
    if random.random() < r:
        geno.food_location = 9 if geno.food_location == 0 else 0  # binary flip

    # Probiotic policy
    if random.random() < r:
        geno.probiotic_interval = _perturb_choice(geno.probiotic_interval,
                                                    PROBIOTIC_INTERVAL_STEPS, n_steps=1)
    if random.random() < r:
        geno.probiotic_quantity = _perturb_int(geno.probiotic_quantity,
                                                *PROBIOTIC_QUANTITY_RANGE, step=1)
    if random.random() < r:
        geno.probiotic_location = 9 if geno.probiotic_location == 0 else 0  # binary flip

    # Oxygen policy
    if random.random() < r:
        geno.oxygen_interval = _perturb_int(geno.oxygen_interval, *OXYGEN_INTERVAL_RANGE, step=4)
    if random.random() < r:
        geno.oxygen_duration = _perturb_int(geno.oxygen_duration, *OXYGEN_DURATION_RANGE, step=1)
    if random.random() < r:
        geno.oxygen_location = 9 if geno.oxygen_location == 0 else 0  # binary flip


# ════════════════════════════════════════════════════════════════
# CSV / HELPERS
# ════════════════════════════════════════════════════════════════

CSV_HEADER = [
    'timeline', 'generation', 'pond', 'status',
    'fitness', 'survival_rate', 'saving_rate', 'healthiness', 'cost',
    'alive_count', 'initial_count',
    'food_interval', 'food_quantity', 'food_location',
    'probiotic_interval', 'probiotic_quantity', 'probiotic_location',
    'oxygen_interval', 'oxygen_duration', 'oxygen_location',
]


def _csv_row_data(tl_idx, gen_idx, pond_idx, status, result, geno_dict):
    return [
        tl_idx + 1, gen_idx + 1, pond_idx, status,
        f"{result.get('fitness', 0):.4f}",
        f"{result.get('survival_rate', 0):.4f}",
        f"{result.get('saving_rate', 0):.4f}",
        f"{result.get('avg_healthiness', 0):.4f}",
        f"{result.get('cost', 0):.2f}",
        result.get('alive_count', 0), result.get('initial_count', 0),
        geno_dict.get('food_interval', ''), geno_dict.get('food_quantity', ''),
        geno_dict.get('food_location', ''), geno_dict.get('probiotic_interval', ''),
        geno_dict.get('probiotic_quantity', ''), geno_dict.get('probiotic_location', ''),
        geno_dict.get('oxygen_interval', ''), geno_dict.get('oxygen_duration', ''),
        geno_dict.get('oxygen_location', ''),
    ]


def _run_pond_worker(args):
    geno_dict, runtime, max_budget, do_rec, frame_skip, seed = args
    return run_single_pond(geno_dict, runtime, max_budget, do_rec, frame_skip, seed)


# ════════════════════════════════════════════════════════════════
# FITNESS MEMORY (Option E) — one per timeline
# ════════════════════════════════════════════════════════════════

class FitnessMemory:
    def __init__(self):
        self._samples = defaultdict(list)

    def record(self, geno: PondGenotype, fitness: float):
        self._samples[_geno_key(geno)].append(fitness)

    def get_samples(self, geno: PondGenotype) -> list:
        return self._samples.get(_geno_key(geno), [])

    def get_mean(self, geno: PondGenotype) -> float:
        s = self.get_samples(geno)
        return sum(s) / len(s) if s else 0.0

    def sample_count(self, geno: PondGenotype) -> int:
        return len(self._samples.get(_geno_key(geno), []))


# ════════════════════════════════════════════════════════════════
# WILCOXON COMPARISON (Option F)
# ════════════════════════════════════════════════════════════════

def _wilcoxon_compare(samples_a, samples_b, alpha=VERIFY_ALPHA):
    if len(samples_a) < 2 or len(samples_b) < 2:
        mean_a = sum(samples_a) / len(samples_a)
        mean_b = sum(samples_b) / len(samples_b)
        if mean_a > mean_b: return 'a_better'
        elif mean_b > mean_a: return 'b_better'
        return 'inconclusive'
    try:
        stat, p = mannwhitneyu(samples_a, samples_b, alternative='two-sided')
    except ValueError:
        return 'inconclusive'
    if p < alpha:
        median_a = sorted(samples_a)[len(samples_a) // 2]
        median_b = sorted(samples_b)[len(samples_b) // 2]
        if median_a > median_b: return 'a_better'
        elif median_b > median_a: return 'b_better'
    return 'inconclusive'


# ════════════════════════════════════════════════════════════════
# PRIORITY POOL
# ════════════════════════════════════════════════════════════════

# Task types
TASK_SIM = 0
TASK_VER = 1


class PriorityPool:
    """
    Persistent process pool with priority-based task scheduling.
    Priority tuple: (timeline, generation, task_type, sequence)
    Lower = higher priority. Sequence is a tiebreaker for FIFO within same priority.

    Timeline is highest priority — TL1 gets all cores, TL2/TL3 fill idle gaps.
    """

    def __init__(self, max_workers):
        self.executor = ProcessPoolExecutor(max_workers=max_workers)
        self.max_workers = max_workers
        self.in_flight = 0
        self.pending = []           # min-heap of (priority_tuple, task_args, tag)
        self.seq = 0                # monotonic tiebreaker
        self.lock = threading.Lock()
        self.result_queue = Queue() # results flow to main thread

    def submit(self, task_args, timeline, gen, task_type, tag=None):
        with self.lock:
            self.seq += 1
            priority = (timeline, gen, task_type, self.seq)
            heapq.heappush(self.pending, (priority, task_args, tag))
            self._drain()

    def _drain(self):
        """Submit highest-priority pending tasks to fill available cores."""
        while self.in_flight < self.max_workers and self.pending:
            priority, task_args, tag = heapq.heappop(self.pending)
            future = self.executor.submit(_run_pond_worker, task_args)
            self.in_flight += 1
            future.add_done_callback(lambda f, t=tag: self._on_done(f, t))

    def _on_done(self, future, tag):
        with self.lock:
            self.in_flight -= 1
            try:
                result = future.result()
            except Exception as e:
                result = {'fitness': 0, 'error': str(e)}
            self.result_queue.put((tag, result))
            self._drain()  # immediately fill the freed core

    def get_result(self, timeout=None):
        return self.result_queue.get(timeout=timeout)

    def shutdown(self):
        self.executor.shutdown(wait=True)


# ════════════════════════════════════════════════════════════════
# TOURNAMENT STATE MACHINE
# ════════════════════════════════════════════════════════════════

class TournamentState:
    """
    State machine for a single tournament with Wilcoxon cascade.
    States: NEED_CURRENT_SAMPLES → NEED_CHALLENGER_SAMPLES → COMPARING → RESOLVED
    """
    def __init__(self, candidates, tournament_idx):
        self.candidates = candidates  # sorted by memory average, descending
        self.tournament_idx = tournament_idx
        self.current_idx = 0
        self.challenger_idx = 1
        self.resolved = False
        self.winner = None
        self.cascade_depth = 0

    def get_current(self):
        if self.current_idx < len(self.candidates):
            return self.candidates[self.current_idx]
        return None

    def get_challenger(self):
        if self.challenger_idx < len(self.candidates):
            return self.candidates[self.challenger_idx]
        return None

    def advance_cascade(self):
        self.challenger_idx += 1
        self.cascade_depth += 1

    def resolve(self, winner):
        self.winner = winner
        self.resolved = True


# ════════════════════════════════════════════════════════════════
# TOURNAMENT MANAGER
# ════════════════════════════════════════════════════════════════

class TournamentMgr:
    """
    Manages all tournaments for a generation.
    Processes verification results and advances tournament state machines.
    Submits verification top-ups lazily per cascade depth.
    """

    def __init__(self, gen_results, n_children, k, memory, pool,
                 tl_idx, gen_idx, runtime, max_budget):
        self.memory = memory
        self.pool = pool
        self.tl_idx = tl_idx
        self.gen_idx = gen_idx
        self.runtime = runtime
        self.max_budget = max_budget
        self.n_tournaments = n_children * 2  # 2 parents per child
        self.tournaments = []
        self.pending_genos = {}   # geno_key → set of tournament indices waiting
        self.ver_in_flight = 0
        self.total_ver_evals = 0
        self.resolved_parents = [None] * self.n_tournaments
        self.n_resolved = 0
        self.children = [None] * n_children
        self.n_children_ready = 0

        # Pre-draw all tournaments
        for i in range(self.n_tournaments):
            candidates = random.sample(gen_results, min(k, len(gen_results)))
            candidates.sort(key=lambda r: self.memory.get_mean(r['genotype_obj']),
                          reverse=True)
            depth = min(VERIFY_MAX_CASCADE_DEPTH + 1, len(candidates))
            self.tournaments.append(TournamentState(candidates[:depth], i))

    def start(self):
        """Kick off all tournaments."""
        for t in self.tournaments:
            self._advance(t)

    def on_ver_result(self, geno_key, result):
        """Called when a verification eval completes."""
        fitness = result.get('fitness', 0)
        elapsed = result.get('_worker_elapsed', 0)
        self.ver_in_flight -= 1

        # Find the genotype object and record
        waiting = self.pending_genos.pop(geno_key, set())
        for t_idx in waiting:
            t = self.tournaments[t_idx]
            for c in t.candidates:
                if _geno_key(c['genotype_obj']) == geno_key:
                    self.memory.record(c['genotype_obj'], fitness)
                    break
            break  # record once

        # Advance all tournaments that were waiting for this genotype
        for t_idx in waiting:
            t = self.tournaments[t_idx]
            if not t.resolved:
                self._advance(t)

        return elapsed

    def _advance(self, t):
        """Try to advance a tournament's state machine."""
        if t.resolved:
            return

        current = t.get_current()
        if current is None:
            t.resolve(t.candidates[0] if t.candidates else None)
            self._on_resolved(t)
            return

        current_geno = current['genotype_obj']
        current_key = _geno_key(current_geno)
        current_samples = self.memory.sample_count(current_geno)

        # Ensure current has enough samples
        if current_samples < VERIFY_MIN_SAMPLES:
            needed = VERIFY_MIN_SAMPLES - current_samples
            self._submit_topups(current_geno, current_key, t.tournament_idx, needed)
            return  # wait for results

        challenger = t.get_challenger()

        # No more challengers or max cascade depth reached
        if challenger is None or t.cascade_depth >= VERIFY_MAX_CASCADE_DEPTH:
            t.resolve(current)
            self._on_resolved(t)
            return

        challenger_geno = challenger['genotype_obj']
        challenger_key = _geno_key(challenger_geno)

        # Skip threshold check before verifying challenger
        current_mean = self.memory.get_mean(current_geno)
        challenger_mean = self.memory.get_mean(challenger_geno)
        if current_mean - challenger_mean > VERIFY_SKIP_THRESHOLD:
            t.resolve(current)
            self._on_resolved(t)
            return

        # Ensure challenger has enough samples
        challenger_samples = self.memory.sample_count(challenger_geno)
        if challenger_samples < VERIFY_MIN_SAMPLES:
            needed = VERIFY_MIN_SAMPLES - challenger_samples
            self._submit_topups(challenger_geno, challenger_key, t.tournament_idx, needed)
            return  # wait for results

        # Both have enough samples — Wilcoxon compare
        current_s = self.memory.get_samples(current_geno)
        challenger_s = self.memory.get_samples(challenger_geno)
        result = _wilcoxon_compare(current_s, challenger_s)

        if result == 'a_better':
            # Current confirmed
            t.resolve(current)
            self._on_resolved(t)
        elif result == 'b_better':
            # Challenger dethroned current
            t.current_idx = t.challenger_idx
            t.advance_cascade()
            self._advance(t)  # recurse with new current
        else:
            # Inconclusive — try next challenger, current holds
            t.advance_cascade()
            self._advance(t)

    def _submit_topups(self, geno, geno_key, tournament_idx, needed):
        """Submit verification evals, deduplicating across tournaments."""
        if geno_key in self.pending_genos:
            # Already in flight — just register this tournament as waiting
            self.pending_genos[geno_key].add(tournament_idx)
            return

        self.pending_genos[geno_key] = {tournament_idx}
        for _ in range(needed):
            seed = random.randint(0, 2**31)
            task_args = (geno.to_dict(), self.runtime, MAX_BUDGET, False, FRAME_SKIP, seed)
            tag = ('ver', self.tl_idx, self.gen_idx, geno_key)
            self.pool.submit(task_args, self.tl_idx, self.gen_idx, TASK_VER, tag=tag)
            self.ver_in_flight += 1
            self.total_ver_evals += 1

    def _on_resolved(self, t):
        """Called when a tournament resolves."""
        idx = t.tournament_idx
        self.resolved_parents[idx] = t.winner
        self.n_resolved += 1

        # Check if pair partner is also resolved
        pair_idx = idx // 2
        a_idx = pair_idx * 2
        b_idx = pair_idx * 2 + 1

        if b_idx < self.n_tournaments:
            if (self.resolved_parents[a_idx] is not None and
                self.resolved_parents[b_idx] is not None and
                self.children[pair_idx] is None):
                # Both parents ready — create child
                parent_a = self.resolved_parents[a_idx]['genotype_obj']
                parent_b = self.resolved_parents[b_idx]['genotype_obj']
                if random.random() < EA_CROSSOVER_RATE:
                    child = crossover(parent_a, parent_b)
                else:
                    child = copy.deepcopy(parent_a)
                mutate(child)
                self.children[pair_idx] = child
                self.n_children_ready += 1

    @property
    def all_resolved(self):
        return self.n_resolved >= self.n_tournaments

    @property
    def all_children_ready(self):
        expected = self.n_tournaments // 2
        return self.n_children_ready >= expected


# ════════════════════════════════════════════════════════════════
# TIMELINE STATE
# ════════════════════════════════════════════════════════════════

class TimelineState:
    def __init__(self, tl_idx, n_timelines):
        self.tl_idx = tl_idx
        self.n_timelines = n_timelines
        self.gen = 0
        self.ponds = [random_genotype() for _ in range(POND_POPULATION)]
        self.memory = FitnessMemory()
        self.gen_results = []
        self.sim_pending = 0
        self.tournament_mgr = None
        self.finished = False
        self.csv_rows = []
        self.champion = None

        # Timing
        self.gen_run_time = {}        # gen → cumulative run-seconds
        self.total_run_time = 0.0     # cumulative run-seconds across all gens

        # Diagnostics — wall-clock for overlap detection
        self.first_sim_start = None   # wall-clock: first sim actually started
        self.last_ver_complete = None  # wall-clock: last ver completed

    def _fmt_run_time(self, seconds):
        if seconds < 60:
            return f"{seconds:.1f}s"
        return f"{seconds / 60:.1f}m"


# ════════════════════════════════════════════════════════════════
# EA CLASS
# ════════════════════════════════════════════════════════════════

class EA:
    def __init__(self):
        self.runtime = RUNTIME

    def run(self, record_best=True):
        # Start tee logger — mirrors all print output to demo.txt
        tee = TeeLogger(DEMO_LOG_PATH)
        sys.stdout = tee

        wall_start = _time.time()
        workers = NUM_WORKERS or max(1, multiprocessing.cpu_count())

        print(f"\n{'=' * 72}")
        print(f"  LARGEMOUTH BASS AQUACULTURE OPTIMIZER -- PSO + EA")
        print(f"{'=' * 72}")
        print(f"  Initial-Fish: {INITIAL_FISH_COUNT}  |  Simulation-Days: {AQUACULTURE_DAYS}  |  "
              f"Budget: ${MAX_BUDGET:.2f}")
        print(f"  Pond-Population: {POND_POPULATION}  |  Pond-Generations: {POND_GENERATIONS}  |  "
              f"Timelines: {RUN_TIMELINES}")
        print(f"  Selection: Elitism({EA_ELITISM_COUNT}) + Verified-Tournament(K={EA_TOURNAMENT_K})")
        print(f"  Verification: Wilcoxon α={VERIFY_ALPHA}, min_samples={VERIFY_MIN_SAMPLES}, "
              f"cascade_depth={VERIFY_MAX_CASCADE_DEPTH}")
        print(f"  Mutation: Gaussian perturbation (rate={EA_MUTATION_RATE})")
        print(f"  Location: Binary (Center/Random)")
        print(f"  Parallelism: {workers} cores, persistent pool, priority scheduling")
        print(f"  Champion: Best pond in last generation")
        print(f"{'=' * 72}")

        pool = PriorityPool(max_workers=workers)

        # Initialize all timelines
        timelines = []
        for tl_idx in range(RUN_TIMELINES):
            tl = TimelineState(tl_idx, RUN_TIMELINES)
            timelines.append(tl)

        # Pre-schedule all Gen-1 Sims for all timelines
        for tl in timelines:
            self._submit_gen_sims(tl, pool)

        # Event-driven main loop
        while not all(tl.finished for tl in timelines):
            try:
                tag, result = pool.get_result(timeout=120)
            except Empty:
                print("  WARNING: Timeout waiting for result")
                break

            if tag is None:
                continue

            tag_type = tag[0]
            tl_idx = tag[1]
            tl = timelines[tl_idx]

            if tag_type == 'sim':
                self._handle_sim_result(tl, tag, result, pool)
            elif tag_type == 'ver':
                self._handle_ver_result(tl, tag, result, pool)

        pool.shutdown()

        # ── Collect results ──
        all_csv_rows = []
        timeline_champions = []

        for tl in timelines:
            all_csv_rows.extend(tl.csv_rows)

            champ = tl.champion
            if champ:
                champ['timeline_idx'] = tl.tl_idx
                timeline_champions.append(champ)
            else:
                timeline_champions.append({
                    'timeline_idx': tl.tl_idx, 'fitness': 0, 'survival_rate': 0,
                    'avg_healthiness': 0, 'saving_rate': 0, 'cost': 0,
                    'genotype': random_genotype().to_dict(), 'frames': [],
                    'alive_count': 0, 'initial_count': 0, 'is_latest_dead': True})

        # ── Save CSV ──
        os.makedirs(os.path.dirname(RESULTS_CSV_PATH), exist_ok=True)
        with open(RESULTS_CSV_PATH, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(CSV_HEADER)
            writer.writerows(all_csv_rows)
        print(f"\n  Saved {RESULTS_CSV_PATH} ({len(all_csv_rows)} rows)")

        # ── Print champions ──
        for champ in timeline_champions:
            tl_i = champ.get('timeline_idx', 0)
            tag = " [LATEST DEAD]" if champ.get('is_latest_dead') else ""
            if champ['fitness'] > 0 or champ.get('is_latest_dead'):
                _print_champion_detail(f"TL {tl_i + 1} Last Pond Champion{tag}", champ)

        real_champs = [c for c in timeline_champions
                       if c.get('fitness', 0) > 0 and not c.get('is_latest_dead')]
        if real_champs:
            valid = real_champs
        else:
            valid = [c for c in timeline_champions if c.get('genotype')]

        if not valid:
            print(f"\n{'=' * 72}\n  No valid champions.\n{'=' * 72}")
            tee.close()
            return None

        print(f"\n{'=' * 72}")
        best_idx = _print_champions_summary(timeline_champions)
        champ = timeline_champions[best_idx]

        # Re-run best champion with recording if needed
        if record_best and not champ.get('frames'):
            tag = " [LATEST DEAD]" if champ.get('is_latest_dead') else ""
            print(f"\n  Re-running champion{tag} (TL {champ['timeline_idx'] + 1}) with recording...")
            res = run_single_pond(champ['genotype'], self.runtime, MAX_BUDGET, True, FRAME_SKIP)
            champ['frames'] = res['frames']

        wall_elapsed = _time.time() - wall_start
        tag = " [LATEST DEAD]" if champ.get('is_latest_dead') else ""
        _print_champion_detail(f"BEST POND CHAMPION{tag}  (TL {champ['timeline_idx'] + 1})", champ)
        print(f"\n  Total wall time: {wall_elapsed:.1f}s")

        # ── Diagnostics ──
        self._print_diagnostics(timelines, wall_start)

        print(f"\n  Saved {DEMO_LOG_PATH}")

        # Close tee logger
        tee.close()

        return champ

    # ────────────────────────────────────────────────────────────
    # SUBMIT GENERATION SIMS
    # ────────────────────────────────────────────────────────────

    def _submit_gen_sims(self, tl, pool):
        """Submit all pond simulations for the current generation."""
        tl.gen_results = []
        tl.sim_pending = 0
        tl.gen_run_time[tl.gen] = 0.0

        is_last = (tl.gen == POND_GENERATIONS - 1)
        do_rec = is_last  # only record frames on last generation

        for p_idx, geno in enumerate(tl.ponds):
            # Gatekeeper check
            if geno.per_cycle_cost() > MAX_BUDGET:
                r = {'fitness': 0.0, 'survival_rate': 0, 'avg_healthiness': 0,
                     'saving_rate': 0, 'cost': geno.total_cost(self.runtime),
                     'genotype_obj': geno, 'genotype': geno.to_dict(),
                     'frames': [], 'budget_exceeded': True,
                     'alive_count': 0, 'initial_count': INITIAL_FISH_COUNT,
                     'status': 'GATEKEEPER', '_worker_elapsed': 0}
                tl.gen_results.append(r)
                tl.memory.record(geno, 0.0)
                tl.csv_rows.append(_csv_row_data(tl.tl_idx, tl.gen, p_idx,
                                                  'GATEKEEPER', r, geno.to_dict()))
                continue

            seed = random.randint(0, 2**31)
            task_args = (geno.to_dict(), self.runtime, MAX_BUDGET,
                        do_rec, FRAME_SKIP, seed)
            tag = ('sim', tl.tl_idx, tl.gen, p_idx)
            pool.submit(task_args, tl.tl_idx, tl.gen, TASK_SIM, tag=tag)
            tl.sim_pending += 1

        # If all were gatekeepered, advance immediately
        if tl.sim_pending == 0:
            self._on_all_sims_done(tl, pool)

    # ────────────────────────────────────────────────────────────
    # HANDLE SIM RESULT
    # ────────────────────────────────────────────────────────────

    def _handle_sim_result(self, tl, tag, result, pool):
        _, tl_idx, gen_idx, p_idx = tag

        # Track run time
        elapsed = result.get('_worker_elapsed', 0)
        if gen_idx not in tl.gen_run_time:
            tl.gen_run_time[gen_idx] = 0.0
        tl.gen_run_time[gen_idx] += elapsed
        tl.total_run_time += elapsed

        # Track wall-clock start for diagnostics
        worker_start = result.get('_worker_start_time', 0)
        if tl.first_sim_start is None or worker_start < tl.first_sim_start:
            tl.first_sim_start = worker_start

        geno = tl.ponds[p_idx]
        result['genotype_obj'] = geno
        result['genotype'] = geno.to_dict()

        if result.get('budget_exceeded'):
            result['status'] = 'OVER-BUDGET'
            result['fitness'] = 0.0
        elif result.get('alive_count', 0) == 0:
            result['status'] = 'ALL-DEAD'
        else:
            result['status'] = 'OK'

        tl.gen_results.append(result)
        tl.memory.record(geno, result.get('fitness', 0))
        tl.csv_rows.append(_csv_row_data(tl.tl_idx, gen_idx, p_idx,
                                          result['status'], result, result['genotype']))

        tl.sim_pending -= 1
        if tl.sim_pending <= 0:
            self._on_all_sims_done(tl, pool)

    # ────────────────────────────────────────────────────────────
    # ALL SIMS DONE → START TOURNAMENTS
    # ────────────────────────────────────────────────────────────

    def _on_all_sims_done(self, tl, pool):
        """All sims for this generation are done. Start tournament selection."""
        gen = tl.gen
        is_last = (gen == POND_GENERATIONS - 1)

        # Sort results
        tl.gen_results.sort(key=lambda r: r.get('fitness', 0), reverse=True)

        # Log generation stats
        self._log_gen(tl, gen)

        if is_last:
            self._finish_timeline(tl)
            return

        if len(tl.gen_results) <= EA_ELITISM_COUNT:
            self._finish_timeline(tl)
            return

        # Start tournament selection
        n_children = POND_POPULATION - EA_ELITISM_COUNT
        mgr = TournamentMgr(
            tl.gen_results, n_children, EA_TOURNAMENT_K,
            tl.memory, pool, tl.tl_idx, gen, self.runtime, MAX_BUDGET)
        tl.tournament_mgr = mgr
        mgr.start()

        # Check if all tournaments resolved immediately (no verification needed)
        if mgr.all_resolved and mgr.all_children_ready:
            self._on_tournaments_done(tl, pool)

    # ────────────────────────────────────────────────────────────
    # HANDLE VER RESULT
    # ────────────────────────────────────────────────────────────

    def _handle_ver_result(self, tl, tag, result, pool):
        _, tl_idx, gen_idx, geno_key = tag

        # Track run time
        elapsed = result.get('_worker_elapsed', 0)
        if gen_idx not in tl.gen_run_time:
            tl.gen_run_time[gen_idx] = 0.0
        tl.gen_run_time[gen_idx] += elapsed
        tl.total_run_time += elapsed

        # Track wall-clock completion for diagnostics
        tl.last_ver_complete = _time.time()

        mgr = tl.tournament_mgr
        if mgr is None:
            return

        mgr.on_ver_result(geno_key, result)

        # Check if all tournaments resolved
        if mgr.all_resolved and mgr.all_children_ready:
            self._on_tournaments_done(tl, pool)

    # ────────────────────────────────────────────────────────────
    # TOURNAMENTS DONE → BUILD NEXT GENERATION
    # ────────────────────────────────────────────────────────────

    def _on_tournaments_done(self, tl, pool):
        """All tournaments resolved. Build next generation and submit."""
        mgr = tl.tournament_mgr
        gen = tl.gen

        # Log verification count
        print(f"\t  Extra Async Verifications: {mgr.total_ver_evals}")

        # Build next generation: elites + children
        sorted_results = tl.gen_results
        elite_genos = [r['genotype_obj'] for r in sorted_results[:EA_ELITISM_COUNT]]
        new_ponds = [copy.deepcopy(g) for g in elite_genos]

        for child in mgr.children:
            if child is not None:
                new_ponds.append(child)

        # Fill any remaining slots
        while len(new_ponds) < POND_POPULATION:
            new_ponds.append(copy.deepcopy(random.choice(elite_genos)))

        tl.ponds = new_ponds[:POND_POPULATION]
        tl.gen += 1
        tl.tournament_mgr = None

        # Submit next generation
        self._submit_gen_sims(tl, pool)

    # ────────────────────────────────────────────────────────────
    # FINISH TIMELINE
    # ────────────────────────────────────────────────────────────

    def _finish_timeline(self, tl):
        """Timeline complete — pick champion."""
        last_results = tl.gen_results
        champ = None
        if last_results:
            for r in last_results:
                if r.get('fitness', 0) > 0:
                    champ = r
                    break
            if champ is None:
                champ = last_results[0]
                champ['is_latest_dead'] = True

        if champ:
            champ.pop('genotype_obj', None)

        tl.champion = champ
        tl.finished = True

        tag = " [LATEST DEAD]" if (champ and champ.get('is_latest_dead')) else ""
        fit = champ['fitness'] if champ else 0
        alive = champ.get('alive_count', 0) if champ else 0
        init = champ.get('initial_count', 0) if champ else 0
        run_str = tl._fmt_run_time(tl.total_run_time)
        print(f"    [TL {tl.tl_idx + 1}] ✓ Finished ({run_str}) | "
              f"Fitness={fit:.4f} | Alive={alive}/{init}{tag}")

    # ────────────────────────────────────────────────────────────
    # LOGGING
    # ────────────────────────────────────────────────────────────

    def _log_gen(self, tl, gen):
        """Log a generation's results to console (mirrored to demo.txt via TeeLogger)."""
        sorted_results = tl.gen_results
        best_fit = sorted_results[0]['fitness'] if sorted_results else 0
        avg_fit = (sum(r.get('fitness', 0) for r in sorted_results) / len(sorted_results)
                   if sorted_results else 0)
        n_ok = sum(1 for r in sorted_results if r.get('status') == 'OK')
        n_dead = sum(1 for r in sorted_results if r.get('status') == 'ALL-DEAD')
        n_over = sum(1 for r in sorted_results if r.get('status') == 'OVER-BUDGET')
        n_gate = sum(1 for r in sorted_results if r.get('status') == 'GATEKEEPER')

        gen_run = tl.gen_run_time.get(gen, 0)
        total_run = tl.total_run_time

        gen_run_str = f"{gen_run:.1f}s"
        total_run_str = tl._fmt_run_time(total_run)

        print(f"    [TL {tl.tl_idx + 1}] Gen {gen + 1:>2}/{POND_GENERATIONS} | "
              f"Best: {best_fit:.4f} | Avg: {avg_fit:.4f} | OK: {n_ok:>2} | Dead: {n_dead:>2} | "
              f"Over$: {n_over:>2} | Reject: {n_gate:>2} | "
              f"{gen_run_str} | Total: {total_run_str}")

    # ────────────────────────────────────────────────────────────
    # DIAGNOSTICS
    # ────────────────────────────────────────────────────────────

    def _print_diagnostics(self, timelines, wall_start):
        print(f"\n  {'=' * 60}")
        print(f"  TIMELINE OVERLAP DIAGNOSTICS")
        print(f"  {'=' * 60}")
        for tl in timelines:
            first = tl.first_sim_start - wall_start if tl.first_sim_start else 0
            last = tl.last_ver_complete - wall_start if tl.last_ver_complete else 0
            run_str = tl._fmt_run_time(tl.total_run_time)
            print(f"    TL {tl.tl_idx + 1}: First Sim started @ {first:.1f}s  |  "
                  f"Last Ver completed @ {last:.1f}s  |  Run time: {run_str}")

        for i in range(len(timelines) - 1):
            a = timelines[i]
            b = timelines[i + 1]
            a_start = a.first_sim_start or 0
            a_end = a.last_ver_complete or 0
            b_start = b.first_sim_start or 0
            b_end = b.last_ver_complete or 0
            if a_start and b_start and a_end and b_end:
                overlap_start = max(a_start, b_start)
                overlap_end = min(a_end, b_end)
                if overlap_start < overlap_end:
                    dur = overlap_end - overlap_start
                    print(f"    ✓ TL {a.tl_idx + 1} and TL {b.tl_idx + 1} OVERLAP "
                          f"({overlap_start - wall_start:.1f}s - {overlap_end - wall_start:.1f}s, "
                          f"{dur:.1f}s)")
                else:
                    print(f"    ✗ TL {a.tl_idx + 1} and TL {b.tl_idx + 1}: No overlap")
