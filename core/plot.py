#!/usr/bin/env python3
"""
plot.py -- Visualize EA evolution from results.csv
"""

import sys, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
from pathlib import Path

from constants import RESULTS_CSV_PATH, PLOTS_DIR, MAX_BUDGET

CSV_PATH = RESULTS_CSV_PATH
OUTPUT_DIR = PLOTS_DIR

DPI = 180
SINGLE_FIG_SIZE = (12, 7)

TL_COLORS = [
    '#1f77b4', '#d62728', '#2ca02c', '#ff7f0e', '#9467bd',
    '#8c564b', '#e377c2', '#7f7f7f', '#bcbd22', '#17becf',
]

STATUS_COLORS = {
    'OK': '#2ca02c', 'ALL-DEAD': '#d62728',
    'OVER-BUDGET': '#ff7f0e', 'GATEKEEPER': '#7f7f7f',
}

STATUS_LABELS = {
    'OK': 'OK', 'ALL-DEAD': 'All Dead',
    'OVER-BUDGET': 'Over Budget', 'GATEKEEPER': 'Reject',
}


def _apply_theme():
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'axes.edgecolor': '#333333', 'axes.labelcolor': '#222222',
        'axes.grid': True, 'grid.color': '#dddddd', 'grid.linestyle': '--', 'grid.alpha': 0.7,
        'text.color': '#222222', 'xtick.color': '#333333', 'ytick.color': '#333333',
        'legend.facecolor': 'white', 'legend.edgecolor': '#cccccc', 'legend.framealpha': 0.9,
        'font.size': 11, 'axes.titlesize': 14, 'axes.labelsize': 12,
    })


def load_data(path: str) -> pd.DataFrame:
    if not Path(path).exists():
        print(f"  ERROR: File not found: {path}")
        sys.exit(1)
    df = pd.read_csv(path)
    for col in ['fitness', 'survival_rate', 'healthiness', 'cost', 'saving', 'yield']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    if 'survival_rate' in df.columns:
        df['survival_pct'] = df['survival_rate'] * 100
    if 'fish_count' in df.columns:
        df['fish_count'] = pd.to_numeric(df['fish_count'], errors='coerce').fillna(0).astype(int)
    if 'saving' in df.columns:
        df['saving_rate'] = df['saving'] / MAX_BUDGET
    print(f"  Loaded {path}: {len(df)} rows, "
          f"{df['timeline'].nunique()} timelines, "
          f"{df['generation'].max()} max generations")
    return df


def _save(fig, filename):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = Path(OUTPUT_DIR) / filename
    fig.savefig(str(path), dpi=DPI, facecolor='white', edgecolor='none', bbox_inches='tight')
    plt.close(fig)
    print(f"    Saved {path}")


# ════════════════════════════════════════════════════════════════
# METRIC VS GENERATION
# ════════════════════════════════════════════════════════════════

def _plot_metric_vs_gen(ax, df, col, ylabel, title, fmt=None, ylim=None):
    for tl in sorted(df['timeline'].unique()):
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        gens = sorted(sdf['generation'].unique())
        means, bests, gl = [], [], []
        for g in gens:
            vals = sdf[sdf['generation'] == g][col].values
            jitter = np.random.uniform(-0.18, 0.18, size=len(vals))
            ax.scatter(g + jitter, vals, color=color, alpha=0.12, s=10, edgecolors='none', zorder=2)
            means.append(vals.mean()); bests.append(vals.max()); gl.append(g)
        ax.plot(gl, means, color=color, linewidth=2, alpha=0.9, marker='o', markersize=4,
                label=f"TL {tl} Mean", zorder=3)
        ax.plot(gl, bests, color=color, linewidth=1.2, alpha=0.5, linestyle='--', marker='^',
                markersize=3, label=f"TL {tl} Best", zorder=3)
    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    if ylim: ax.set_ylim(ylim)
    if fmt: ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt))
    ax.legend(fontsize=7, loc='best', ncol=2)


# ════════════════════════════════════════════════════════════════
# HEATMAP PAIR PLOT
# ════════════════════════════════════════════════════════════════

def _plot_pair_fitness(df, col_x, col_y, xlabel, ylabel, title, filename):
    """Scatter plot of two factors, colored by fitness."""
    ok = df[df['fitness'] > 0].copy()
    if ok.empty or len(ok) < 3:
        print(f"    Skipped {filename} (not enough data)")
        return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)

    x = ok[col_x].values
    y = ok[col_y].values
    c = ok['fitness'].values

    sc = ax.scatter(x, y, c=c, cmap='RdYlGn', s=30, alpha=0.7,
                    edgecolors='#333333', linewidth=0.3, zorder=2)

    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label('Fitness', fontweight='bold')

    ax.set_xlabel(xlabel, fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=12)

    fig.tight_layout(); _save(fig, filename)


# ════════════════════════════════════════════════════════════════
# INDIVIDUAL PLOTS
# ════════════════════════════════════════════════════════════════

def plot_fitness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'fitness', 'Fitness', 'Fitness vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(); _save(fig, 'plot_01_fitness_vs_gen.png')

def plot_yield(df):
    if 'yield' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'yield', 'Yield', 'Yield vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(); _save(fig, 'plot_02_yield_vs_gen.png')

def plot_saving(df):
    if 'saving' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'saving', 'Saving ($)', 'Saving vs Generation',
                        fmt=lambda x, _: f'${x:,.0f}')
    fig.tight_layout(); _save(fig, 'plot_03_saving_vs_gen.png')

def plot_healthiness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'healthiness', 'Healthiness', 'Healthiness vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(); _save(fig, 'plot_04_healthiness_vs_gen.png')

def plot_yield_vs_saving(df):
    _plot_pair_fitness(df, 'yield', 'saving', 'Yield', 'Saving ($)',
                       'Yield vs Saving (colored by Fitness)', 'plot_05_yield_vs_saving.png')

def plot_yield_vs_healthiness(df):
    _plot_pair_fitness(df, 'yield', 'healthiness', 'Yield', 'Healthiness',
                       'Yield vs Healthiness (colored by Fitness)', 'plot_06_yield_vs_healthiness.png')

def plot_saving_vs_healthiness(df):
    _plot_pair_fitness(df, 'saving', 'healthiness', 'Saving ($)', 'Healthiness',
                       'Saving vs Healthiness (colored by Fitness)', 'plot_07_saving_vs_healthiness.png')

def plot_fitness_vs_saving(df):
    _plot_pair_fitness(df, 'fitness', 'saving', 'Fitness', 'Saving ($)',
                       'Fitness vs Saving (colored by Fitness)', 'plot_08_fitness_vs_saving.png')

def plot_fitness_vs_yield(df):
    _plot_pair_fitness(df, 'fitness', 'yield', 'Fitness', 'Yield',
                       'Fitness vs Yield (colored by Fitness)', 'plot_09_fitness_vs_yield.png')

def plot_fitness_vs_healthiness(df):
    _plot_pair_fitness(df, 'fitness', 'healthiness', 'Fitness', 'Healthiness',
                       'Fitness vs Healthiness (colored by Fitness)', 'plot_10_fitness_vs_healthiness.png')
    
def plot_fish_count(df):
    if 'fish_count' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'fish_count', 'Fish Count',
                        'Initial Fish Count vs Generation', ylim=(0, 110))
    fig.tight_layout(); _save(fig, 'plot_11_fish_count_vs_gen.png')

def plot_status(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    status_order = ['OK', 'ALL-DEAD', 'OVER-BUDGET', 'GATEKEEPER']
    gens = sorted(df['generation'].unique())
    bottom = np.zeros(len(gens))
    for status in status_order:
        counts = np.array([len(df[(df['generation'] == g) & (df['status'] == status)])
                           for g in gens], dtype=float)
        label = STATUS_LABELS.get(status, status)
        ax.bar(gens, counts, bottom=bottom, color=STATUS_COLORS.get(status, '#aaa'),
               label=label, alpha=0.85, edgecolor='white', linewidth=0.5)
        bottom += counts
    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel('Pond Count', fontweight='bold')
    ax.set_title('Pond Status Distribution per Generation', fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.legend(fontsize=10, loc='upper right')
    fig.tight_layout(); _save(fig, 'plot_12_status.png')

def plot_champion_comparison(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    timelines = sorted(df['timeline'].unique())
    best_fit, best_yld, best_hlth, best_sav_rate, labels = [], [], [], [], []
    for tl in timelines:
        sdf = df[df['timeline'] == tl]
        last_gen = sdf['generation'].max()
        last_df = sdf[sdf['generation'] == last_gen]
        row = last_df.loc[last_df['fitness'].idxmax()]
        best_fit.append(row['fitness'])
        best_yld.append(row.get('yield', 0))
        best_hlth.append(row['healthiness'])
        # Saving rate = saving / budget (0-1 scale, matches fitness formula)
        sav = row.get('saving', 0)
        best_sav_rate.append(sav / MAX_BUDGET if MAX_BUDGET > 0 else 0)
        labels.append(f"TL {tl}")
    x = np.arange(len(timelines)); w = 0.18
    b1 = ax.bar(x - 1.5*w, best_fit, w, label='Fitness', color='#1f77b4', alpha=0.9, edgecolor='white')
    b2 = ax.bar(x - 0.5*w, best_yld, w, label='Yield', color='#2ca02c', alpha=0.9, edgecolor='white')
    b3 = ax.bar(x + 0.5*w, best_hlth, w, label='Healthiness', color='#ff7f0e', alpha=0.9, edgecolor='white')
    b4 = ax.bar(x + 1.5*w, best_sav_rate, w, label='Saving Rate', color='#9467bd', alpha=0.9, edgecolor='white')
    for bars in [b1, b2, b3, b4]:
        for bar in bars:
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.012, f'{h:.3f}',
                        ha='center', va='bottom', fontsize=6, color='#333')
    best_tl_idx = int(np.argmax(best_fit))
    ax.annotate('BEST', xy=(best_tl_idx - 1.5*w, best_fit[best_tl_idx]),
                xytext=(best_tl_idx - 1.5*w, best_fit[best_tl_idx] + 0.08),
                ha='center', fontsize=10, fontweight='bold', color='#d62728',
                arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.5))
    ax.set_xticks(x); ax.set_xticklabels(labels, fontsize=10)
    ax.set_ylabel('Score (0 - 1)', fontweight='bold')
    ax.set_title('Converged Champions Comparison', fontweight='bold', pad=12)
    ax.legend(fontsize=9, loc='upper right'); ax.set_ylim(0, 1.15)
    fig.tight_layout(); _save(fig, 'plot_13_champion_comparison.png')


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
    plot_yield(df)
    plot_saving(df)
    plot_healthiness(df)

    plot_yield_vs_saving(df)
    plot_yield_vs_healthiness(df)
    plot_saving_vs_healthiness(df)
    plot_fitness_vs_saving(df)
    plot_fitness_vs_yield(df)
    plot_fitness_vs_healthiness(df)

    plot_fish_count(df)
    plot_status(df)
    plot_champion_comparison(df)

    print(f"\n  All plots saved to {OUTPUT_DIR}/")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()