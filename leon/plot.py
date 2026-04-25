#!/usr/bin/env python3
"""
plot.py -- Visualize EA evolution from results.csv

Reads results.csv (produced by simulation.py) and generates 8 separate
plot files in./plots/, each focusing on one aspect of the evolution.

Run:    python plot.py
Input:  results.csv
Output: plots/plot_1_fitness.png
        plots/plot_2_survival.png
        plots/plot_3_healthiness.png
        plots/plot_4_cost.png
        plots/plot_5_status.png
        plots/plot_6_cost_vs_fitness.png
        plots/plot_7_survival_vs_healthiness.png
        plots/plot_8_champion_comparison.png
"""

import sys
import os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
from pathlib import Path

# ════════════════════════════════════════════════════════════════
# CONFIGURATION
# ════════════════════════════════════════════════════════════════

CSV_PATH = 'results.csv'
OUTPUT_DIR = './plots'
DPI = 180
SINGLE_FIG_SIZE = (12, 7)

# Academic-friendly colors for timelines (distinct, colorblind-safe-ish)
TL_COLORS = [
    '#1f77b4',  # blue
    '#d62728',  # red
    '#2ca02c',  # green
    '#ff7f0e',  # orange
    '#9467bd',  # purple
    '#8c564b',  # brown
    '#e377c2',  # pink
    '#7f7f7f',  # gray
    '#bcbd22',  # olive
    '#17becf',  # cyan
]

# Status colors (for white background)
STATUS_COLORS = {
    'OK':          '#2ca02c',
    'ALL-DEAD':    '#d62728',
    'OVER-BUDGET': '#ff7f0e',
    'GATEKEEPER':  '#7f7f7f',
}


# ════════════════════════════════════════════════════════════════
# WHITE ACADEMIC THEME
# ════════════════════════════════════════════════════════════════

def _apply_theme():
    plt.rcParams.update({
        'figure.facecolor': 'white',
        'axes.facecolor': 'white',
        'axes.edgecolor': '#333333',
        'axes.labelcolor': '#222222',
        'axes.grid': True,
        'grid.color': '#dddddd',
        'grid.linestyle': '--',
        'grid.alpha': 0.7,
        'text.color': '#222222',
        'xtick.color': '#333333',
        'ytick.color': '#333333',
        'legend.facecolor': 'white',
        'legend.edgecolor': '#cccccc',
        'legend.framealpha': 0.9,
        'font.size': 11,
        'axes.titlesize': 14,
        'axes.labelsize': 12,
    })


# ════════════════════════════════════════════════════════════════
# LOAD DATA
# ════════════════════════════════════════════════════════════════

def load_data(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        print(f"  ERROR: File not found: {path}")
        print(f"         Run simulation.py first to generate it.")
        sys.exit(1)

    df = pd.read_csv(path)
    for col in ['fitness', 'survival_rate', 'healthiness', 'cost', 'efficiency']:
        df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    df['survival_pct'] = df['survival_rate'] * 100
    print(f"  Loaded {path}: {len(df)} rows, "
          f"{df['timeline'].nunique()} timelines, "
          f"{df['generation'].max()} max generations")
    return df


# ════════════════════════════════════════════════════════════════
# SAVE HELPER
# ════════════════════════════════════════════════════════════════

def _save(fig, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = Path(OUTPUT_DIR) / filename
    fig.savefig(str(path), dpi=DPI, facecolor='white',
                edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    print(f"    Saved {path}")


# ════════════════════════════════════════════════════════════════
# SHARED METRIC PLOTTER
# ════════════════════════════════════════════════════════════════

def _plot_metric(ax, df, col, ylabel, title, fmt=None, ylim=None):
    for tl in sorted(df['timeline'].unique()):
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]

        gens = sorted(sdf['generation'].unique())
        means, bests, gl = [], [], []
        for g in gens:
            vals = sdf[sdf['generation'] == g][col].values
            jitter = np.random.uniform(-0.18, 0.18, size=len(vals))
            ax.scatter(g + jitter, vals, color=color, alpha=0.15, s=14,
                       edgecolors='none', zorder=2)
            means.append(vals.mean())
            bests.append(vals.max())
            gl.append(g)

        ax.plot(gl, means, color=color, linewidth=2, alpha=0.9,
                marker='o', markersize=4, label=f"TL {tl} Mean", zorder=3)
        ax.plot(gl, bests, color=color, linewidth=1.2, alpha=0.5,
                linestyle='--', marker='^', markersize=3,
                label=f"TL {tl} Best", zorder=3)

    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    if ylim: ax.set_ylim(ylim)
    if fmt: ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt))
    ax.legend(fontsize=7, loc='best', ncol=2)


# ════════════════════════════════════════════════════════════════
# PLOT 1: FITNESS
# ════════════════════════════════════════════════════════════════

def plot_fitness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric(ax, df, 'fitness', 'Fitness',
                 'Fitness across Generations',
                 fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout()
    _save(fig, 'plot_1_fitness.png')


# ════════════════════════════════════════════════════════════════
# PLOT 2: SURVIVAL
# ════════════════════════════════════════════════════════════════

def plot_survival(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric(ax, df, 'survival_pct', 'Survival Rate (%)',
                 'Survival Rate across Generations',
                 fmt=lambda x, _: f'{x:.1f}%', ylim=(-2, 102))
    fig.tight_layout()
    _save(fig, 'plot_2_survival.png')


# ════════════════════════════════════════════════════════════════
# PLOT 3: HEALTHINESS
# ════════════════════════════════════════════════════════════════

def plot_healthiness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric(ax, df, 'healthiness', 'Healthiness',
                 'Healthiness across Generations',
                 fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout()
    _save(fig, 'plot_3_healthiness.png')


# ════════════════════════════════════════════════════════════════
# PLOT 4: COST
# ════════════════════════════════════════════════════════════════

def plot_cost(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric(ax, df, 'cost', 'Cost ($)',
                 'Cost across Generations',
                 fmt=lambda x, _: f'${x:,.0f}', ylim=None)
    fig.tight_layout()
    _save(fig, 'plot_4_cost.png')


# ════════════════════════════════════════════════════════════════
# PLOT 5: STATUS BREAKDOWN
# ════════════════════════════════════════════════════════════════

def plot_status(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)

    status_order = ['OK', 'ALL-DEAD', 'OVER-BUDGET', 'GATEKEEPER']
    gens = sorted(df['generation'].unique())
    bottom = np.zeros(len(gens))

    for status in status_order:
        counts = np.array([len(df[(df['generation'] == g) & (df['status'] == status)])
                           for g in gens], dtype=float)
        ax.bar(gens, counts, bottom=bottom, color=STATUS_COLORS.get(status, '#aaa'),
               label=status, alpha=0.85, edgecolor='white', linewidth=0.5)
        bottom += counts

    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel('Pond Count', fontweight='bold')
    ax.set_title('Pond Status Distribution per Generation (All Timelines)',
                 fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(fontsize=10, loc='upper right')

    fig.tight_layout()
    _save(fig, 'plot_5_status.png')


# ════════════════════════════════════════════════════════════════
# PLOT 6: COST VS FITNESS
# ════════════════════════════════════════════════════════════════

def plot_cost_vs_fitness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)

    for tl in sorted(df['timeline'].unique()):
        sdf = df[(df['timeline'] == tl) & (df['fitness'] > 0)]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        ax.scatter(sdf['cost'], sdf['fitness'], color=color, alpha=0.5,
                   s=30, edgecolors='white', linewidth=0.3, label=f"Timeline {tl}")

    ax.set_xlabel('Cost ($)', fontweight='bold')
    ax.set_ylabel('Fitness', fontweight='bold')
    ax.set_title('Cost vs Fitness (Successful Ponds Only)',
                 fontweight='bold', pad=12)
    ax.legend(fontsize=9, loc='best')

    fig.tight_layout()
    _save(fig, 'plot_6_cost_vs_fitness.png')


# ════════════════════════════════════════════════════════════════
# PLOT 7: SURVIVAL VS HEALTHINESS
# ════════════════════════════════════════════════════════════════

def plot_survival_vs_healthiness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)

    ok = df[df['fitness'] > 0].copy()
    if ok.empty:
        ax.text(0.5, 0.5, 'No successful ponds to display', ha='center', va='center',
                transform=ax.transAxes, fontsize=14, color='#888')
        ax.set_title('Survival vs Healthiness', fontweight='bold', pad=12)
        fig.tight_layout()
        _save(fig, 'plot_7_survival_vs_healthiness.png')
        return

    for tl in sorted(ok['timeline'].unique()):
        sdf = ok[ok['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        sizes = sdf['fitness'] * 200 + 10
        ax.scatter(sdf['survival_pct'], sdf['healthiness'], color=color,
                   alpha=0.55, s=sizes, edgecolors='#333333', linewidth=0.3,
                   label=f"Timeline {tl}")

    ax.set_xlabel('Survival Rate (%)', fontweight='bold')
    ax.set_ylabel('Healthiness', fontweight='bold')
    ax.set_title('Survival vs Healthiness (bubble size = fitness)',
                 fontweight='bold', pad=12)
    ax.legend(fontsize=9, loc='best')

    fig.tight_layout()
    _save(fig, 'plot_7_survival_vs_healthiness.png')


# ════════════════════════════════════════════════════════════════
# PLOT 8: CHAMPION COMPARISON
# ════════════════════════════════════════════════════════════════

def plot_champion_comparison(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)

    timelines = sorted(df['timeline'].unique())
    best_fit, best_surv, best_hlth, labels = [], [], [], []

    for tl in timelines:
        sdf = df[df['timeline'] == tl]
        row = sdf.loc[sdf['fitness'].idxmax()]
        best_fit.append(row['fitness'])
        best_surv.append(row['survival_pct'] / 100)
        best_hlth.append(row['healthiness'])
        labels.append(f"TL {tl}")

    x = np.arange(len(timelines))
    w = 0.22

    b1 = ax.bar(x - w, best_fit, w, label='Fitness', color='#1f77b4', alpha=0.9,
                edgecolor='white', linewidth=0.5)
    b2 = ax.bar(x, best_surv, w, label='Survival (norm)', color='#2ca02c', alpha=0.9,
                edgecolor='white', linewidth=0.5)
    b3 = ax.bar(x + w, best_hlth, w, label='Healthiness', color='#ff7f0e', alpha=0.9,
                edgecolor='white', linewidth=0.5)

    for bars in [b1, b2, b3]:
        for bar in bars:
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width() / 2, h + 0.012,
                        f'{h:.3f}', ha='center', va='bottom', fontsize=7, color='#333')

    best_tl_idx = int(np.argmax(best_fit))
    ax.annotate('BEST', xy=(best_tl_idx - w, best_fit[best_tl_idx]),
                xytext=(best_tl_idx - w, best_fit[best_tl_idx] + 0.08),
                ha='center', fontsize=10, fontweight='bold', color='#d62728',
                arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.5))

    ax.set_xticks(x)
    ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel('Score (0 - 1)', fontweight='bold')
    ax.set_title('Best Pond per Timeline -- Fitness / Survival / Healthiness',
                 fontweight='bold', pad=12)
    ax.legend(fontsize=10, loc='upper right')
    ax.set_ylim(0, 1.15)

    fig.tight_layout()
    _save(fig, 'plot_8_champion_comparison.png')


# ════════════════════════════════════════════════════════════════
# MAIN
# ════════════════════════════════════════════════════════════════

def main():
    print(f"\n{'=' * 60}")
    print(f"  Largemouth Bass Aquaculture -- Evolution Plotter")
    print(f"{'=' * 60}")

    _apply_theme()
    df = load_data(CSV_PATH)

    print(f"\n  Generating plots into {OUTPUT_DIR}/...")

    plot_fitness(df)
    plot_survival(df)
    plot_healthiness(df)
    plot_cost(df)
    plot_status(df)
    plot_cost_vs_fitness(df)
    plot_survival_vs_healthiness(df)
    plot_champion_comparison(df)

    print(f"\n  All 8 plots saved to {OUTPUT_DIR}/")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()