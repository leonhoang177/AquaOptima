#!/usr/bin/env python3
"""
plot.py -- Visualize EA evolution from results.csv
Option A: fish_count is fixed, so fish_count plots are removed.
"""

import sys, os
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.colors as mcolors
from pathlib import Path

from constants import RESULTS_CSV_PATH, PLOTS_DIR, MAX_BUDGET, POND_POPULATION, FISH_COUNT

CSV_PATH = RESULTS_CSV_PATH
OUTPUT_DIR = PLOTS_DIR

DPI = 280
SINGLE_FIG_SIZE = (20, 17)

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
# FONT SIZES (centralized, scaled up)
# ════════════════════════════════════════════════════════════════

_BASE_FONT = 11
_BASE_LABEL = 12
_BASE_TITLE = 14
_BASE_LEGEND = 10
_BASE_TICK = 11

_SCALE = 1.3 * 1.3 * 1.3  # triple 30% scaling = ~2.197

FONT_SIZE = _BASE_FONT * _SCALE          # ~24.2
LABEL_SIZE = _BASE_LABEL * _SCALE        # ~26.4
TITLE_SIZE = _BASE_TITLE * _SCALE        # ~30.8
LEGEND_SIZE = _BASE_LEGEND * _SCALE      # ~22.0
TICK_SIZE = _BASE_TICK * _SCALE          # ~24.2
SMALL_LEGEND_SIZE = 7 * _SCALE           # ~15.4
CHAMPION_LEGEND_SIZE = 9 * _SCALE        # ~19.8

# Genotype plots get extra scaling
_GENO_SCALE = _SCALE * 1.3
GENO_FIG_SIZE = (26, 22)
GENO_FONT_SIZE = _BASE_FONT * _GENO_SCALE
GENO_LABEL_SIZE = _BASE_LABEL * _GENO_SCALE
GENO_TITLE_SIZE = _BASE_TITLE * _GENO_SCALE
GENO_TICK_SIZE = _BASE_TICK * _GENO_SCALE
GENO_LEGEND_SIZE = _BASE_LEGEND * _GENO_SCALE


def _apply_theme():
    plt.rcParams.update({
        'figure.facecolor': 'white', 'axes.facecolor': 'white',
        'axes.edgecolor': '#333333', 'axes.labelcolor': '#222222',
        'axes.grid': True, 'grid.color': '#dddddd', 'grid.linestyle': '--', 'grid.alpha': 0.7,
        'text.color': '#222222', 'xtick.color': '#333333', 'ytick.color': '#333333',
        'legend.facecolor': 'white', 'legend.edgecolor': '#cccccc', 'legend.framealpha': 0.7,
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


def _filter_legend_avg_only(ax):
    """Remove Std Dev entries from legend, keep only Average lines."""
    handles, labels = ax.get_legend_handles_labels()
    filtered_h, filtered_l = [], []
    for h, l in zip(handles, labels):
        if 'Std Dev' not in l:
            filtered_h.append(h)
            filtered_l.append(l)
    if filtered_h:
        ax.legend(filtered_h, filtered_l, fontsize=SMALL_LEGEND_SIZE,
                  loc='best', framealpha=0.7)


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
                         color=color, alpha=0.06, zorder=1,
                         label=f"TL {tl} ±1 Std Dev")
        # Average line
        ax.plot(gl, means, color=color, linewidth=3.2, alpha=0.9,
                marker='o', markersize=5, label=f"TL {tl} Average", zorder=3)

    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    if ylim:
        ax.set_ylim(ylim)
        if ylim == (-0.02, 1.02):
            ax.yaxis.set_major_locator(mticker.MultipleLocator(0.1))
    if fmt: ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt))
    _filter_legend_avg_only(ax)


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
                         color=color, alpha=0.06, zorder=1,
                         label=f"TL {tl} ±1 Std Dev")
        # Average line
        ax.plot(bin_centers, means, color=color, linewidth=3.2, alpha=0.9,
                marker='o', markersize=5, label=f"TL {tl} Average", zorder=3)

    ax.set_xlabel(xlabel, fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=12)
    if xlim: ax.set_xlim(xlim)
    if ylim: ax.set_ylim(ylim)
    if fmt_x: ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_x))
    if fmt_y: ax.yaxis.set_major_formatter(mticker.FuncFormatter(fmt_y))
    _filter_legend_avg_only(ax)

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

    sc = ax.scatter(x, y, c=c, cmap='RdYlGn', s=40, alpha=0.7,
                    edgecolors='#333333', linewidth=0.3, zorder=2)

    cbar = fig.colorbar(sc, ax=ax, shrink=0.8)
    cbar.set_label('Fitness', fontweight='bold')
    cbar.ax.tick_params(labelsize=TICK_SIZE)

    ax.set_xlabel(xlabel, fontweight='bold')
    ax.set_ylabel(ylabel, fontweight='bold')
    ax.set_title(title, fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MultipleLocator(0.1))
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.1))

    fig.tight_layout(); _save(fig, filename)


# ════════════════════════════════════════════════════════════════
# GENOTYPE CONVERGENCE PLOTS
# ════════════════════════════════════════════════════════════════

def _plot_genotype_convergence(df, policy_name, qty_col, int_col, loc_col,
                                qty_label, int_label, title, filename):
    """Plot genotype convergence: quantity/duration + interval + location."""
    timelines = sorted(df['timeline'].unique())
    n_timelines = len(timelines)
    n_gens = df['generation'].max()

    # Responsive width
    fig_w = max(GENO_FIG_SIZE[0], n_gens * n_timelines * 0.35 + 6)
    fig_h = GENO_FIG_SIZE[1]

    fig = plt.figure(figsize=(fig_w, fig_h))
    gs = fig.add_gridspec(2, 2, height_ratios=[1, 1], hspace=0.35, wspace=0.3)
    ax_qty = fig.add_subplot(gs[0, 0])
    ax_int = fig.add_subplot(gs[0, 1])
    ax_loc = fig.add_subplot(gs[1, :])

    # ── Quantity / Duration subplot ──
    for tl in timelines:
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        gens = sorted(sdf['generation'].unique())
        means, stds, gl = [], [], []
        for g in gens:
            vals = sdf[sdf['generation'] == g][qty_col].values
            means.append(vals.mean()); stds.append(vals.std()); gl.append(g)
        means, stds, gl = np.array(means), np.array(stds), np.array(gl)
        ax_qty.fill_between(gl, means - stds, means + stds, color=color, alpha=0.06)
        ax_qty.plot(gl, means, color=color, linewidth=3.2, alpha=0.9,
                    marker='o', markersize=5, label=f"TL {tl}")
    ax_qty.set_xlabel('Generation', fontweight='bold', fontsize=GENO_LABEL_SIZE)
    ax_qty.set_ylabel(qty_label, fontweight='bold', fontsize=GENO_LABEL_SIZE)
    ax_qty.set_title(qty_label, fontweight='bold', fontsize=GENO_TITLE_SIZE, pad=12)
    ax_qty.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax_qty.tick_params(labelsize=GENO_TICK_SIZE)
    ax_qty.legend(fontsize=GENO_LEGEND_SIZE, loc='best', framealpha=0.7)

    # ── Interval subplot ──
    for tl in timelines:
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        gens = sorted(sdf['generation'].unique())
        means, stds, gl = [], [], []
        for g in gens:
            vals = sdf[sdf['generation'] == g][int_col].values
            means.append(vals.mean()); stds.append(vals.std()); gl.append(g)
        means, stds, gl = np.array(means), np.array(stds), np.array(gl)
        ax_int.fill_between(gl, means - stds, means + stds, color=color, alpha=0.06)
        ax_int.plot(gl, means, color=color, linewidth=3.2, alpha=0.9,
                    marker='o', markersize=5, label=f"TL {tl}")
    ax_int.set_xlabel('Generation', fontweight='bold', fontsize=GENO_LABEL_SIZE)
    ax_int.set_ylabel(int_label, fontweight='bold', fontsize=GENO_LABEL_SIZE)
    ax_int.set_title(int_label, fontweight='bold', fontsize=GENO_TITLE_SIZE, pad=12)
    ax_int.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax_int.tick_params(labelsize=GENO_TICK_SIZE)
    ax_int.legend(fontsize=GENO_LEGEND_SIZE, loc='best', framealpha=0.7)

    # ── Location subplot (stacked bars: Center vs Random) ──
    gens = sorted(df['generation'].unique())
    bar_w = min(0.08, 0.7 / max(n_timelines, 1))
    offsets = np.arange(n_timelines) - (n_timelines - 1) / 2

    for i, tl in enumerate(timelines):
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        center_pcts, random_pcts = [], []
        for g in gens:
            gdf = sdf[sdf['generation'] == g]
            n = len(gdf) if len(gdf) > 0 else 1
            center_count = (gdf[loc_col] == 0).sum()
            center_pct = center_count / n * 100
            center_pcts.append(center_pct)
            random_pcts.append(100 - center_pct)

        x = np.array(gens) + offsets[i] * bar_w
        # Center (solid)
        ax_loc.bar(x, center_pcts, bar_w, color=color, alpha=0.85,
                   edgecolor='white', linewidth=0.5,
                   label=f"TL {tl}" if i == 0 else "")
        # Random (hatched)
        ax_loc.bar(x, random_pcts, bar_w, bottom=center_pcts,
                   color=color, alpha=0.50, hatch='///',
                   edgecolor='white', linewidth=0.5)

    # Add texture legend
    from matplotlib.patches import Patch
    texture_handles = [
        Patch(facecolor='gray', alpha=0.85, label='Center (solid)'),
        Patch(facecolor='gray', alpha=0.50, hatch='///', label='Random (hatched)'),
    ]
    tl_handles = [Patch(facecolor=TL_COLORS[(tl - 1) % len(TL_COLORS)],
                        label=f"TL {tl}") for tl in timelines]
    all_handles = tl_handles + texture_handles
    ax_loc.legend(handles=all_handles, fontsize=GENO_LEGEND_SIZE,
                  loc='best', framealpha=0.7, ncol=min(len(all_handles), 6))

    ax_loc.set_xlabel('Generation', fontweight='bold', fontsize=GENO_LABEL_SIZE)
    ax_loc.set_ylabel('Location %', fontweight='bold', fontsize=GENO_LABEL_SIZE)
    ax_loc.set_title(f'{policy_name} Location', fontweight='bold',
                     fontsize=GENO_TITLE_SIZE, pad=12)
    ax_loc.set_ylim(0, 115)
    ax_loc.yaxis.set_major_locator(mticker.MultipleLocator(10))
    ax_loc.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax_loc.tick_params(labelsize=GENO_TICK_SIZE)

    fig.suptitle(title, fontweight='bold', fontsize=GENO_TITLE_SIZE * 1.1, y=0.98)
    fig.subplots_adjust(hspace=0.35, wspace=0.3, top=0.92, bottom=0.08)
    _save(fig, filename)


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

def plot_saving_rate(df):
    if 'saving_rate' not in df.columns: return
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'saving_rate', 'Saving Rate', 'Saving Rate vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(); _save(fig, 'plot_03_saving_rate_vs_gen.png')

def plot_healthiness(df):
    fig, ax = plt.subplots(figsize=SINGLE_FIG_SIZE)
    _plot_metric_vs_gen(ax, df, 'healthiness', 'Healthiness', 'Healthiness vs Generation',
                        fmt=lambda x, _: f'{x:.2f}', ylim=(-0.02, 1.02))
    fig.tight_layout(); _save(fig, 'plot_04_healthiness_vs_gen.png')

def plot_yield_vs_saving(df):
    _plot_pair_fitness(df, 'yield', 'saving_rate', 'Yield', 'Saving Rate',
                       'Yield vs Saving Rate Heatmap', 'plot_05_yield_vs_saving_heatmap.png')

def plot_yield_vs_healthiness(df):
    _plot_pair_fitness(df, 'yield', 'healthiness', 'Yield', 'Healthiness',
                       'Yield vs Healthiness Heatmap', 'plot_06_yield_vs_healthiness_heatmap.png')

def plot_saving_vs_healthiness(df):
    _plot_pair_fitness(df, 'saving_rate', 'healthiness', 'Saving Rate', 'Healthiness',
                       'Saving Rate vs Healthiness Heatmap', 'plot_07_saving_rate_vs_healthiness_heatmap.png')

def plot_food_genotype(df):
    _plot_genotype_convergence(df, 'Food', 'food_quantity', 'food_interval', 'food_location',
                                'Food Quantity', 'Food Interval',
                                'Food Genotype Convergence',
                                'plot_08_food_genotype_convergence.png')

def plot_probiotic_genotype(df):
    _plot_genotype_convergence(df, 'Probiotic', 'probiotic_quantity', 'probiotic_interval',
                                'probiotic_location',
                                'Probiotic Quantity', 'Probiotic Interval',
                                'Probiotic Genotype Convergence',
                                'plot_09_probiotic_genotype_convergence.png')

def plot_oxygen_genotype(df):
    _plot_genotype_convergence(df, 'Oxygen', 'oxygen_duration', 'oxygen_interval',
                                'oxygen_location',
                                'Oxygen Duration', 'Oxygen Interval',
                                'Oxygen Genotype Convergence',
                                'plot_10_oxygen_genotype_convergence.png')

def plot_status(df):
    from matplotlib.patches import Patch

    timelines = sorted(df['timeline'].unique())
    n_timelines = len(timelines)
    gens = sorted(df['generation'].unique())
    n_gens = len(gens)

    # Responsive width
    fig_w = max(SINGLE_FIG_SIZE[0], n_gens * n_timelines * 0.35 + 6)
    fig, ax = plt.subplots(figsize=(fig_w, SINGLE_FIG_SIZE[1]))

    status_order = ['OK', 'ALL-DEAD', 'OVER-BUDGET', 'GATEKEEPER']
    hatches = {'OK': '', 'ALL-DEAD': '///', 'OVER-BUDGET': 'xxx', 'GATEKEEPER': '\\\\\\'}
    bar_w = min(0.08, 0.7 / max(n_timelines, 1))
    offsets = np.arange(n_timelines) - (n_timelines - 1) / 2

    for i, tl in enumerate(timelines):
        sdf = df[df['timeline'] == tl]
        color = TL_COLORS[(tl - 1) % len(TL_COLORS)]
        x_base = np.array(gens) + offsets[i] * bar_w

        bottom = np.zeros(n_gens)
        for status in status_order:
            counts = np.array([len(sdf[(sdf['generation'] == g) & (sdf['status'] == status)])
                               for g in gens], dtype=float)
            hatch = hatches.get(status, '')
            alpha = 0.85 if status == 'OK' else 0.50
            ax.bar(x_base, counts, bar_w, bottom=bottom,
                   color=color, alpha=alpha, hatch=hatch,
                   edgecolor='white', linewidth=0.5)
            bottom += counts

    # Legend: timeline colors + status textures
    tl_handles = [Patch(facecolor=TL_COLORS[(tl - 1) % len(TL_COLORS)],
                        label=f"TL {tl}") for tl in timelines]
    status_handles = [
        Patch(facecolor='gray', alpha=0.85, label='OK'),
        Patch(facecolor='gray', alpha=0.50, hatch='///', label='All Dead'),
        Patch(facecolor='gray', alpha=0.50, hatch='xxx', label='Over Budget'),
        Patch(facecolor='gray', alpha=0.50, hatch='\\\\\\', label='Reject'),
    ]
    all_handles = tl_handles + status_handles
    ax.legend(handles=all_handles, fontsize=LEGEND_SIZE,
              loc='upper left', framealpha=0.7,
              ncol=min(len(all_handles), 5))

    ax.set_xlabel('Generation', fontweight='bold')
    ax.set_ylabel('Pond Count', fontweight='bold')
    ax.set_title('Pond Population Distribution', fontweight='bold', pad=12)
    ax.xaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    ax.set_ylim(0, POND_POPULATION * 1.25)
    ax.yaxis.set_major_locator(mticker.MaxNLocator(integer=True))
    fig.tight_layout(); _save(fig, 'plot_11_pond_population_distribution.png')

def plot_champion_comparison(df):
    from matplotlib.patches import Patch

    timelines = sorted(df['timeline'].unique())
    n_timelines = len(timelines)

    # Responsive width
    fig_w = max(SINGLE_FIG_SIZE[0], n_timelines * 4 + 4)
    fig, ax = plt.subplots(figsize=(fig_w, SINGLE_FIG_SIZE[1]))

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
    x = np.arange(n_timelines); w = 0.18

    b1 = ax.bar(x - 1.5*w, best_fit,      w, label='Fitness',     color='#1f77b4', alpha=0.9, edgecolor='white')
    b2 = ax.bar(x - 0.5*w, best_yld,      w, label='Yield',       color='#2ca02c', alpha=0.9, edgecolor='white')
    b3 = ax.bar(x + 0.5*w, best_sav_rate,  w, label='Saving Rate', color='#9467bd', alpha=0.9, edgecolor='white')
    b4 = ax.bar(x + 1.5*w, best_hlth,      w, label='Healthiness', color='#ff7f0e', alpha=0.9, edgecolor='white')

    # Show fitness values on all bars
    best_tl_idx = int(np.argmax(best_fit))
    for i, bar in enumerate(b1):
        h = bar.get_height()
        if h > 0.01:
            is_best = (i == best_tl_idx)
            color = '#d62728' if is_best else '#333333'
            weight = 'bold' if is_best else 'normal'
            ax.text(bar.get_x() + bar.get_width()/2, h + 0.012, f'{h:.4f}',
                    ha='center', va='bottom', fontsize=TICK_SIZE * 0.7,
                    color=color, fontweight=weight)

    # BEST annotation
    best_bar = b1[best_tl_idx]
    best_bar_x = best_bar.get_x() + best_bar.get_width()/2
    best_bar_h = best_fit[best_tl_idx]
    ax.annotate('BEST', xy=(best_bar_x, best_bar_h),
                xytext=(best_bar_x, max(0, best_bar_h - 0.20)),
                ha='center', fontsize=TICK_SIZE * 0.65, fontweight='bold', color='#d62728',
                arrowprops=dict(arrowstyle='->', color='#d62728', lw=1.5))

    ax.set_xticks(x); ax.set_xticklabels(labels)
    ax.set_xlabel('Timeline', fontweight='bold')
    ax.set_ylabel('Score (0 - 1)', fontweight='bold')
    ax.set_title('Champion Comparison', fontweight='bold', pad=12)
    ax.legend(fontsize=CHAMPION_LEGEND_SIZE, loc='upper left', framealpha=0.7, ncol=4)
    ax.set_ylim(0, 1.25)
    ax.yaxis.set_major_locator(mticker.MultipleLocator(0.1))
    fig.tight_layout(); _save(fig, 'plot_12_champion_comparison.png')


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
    plot_saving_rate(df)
    plot_healthiness(df)

    plot_yield_vs_saving(df)
    plot_yield_vs_healthiness(df)
    plot_saving_vs_healthiness(df)

    plot_food_genotype(df)
    plot_probiotic_genotype(df)
    plot_oxygen_genotype(df)

    plot_status(df)
    plot_champion_comparison(df)

    print(f"\n  All plots saved to {OUTPUT_DIR}/")
    print(f"{'=' * 60}")


if __name__ == '__main__':
    main()
