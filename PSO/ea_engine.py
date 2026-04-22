"""
EA engine — two evolutionary layers:

  season_ea   : end-of-season school competition and reproduction
                (evolves PSO hyperparameters and species composition of schools)

  outer_ea    : evolves the tank's environmental parameters to match a target
                population size and diversity
"""

import numpy as np
from typing import List, Dict, Tuple, Callable
from .fish import Fish
from .school import School
from .tank import Tank
from . import config


# ─── Season-end EA ────────────────────────────────────────────────────────────

def season_ea(schools: List[School], tank: Tank,
              num_species: int = config.NUM_SPECIES) -> List[School]:
    """
    End-of-season competition and reproduction.

    Schools are ranked by their accumulated seasonal_fitness.
    The bottom (1 - SEASON_SURVIVAL_FRACTION) are eliminated; survivors
    reproduce via crossover + mutation to fill the vacated slots.

    Returns the new list of alive schools (survivors + offspring).
    """
    alive = [s for s in schools if s.alive and s.size > 0]
    if not alive:
        return schools

    ranked = sorted(alive, key=lambda s: s.seasonal_fitness, reverse=True)

    n_keep = max(config.MIN_SCHOOLS_ALIVE,
                 round(len(ranked) * config.SEASON_SURVIVAL_FRACTION))
    n_keep = min(n_keep, len(ranked))

    survivors = ranked[:n_keep]
    n_new = len(ranked) - n_keep

    offspring: List[School] = []
    for _ in range(n_new):
        p1 = _tournament_select(survivors)
        p2 = _tournament_select(survivors)
        child_genes = _crossover_genes(p1.gene_vector(), p2.gene_vector(),
                                       config.SEASON_CROSSOVER_PROB)
        child_genes = _mutate_school_genes(child_genes)
        child_comp = _mutate_composition(dict(p1.species_composition), num_species)
        new_fish = _spawn_fish(child_comp, tank, child_genes)
        offspring.append(School.from_gene_vector(child_genes, new_fish, child_comp))

    for s in survivors:
        s.reset_season()

    return survivors + offspring


def _tournament_select(schools: List[School]) -> School:
    k = min(2, len(schools))
    candidates = [schools[i] for i in
                  np.random.choice(len(schools), size=k, replace=False)]
    return max(candidates, key=lambda s: s.seasonal_fitness)


def _crossover_genes(g1: List[float], g2: List[float],
                     prob: float) -> List[float]:
    if np.random.random() > prob:
        return list(g1)
    mask = np.random.randint(0, 2, size=len(g1)).astype(bool)
    return [g1[i] if mask[i] else g2[i] for i in range(len(g1))]


def _mutate_school_genes(genes: List[float]) -> List[float]:
    bounds = [config.W_BOUNDS, config.C1_BOUNDS,
              config.C2_BOUNDS, config.SENSORY_RADIUS_BOUNDS]
    out = []
    for val, (lo, hi) in zip(genes, bounds):
        if np.random.random() < config.SEASON_MUTATION_RATE:
            val += np.random.normal(0.0, config.SEASON_MUTATION_SCALE * (hi - lo))
        out.append(float(np.clip(val, lo, hi)))
    return out


def _mutate_composition(comp: Dict[int, int], num_species: int) -> Dict[int, int]:
    """Occasionally transfer one fish's species slot to keep diversity alive."""
    total = sum(comp.values())
    if total == 0:
        return {i: 1 for i in range(num_species)}

    if np.random.random() < 0.3 and num_species > 1:
        donors = [sp for sp, cnt in comp.items() if cnt > 0]
        if donors:
            sp_from = int(np.random.choice(donors))
            sp_to = int(np.random.randint(0, num_species))
            comp[sp_from] -= 1
            comp[sp_to] = comp.get(sp_to, 0) + 1

    return comp


def _spawn_fish(composition: Dict[int, int], tank: Tank,
                genes: List[float]) -> List[Fish]:
    """Spawn exactly FISH_PER_SCHOOL fresh fish, using composition as species ratios."""
    w, c1, c2, sr = genes

    total = sum(max(0, v) for v in composition.values())
    if total == 0:
        composition = {i: 1 for i in range(config.NUM_SPECIES)}
        total = config.NUM_SPECIES

    target = config.FISH_PER_SCHOOL
    items = [(sp, cnt) for sp, cnt in sorted(composition.items()) if cnt > 0]
    fish_list: List[Fish] = []
    remaining = target

    for i, (sp_id, cnt) in enumerate(items):
        n = remaining if i == len(items) - 1 else min(remaining,
            max(0, round(cnt / total * target)))
        remaining -= n
        for _ in range(n):
            x = np.random.uniform(20.0, tank.width - 20.0)
            y = np.random.uniform(20.0, tank.height - 20.0)
            fish_list.append(Fish(x, y, sp_id, -1, w, c1, c2, sr))

    if not fish_list:
        fish_list.append(
            Fish(tank.width / 2.0, tank.height / 2.0, 0, -1, w, c1, c2, sr))
    return fish_list


# ─── Outer EA ─────────────────────────────────────────────────────────────────

def outer_ea(target_population: int, target_diversity: float,
             eval_fn: Callable[[dict], Tuple[int, float]],
             verbose: bool = True) -> Tuple[dict, List[dict]]:
    """
    Evolve tank environmental parameters to match target_population and
    target_diversity.

    eval_fn(env_params) must return (final_population, final_diversity).

    Returns:
        best_params  — env_params dict that produced the closest match
        history      — list of per-generation statistics
    """
    pop = _init_env_pop(config.OUTER_POP_SIZE)
    best_params: dict = {}
    best_fitness: float = float('-inf')
    history: List[dict] = []

    for gen in range(config.OUTER_GENERATIONS):
        fitnesses: List[float] = []

        for individual in pop:
            final_pop, final_div = eval_fn(individual)
            f = _env_fitness(final_pop, final_div, target_population, target_diversity)
            fitnesses.append(f)

            if f > best_fitness:
                best_fitness = f
                best_params = dict(individual)

        record = {
            'generation': gen,
            'best_fitness': float(max(fitnesses)),
            'mean_fitness': float(np.mean(fitnesses)),
            'best_params': dict(pop[int(np.argmax(fitnesses))]),
        }
        history.append(record)

        if verbose:
            bp = record['best_params']
            print(f"  Gen {gen:3d} | fitness best={record['best_fitness']:+.4f} "
                  f"mean={record['mean_fitness']:+.4f} | "
                  f"T={bp['temperature']:.1f}°C  O₂={bp['oxygen_level']:.2f}  "
                  f"pH={bp['ph_level']:.2f}  food={bp['food_density']:.2f}")

        pop = _evolve_env_pop(pop, fitnesses)

    return best_params, history


def _init_env_pop(n: int) -> List[dict]:
    return [{
        'food_density': float(np.random.uniform(*config.ENV_FOOD_DENSITY)),
        'temperature':  float(np.random.uniform(*config.ENV_TEMPERATURE)),
        'oxygen_level': float(np.random.uniform(*config.ENV_OXYGEN)),
        'ph_level':     float(np.random.uniform(*config.ENV_PH)),
    } for _ in range(n)]


def _env_fitness(final_pop: int, final_div: float,
                 target_pop: int, target_div: float) -> float:
    pop_err = abs(final_pop - target_pop) / max(target_pop, 1)
    div_err = abs(final_div - target_div)
    return float(-(0.6 * pop_err + 0.4 * div_err))


def _env_tournament(pop: List[dict], fitnesses: List[float]) -> dict:
    k = min(config.OUTER_TOURNAMENT_SIZE, len(pop))
    idxs = np.random.choice(len(pop), size=k, replace=False)
    best_idx = int(max(idxs, key=lambda i: fitnesses[i]))
    return dict(pop[best_idx])


def _crossover_env(p1: dict, p2: dict) -> dict:
    if np.random.random() > config.OUTER_CROSSOVER_PROB:
        return dict(p1)
    return {k: (p1[k] if np.random.random() < 0.5 else p2[k]) for k in p1}


def _mutate_env(individual: dict) -> dict:
    _bounds = {
        'food_density': config.ENV_FOOD_DENSITY,
        'temperature':  config.ENV_TEMPERATURE,
        'oxygen_level': config.ENV_OXYGEN,
        'ph_level':     config.ENV_PH,
    }
    out = {}
    for key, val in individual.items():
        if key in _bounds and np.random.random() < config.OUTER_MUTATION_RATE:
            lo, hi = _bounds[key]
            val += np.random.normal(0.0, config.OUTER_MUTATION_SCALE * (hi - lo))
            val = float(np.clip(val, lo, hi))
        out[key] = val
    return out


def _evolve_env_pop(pop: List[dict], fitnesses: List[float]) -> List[dict]:
    new_pop: List[dict] = []

    # Elitism — always keep the top OUTER_ELITISM individuals
    elite_idxs = np.argsort(fitnesses)[::-1][:config.OUTER_ELITISM]
    for i in elite_idxs:
        new_pop.append(dict(pop[i]))

    while len(new_pop) < len(pop):
        p1 = _env_tournament(pop, fitnesses)
        p2 = _env_tournament(pop, fitnesses)
        child = _crossover_env(p1, p2)
        child = _mutate_env(child)
        new_pop.append(child)

    return new_pop
