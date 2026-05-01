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

from constants import RESULTS_CSV_PATH, PLOTS_DIR, MAX_BUDGET, INITIAL_POND_COUNT

CSV_PATH = RESULTS_CSV_PATH
OUTPUT_DIR = PLOTS_DIR

DPI = 180
SINGLE_FIG_SIZE = (12, 10)

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

# ════════════════════════════════════════════════════════════════
# FONT SIZES (centralized)
# ════════════════════════════════════════════════════════════════

_BASE_FONT = 11
_BASE_LABEL = 12
_BASE_TITLE = 14
_BASE_LEGEND = 10
_BASE_TICK = 11

FONT_SIZE = _BASE_FONT * 1.3          # 14.3
LABEL_SIZE = _BASE_LABEL * 1.3        # 15.6
TITLE_SIZE = _BASE_TITLE * 1.3        # 18.2
LEGEND_SIZE = _BASE_LEGEND * 2.0      # 20.0
TICK_SIZE = _BASE_TICK * 1.3          # 14.3
SMALL_LEGEND_SIZE = 7 * 2.0           # 14.0 (for metric-vs-gen plots)
CHAMPION_LEGEND_SIZE = 9 * 2.0        # 18.0

# ════════════════════════════════════════════════════════════════
# LAYOUT CONSTANTS (for outside-legend placement)
# ════════════════════════════════════════════════════════════════

TITLE_PAD = 55
TIGHT_LAYOUT_RECT = [0, 0, 1, 0.93]


def _apply_theme():
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'axes.edgecolor': '#333333', 'axes.labelcolor': '#222222',
        'axes.grid': True, 'grid.color': '#dddddd', 'grid.linestyle': '--', 'grid.alpha': 0.7,
        'text.color': '#222222', 'xtick.color': '#333333', 'ytick.color': '#333333',
        'legend.facecolor': 'white', 'legend.edgecolor': '#cccccc', 'legend.framealpha': 0.9,
        'font.size': FONT_SIZE,
        'axes.titlesize': TITLE_SIZE,
        'axes.labelsize': LABEL_SIZE,
        'xtick.labelsize': TICK_SIZE,
        'ytick.labelsize': TICK_SIZE,
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


def _place_legend_outside(ax, fontsize, ncol=None):
    """Place legend above the axes, outside the plot area."""
    handles, labels = ax.get_legend_handles_labels()
    if not handles:
        return
    if ncol is None:
        ncol = min(len(handles), 4)
    ax.legend(fontsize=fontsize, loc='lower left',
              bbox_to_anchor=(0.0, 1.02), ncol=ncol, borderaxespad=0.0)


# ════════════════════════════════════════════════════════════════
# METRIC VS GENERATION (Average + Std Dev shade)
# ════════════════════════════════════════════════════════════════

def _plot_metric_vs_gen(ax, df, col, ylabel, title, fmt=None, ylim=None):
    for tl in sorted(df['timeline'].unique()):
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        gens = sorted(sdf['generation'].unique())
        means, stds, gl = [], [], []
        for g in gens:
            vals = sdf[sdf['generation'] == g][col].values
            means.append(vals.mean())
            stds.append(vals.std())
            gl.append(g)
        means = np.array(means)
        stds = np.array(stds)
        gl = np.array(gl)

        # Shaded region: mean ± 1 std dev
        ax.fill_between(gl, means - stds, means + stds,
                         color=color, alpha=0.10, zorder=1,
                         label=f"TL {tl} ±1 Std Dev")
        # Average line
        ax.plot(gl, means, color=color, linewidth=2.5, alpha=0.9,
                marker='o', markersize=4, label=f"TL {tl} Average", zorder=3)

    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=TITLE_PAD)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    if ylim: ax.set_ylim(ylim)
    if fmt: ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt))
    _place_legend_outside(ax, SMALL_LEGEND_SIZE)


# ════════════════════════════════════════════════════════════════
# METRIC VS METRIC (Average + Std Dev shade, binned)
# ════════════════════════════════════════════════════════════════

def _plot_metric_vs_metric(ax, df, col_x, col_y, xlabel, ylabel, title,
                           fmt_x=None, fmt_y=None, xlim=None, ylim=None, bins=20):
    for tl in sorted(df['timeline'].unique()):
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]

        x_vals = sdf[col_x].values
        y_vals = sdf[col_y].values

        # Bin x-values to compute average and std of y per bin
        bin_edges = np.linspace(x_vals.min(), x_vals.max(), bins + 1)
        bin_centers, means, stds = [], [], []
        for i in range(len(bin_edges) - 1):
            mask = (x_vals >= bin_edges[i]) & (x_vals < bin_edges[i + 1])
            if i == len(bin_edges) - 2:  # include right edge in last bin
                mask = (x_vals >= bin_edges[i]) & (x_vals <= bin_edges[i + 1])
            if mask.sum() > 0:
                bin_centers.append((bin_edges[i] + bin_edges[i + 1]) / 2)
                means.append(y_vals[mask].mean())
                stds.append(y_vals[mask].std())

        bin_centers = np.array(bin_centers)
        means = np.array(means)
        stds = np.array(stds)

        # Shaded region: mean ± 1 std dev
        ax.fill_between(bin_centers, means - stds, means + stds,
                         color=color, alpha=0.10, zorder=1,
                         label=f"TL {tl} ±1 Std Dev")
        # Average line
        ax.plot(bin_centers, means, color=color, linewidth=2.5, alpha=0.9,
                marker='o', markersize=4, label=f"TL {tl} Average", zorder=3)

    ax.set_xlabel(xlabel, fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=TITLE_PAD)
    if xlim: ax.set_xlim(xlim)
    if ylim: ax.set_ylim(ylim)
    if fmt_x: ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_x))
    if fmt_y: ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_y))
    _place_legend_outside(ax, SMALL_LEGEND_SIZE)

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
    cbar.ax.tick_params(labelsize=TICK_SIZE)

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
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_01_fitness_vs_gen.png')

def plot_yield(df):
    if 'yield' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'yield', 'Yield', 'Yield vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_02_yield_vs_gen.png')

def plot_saving(df):
    if 'saving' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'saving', 'Saving ($)', 'Saving vs Generation',
                        fmt=lambda x, _: f'${x:,.0f}')
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_03_saving_vs_gen.png')

def plot_healthiness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'healthiness', 'Healthiness', 'Healthiness vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_04_healthiness_vs_gen.png')

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

def plot_fish_count_vs_gen(df):
    if 'fish_count' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'fish_count', 'Fish Count',
                        'Initial Fish Count vs Generation', ylim=(0, 110))
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_11_fish_count_vs_gen.png')

def plot_fish_count_vs_cost(df):
    if 'fish_count' not in df.columns or 'cost' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_metric(ax, df, 'fish_count', 'cost', 'Fish Count', 'Cost ($)',
                           'Fish Count vs Cost',
                           fmt_y=lambda x, _: f'${x:,.0f}')
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_12_fish_count_vs_cost.png')

def plot_status(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    status_order = ['OK', 'ALL-DEAD', 'OVER-BUDGET', 'GATEKEEPER']
    gens = sorted(df['generation'].unique())
    n_timelines = df['timeline'].nunique()
    bottom = np.zeros(len(gens))
    for status in status_order:
        counts = np.array([len(df[(df['generation'] == g) & (df['status'] == status)])
                           for g in gens], dtype=float)
        counts = counts / n_timelines
        label = STATUS_LABELS.get(status, status)
        ax.bar(gens, counts, bottom=bottom, color=STATUS_COLORS.get(status, '#aaa'),
               label=label, alpha=0.85, edgecolor='white', linewidth=0.5)
        bottom += counts
    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel('Pond Count', fontweight='bold')
    ax.set_title('Pond Status Distribution per Generation', fontweight='bold', pad=TITLE_PAD)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.set_ylim(0, INITIAL_POND_COUNT + 1)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    _place_legend_outside(ax, LEGEND_SIZE)
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_13_status.png')

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
        sav = row.get('saving', 0)
        best_sav_rate.append(sav / MAX_BUDGET if MAX_BUDGET > 0 else 0)
        labels.append(f"TL {tl}")
    x = np.arange(len(timelines)); w = 0.18

    # Order: Fitness, Yield, Saving, Healthiness
    b1 = ax.bar(x - 1.5*w, best_fit,      w, label='Fitness',     color='#1f77b4', alpha=0.9, edgecolor='white')
    b2 = ax.bar(x - 0.5*w, best_yld,      w, label='Yield',       color='#2ca02c', alpha=0.9, edgecolor='white')
    b3 = ax.bar(x + 0.5*w, best_sav_rate,  w, label='Saving',      color='#9467bd', alpha=0.9, edgecolor='white')
    b4 = ax.bar(x + 1.5*w, best_hlth,      w, label='Healthiness', color='#ff7f0e', alpha=0.9, edgecolor='white')

    for bars in [b1, b2, b3, b4]:
        for bar in bars:
            h = bar.get_height()
            if h > 0.01:
                ax.text(bar.get_x() + bar.get_width()/2, h + 0.012, f'{h:.3f}',
                        ha='center', va='bottom', fontsize=16, color='#333')

    # Place "BEST" annotation below the bar to avoid overlapping value labels
    best_tl_idx = int(np.argmax(best_fit))
    best_bar_x = best_tl_idx - 1.5*w
    best_bar_h = best_fit[best_tl_idx]
    ax.annotate('BEST', xy=(best_bar_x, best_bar_h),
                xytext=(best_bar_x, max(0, best_bar_h - 0.20)),
                ha='center', fontsize=13, fontweight='bold', color='#d62728',
                arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.5))

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel('Timeline', fontweight='bold')
    ax.set_ylabel('Score (0 - 1)', fontweight='bold')
    ax.set_title('Comparisons of Champions From All Timelines', fontweight='bold', pad=TITLE_PAD)
    _place_legend_outside(ax, CHAMPION_LEGEND_SIZE, ncol=4)
    ax.set_ylim(0, 1.15)
    fig.tight_layout(rect=TIGHT_LAYOUT_RECT); _save(fig, 'plot_14_champion_comparison.png')


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

    plot_fish_count_vs_gen(df)
    plot_fish_count_vs_cost(df)
    plot_status(df)
    plot_champion_comparison(df)

    print(f"\n  All plots saved to {OUTPUT_DIR}/")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()