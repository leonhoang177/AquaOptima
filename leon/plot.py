#!/usr/bin/env python3
"""
plot.py — Visualize EA evolution from results.csv

Generates a multi-panel figure showing how Fitness, Survival Rate,
Healthiness, and Cost evolve across generations for each simulation.

Run:  python plot.py
Input:  results.csv  (produced by simulation.py)
Output: plots displayed on screen + saved as evolution_plots.png
"""

import sys
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════

CSV_PATH = 'results.csv'
OUTPUT_PATH = 'evolution_plots.png'
DPI = 150
FIGSIZE = (18, 22)

# Color palette for simulations (up to 10)
SIM_COLORS = [
    '#5ec4ff', '#ff6b6b', '#4cff8e', '#ffc04c', '#cc66ff',
    '#ff66b2', '#66ffcc', '#ffcc66', '#66b2ff', '#b2ff66',
]

# ════════════════════════════════════════════════════════════════
# LOAD DATA
# ════════════════════════════════════════════════════════════════

def load_data(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        print(f"  ❌ File not found: {path}")
        print(f"     Run simulation.py first to generate it.")
        sys.exit(1)

    df = pd.read_csv(path)
    # Ensure numeric columns
    for col in ['fitness', 'survival_rate', 'healthiness', 'cost', 'efficiency']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['survival_pct'] = df['survival_rate'] * 100
    print(f"  ✅ Loaded {path}: {len(df)} rows, "
          f"{df['simulation'].nunique()} simulations, "
          f"{df['generation'].max()} max generations")
    return df


# ════════════════════════════════════════════════════════════════
# PLOT FUNCTIONS
# ════════════════════════════════════════════════════════════════

def plot_metric_per_generation(ax, df, metric_col, ylabel, title,
                                fmt_func=None, show_all_ponds=True,
                                y_range=None):
    """
    Plot one metric across generations.
    Shows: individual pond dots, generation mean line, generation best line.
    One color per simulation.
    """
    sims = sorted(df['simulation'].unique())

    for sim in sims:
        sdf = df[df['simulation'] == sim]
        color = SIM_COLORS[(sim - 1) % len(SIM_COLORS)]
        label_prefix = f"Sim {sim}"

        gens = sorted(sdf['generation'].unique())
        means = []
        bests = []
        gen_list = []

        for g in gens:
            gdf = sdf[sdf['generation'] == g]
            vals = gdf[metric_col].values

            if show_all_ponds:
                jitter = np.random.uniform(-0.15, 0.15, size=len(vals))
                ax.scatter(g + jitter, vals, color=color, alpha=0.15, s=12,
                           edgecolors='none', zorder=2)

            means.append(vals.mean())
            bests.append(vals.max())
            gen_list.append(g)

        ax.plot(gen_list, means, color=color, linewidth=1.8, alpha=0.8,
                marker='o', markersize=4, label=f"{label_prefix} Mean", zorder=3)
        ax.plot(gen_list, bests, color=color, linewidth=1.2, alpha=0.5,
                linestyle='--', marker='^', markersize=3,
                label=f"{label_prefix} Best", zorder=3)

    ax.set_xlabel('Generation', fontsize=11, fontweight='bold')
    ax.set_ylabel(ylabel, fontsize=11, fontweight='bold')
    ax.set_title(title, fontsize=13, fontweight='bold', pad=10)
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))

    if y_range is not None:
        ax.set_ylim(y_range)

    if fmt_func:
        ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_func))

    ax.legend(fontsize=7, loc='best', ncol=2, framealpha=0.7)


def plot_status_breakdown(ax, df):
    """Stacked bar chart showing pond status distribution per generation."""
    status_order = ['OK', 'ALL-DEAD', 'OVER-BUDGET', 'GATEKEEPER']
    status_colors = {
        'OK': '#4cff8e',
        'ALL-DEAD': '#ff4c6a',
        'OVER-BUDGET': '#ffc04c',
        'GATEKEEPER': '#888888',
    }

    gens = sorted(df['generation'].unique())
    bottom = np.zeros(len(gens))

    for status in status_order:
        counts = []
        for g in gens:
            gdf = df[df['generation'] == g]
            counts.append(len(gdf[gdf['status'] == status]))
        counts = np.array(counts, dtype=float)
        color = status_colors.get(status, '#aaaaaa')
        ax.bar(gens, counts, bottom=bottom, color=color, label=status,
               alpha=0.8, edgecolor='white', linewidth=0.3)
        bottom += counts

    ax.set_xlabel('Generation', fontsize=11, fontweight='bold')
    ax.set_ylabel('Pond Count', fontsize=11, fontweight='bold')
    ax.set_title('Pond Status Distribution per Generation (All Simulations)',
                 fontsize=13, fontweight='bold', pad=10)
    ax.grid(True, alpha=0.2, linestyle='--', axis='y')
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(fontsize=9, loc='upper right', framealpha=0.7)


def plot_cost_vs_fitness(ax, df):
    """Scatter plot of cost vs fitness, colored by simulation."""
    sims = sorted(df['simulation'].unique())
    for sim in sims:
        sdf = df[(df['simulation'] == sim) & (df['fitness'] > 0)]
        color = SIM_COLORS[(sim - 1) % len(SIM_COLORS)]
        ax.scatter(sdf['cost'], sdf['fitness'], color=color, alpha=0.4,
                   s=20, edgecolors='none', label=f"Sim {sim}")

    ax.set_xlabel('Cost ($)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Fitness', fontsize=11, fontweight='bold')
    ax.set_title('Cost vs Fitness (Successful Ponds Only)',
                 fontsize=13, fontweight='bold', pad=10)
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.legend(fontsize=8, loc='best', framealpha=0.7)


def plot_survival_vs_healthiness(ax, df):
    """Scatter of survival rate vs healthiness, sized by fitness."""
    ok = df[(df['fitness'] > 0)].copy()
    if ok.empty:
        ax.text(0.5, 0.5, 'No successful ponds', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, color='#888')
        ax.set_title('Survival vs Healthiness', fontsize=13, fontweight='bold', pad=10)
        return

    sims = sorted(ok['simulation'].unique())
    for sim in sims:
        sdf = ok[ok['simulation'] == sim]
        color = SIM_COLORS[(sim - 1) % len(SIM_COLORS)]
        sizes = sdf['fitness'] * 150 + 5
        ax.scatter(sdf['survival_pct'], sdf['healthiness'], color=color,
                   alpha=0.5, s=sizes, edgecolors='white', linewidth=0.3,
                   label=f"Sim {sim}")

    ax.set_xlabel('Survival Rate (%)', fontsize=11, fontweight='bold')
    ax.set_ylabel('Healthiness', fontsize=11, fontweight='bold')
    ax.set_title('Survival vs Healthiness (size = fitness)',
                 fontsize=13, fontweight='bold', pad=10)
    ax.grid(True, alpha=0.2, linestyle='--')
    ax.legend(fontsize=8, loc='best', framealpha=0.7)


def plot_best_per_simulation(ax, df):
    """Bar chart comparing the best fitness from each simulation."""
    sims = sorted(df['simulation'].unique())
    best_fitness = []
    best_survival = []
    best_healthiness = []
    labels = []

    for sim in sims:
        sdf = df[df['simulation'] == sim]
        best_row = sdf.loc[sdf['fitness'].idxmax()]
        best_fitness.append(best_row['fitness'])
        best_survival.append(best_row['survival_pct'])
        best_healthiness.append(best_row['healthiness'])
        labels.append(f"Sim {sim}")

    x = np.arange(len(sims))
    width = 0.25

    b1 = ax.bar(x - width, best_fitness, width, label='Fitness',
                color='#5ec4ff', alpha=0.85, edgecolor='white', linewidth=0.5)
    b2 = ax.bar(x, [s / 100 for s in best_survival], width, label='Survival (norm)',
                color='#4cff8e', alpha=0.85, edgecolor='white', linewidth=0.5)
    b3 = ax.bar(x + width, best_healthiness, width, label='Healthiness',
                color='#ffc04c', alpha=0.85, edgecolor='white', linewidth=0.5)

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel('Score (0-1)', fontsize=11, fontweight='bold')
    ax.set_title('Best Pond per Simulation — Fitness / Survival / Healthiness',
                 fontsize=13, fontweight='bold', pad=10)
    ax.grid(True, alpha=0.2, linestyle='--', axis='y')
    ax.legend(fontsize=9, loc='upper right', framealpha=0.7)
    ax.set_ylim(0, 1.05)

    # Value labels on bars
    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.01,
                        f'{h:.2f}', ha='center', va='bottom', fontsize=7)


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'═' * 60}")
    print(f"  📊 Largemouth Bass Aquaculture — Evolution Plotter")
    print(f"{'═' * 60}")

    df = load_data(CSV_PATH)

    # Set dark style
    plt.style.use('dark_background')
    plt.rcParams.update({
        'figure.facecolor': '#0a1628',
        'axes.facecolor': '#111e30',
        'axes.edgecolor': '#1e3a5f',
        'grid.color': '#1e3a5f',
        'text.color': '#e0e8f0',
        'axes.labelcolor': '#e0e8f0',
        'xtick.color': '#8899aa',
        'ytick.color': '#8899aa',
    })

    fig, axes = plt.subplots(4, 2, figsize=FIGSIZE)
    fig.suptitle('Largemouth Bass Aquaculture — EA Evolution Analysis',
                 fontsize=16, fontweight='bold', color='#5ec4ff', y=0.98)

    # Row 1: Fitness & Survival Rate across generations
    plot_metric_per_generation(
        axes[0, 0], df, 'fitness', 'Fitness', 'Fitness across Generations',
        fmt_func=lambda x, _: f'{x:.2f}', y_range=(-0.02, 1.02))

    plot_metric_per_generation(
        axes[0, 1], df, 'survival_pct', 'Survival Rate (%)',
        'Survival Rate across Generations',
        fmt_func=lambda x, _: f'{x:05.2f}%', y_range=(-2, 102))

    # Row 2: Healthiness & Cost across generations
    plot_metric_per_generation(
        axes[1, 0], df, 'healthiness', 'Healthiness', 'Healthiness across Generations',
        fmt_func=lambda x, _: f'{x:.2f}', y_range=(-0.02, 1.02))

    plot_metric_per_generation(
        axes[1, 1], df, 'cost', 'Cost ($)', 'Cost across Generations',
        fmt_func=lambda x, _: f'${x:,.0f}', show_all_ponds=True)

    # Row 3: Status breakdown & Cost vs Fitness scatter
    plot_status_breakdown(axes[2, 0], df)
    plot_cost_vs_fitness(axes[2, 1], df)

    # Row 4: Survival vs Healthiness & Best per simulation
    plot_survival_vs_healthiness(axes[3, 0], df)
    plot_best_per_simulation(axes[3, 1], df)

    plt.tight_layout(rect=[0, 0, 1, 0.96])
    plt.savefig(OUTPUT_PATH, dpi=DPI, facecolor=fig.get_facecolor(),
                edgecolor='none', bbox_inches='tight')
    print(f"\n  💾 Saved {OUTPUT_PATH}")
    print(f"  🖥  Displaying plots...")
    plt.show()


if __name__ == '__main__':
    main()