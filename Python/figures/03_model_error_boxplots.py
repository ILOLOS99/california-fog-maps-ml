import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.gridspec as gridspec

model_files = {
    "LightGBM":      "LightGBM_with_coords.csv",
    "XGBoost":       "XGBoost_with_coords.csv",
    "Random Forest": "Random Forest_Fixed Hyperparameters_with_coords.csv"
}

MODEL_COLORS = {
    "LightGBM":      "#378ADD",
    "XGBoost":       "#D85A30",
    "Random Forest": "#1D9E75"
}

BENCHMARKS = [
    (0.50, "#0F6E56", "#E1F5EE", "0 – 0.50"),
    (1.00, "#633806", "#FAEEDA", "0.50 – 1.00"),
    (None, "#791F1F", "#FCEBEB", "> 1.00"),
]

# GLOBAL FONT SIZES
FS_SUPTITLE  = 24
FS_SUBTITLE  = 16
FS_TITLE     = 20
FS_AXIS      = 16
FS_TICK      = 14
FS_BAND      = 13
FS_LEGEND    = 18
FS_ANNOT     = 12

plt.rcParams.update({
    "font.size":        FS_TICK,
    "axes.titlesize":   FS_TITLE,
    "axes.labelsize":   FS_AXIS,
    "xtick.labelsize":  FS_TICK,
    "ytick.labelsize":  FS_TICK,
    "legend.fontsize":  FS_LEGEND,
})

# LOAD & CALCULATE
all_dfs = []
for model_name, filename in model_files.items():
    df = pd.read_csv(filename)
    df["model"] = model_name
    df["rel_abs_err"] = np.where(
        df["obs_freq"] > 0,
        np.abs(df["obs_freq"] - df["pred_freq"]) / df["obs_freq"],
        np.nan
    )
    all_dfs.append(df)

data     = pd.concat(all_dfs, ignore_index=True)
models   = ["LightGBM", "XGBoost", "Random Forest"]
pos_obs  = data[data["obs_freq"] >  0].copy()
zero_obs = data[data["obs_freq"] == 0].copy()

n_pos_sm   = len(pos_obs)  // len(models)
n_zero_sm  = len(zero_obs) // len(models)
n_total_sm = n_pos_sm + n_zero_sm
pct_pos    = 100 * n_pos_sm  / n_total_sm
pct_zero   = 100 * n_zero_sm / n_total_sm
print(f"obs>0 station-months : {n_pos_sm}  of {n_total_sm} ({pct_pos:.1f}%)")
print(f"obs=0 station-months : {n_zero_sm} of {n_total_sm} ({pct_zero:.1f}%)")

years   = sorted(data["year_local"].dropna().unique().astype(int))
n_years = len(years)
width   = 0.22
offsets = np.linspace(-(len(models) - 1) * width / 2,
                       (len(models) - 1) * width / 2, len(models))

# HELPERS
def draw_broken_marks(ax_bottom, ax_top, color="#5F5E5A"):
    d = 0.012
    for ax, y in [(ax_bottom, 1), (ax_top, 0)]:
        kw = dict(transform=ax.transAxes, color=color,
                  clip_on=False, linewidth=0.8)
        ax.plot((-d, +d), (y - d, y + d), **kw)
        ax.plot((1 - d, 1 + d), (y - d, y + d), **kw)


def add_benchmark_bands(ax, y_min, y_max, benchmarks, n_years):
    thresholds = [0.0] + [b[0] for b in benchmarks if b[0] is not None] + [y_max]

    for i, (upper, line_color, band_color, label) in enumerate(benchmarks):
        lower         = thresholds[i]
        upper_clipped = min(upper if upper is not None else y_max, y_max)
        lower_clipped = max(lower, y_min)

        if upper_clipped <= y_min or lower_clipped >= y_max:
            continue

        ax.axhspan(lower_clipped, upper_clipped,
                   color=band_color, alpha=0.35, zorder=0, linewidth=0)

        if upper is not None and y_min < upper < y_max:
            ax.axhline(upper, color=line_color, linewidth=0.8,
                       linestyle=":", alpha=0.9, zorder=1)

    bench_vals = [b[0] for b in benchmarks if b[0] is not None
                  and y_min < b[0] < y_max]
    if bench_vals:
        existing = list(ax.get_yticks())
        combined = sorted(set(existing + bench_vals))
        ax.set_yticks(combined)


def draw_boxplots(ax_bottom, ax_top, df, value_col, years, models,
                  offsets, width, break_pt, upper_max,
                  ref_line, ref_color, ref_label, benchmarks=None):

    if benchmarks is not None:
        add_benchmark_bands(ax_bottom, 0,        break_pt,  benchmarks, n_years)
        add_benchmark_bands(ax_top,    break_pt, upper_max, benchmarks, n_years)

    for mi, model in enumerate(models):
        color     = MODEL_COLORS[model]
        positions = np.arange(n_years) + offsets[mi]
        plot_data = [
            df.loc[
                (df["model"] == model) & (df["year_local"] == yr),
                value_col
            ].dropna().values
            for yr in years
        ]

        bp_kwargs = dict(
            positions=positions,
            widths=width * 0.85,
            patch_artist=True,
            showfliers=True,
            flierprops=dict(marker="o", markersize=2.5,
                            markerfacecolor=color,
                            markeredgewidth=0, alpha=0.4),
            medianprops=dict(color="white", linewidth=1.8),
            whiskerprops=dict(linewidth=0.8, color="#5F5E5A"),
            capprops=dict(linewidth=0.8, color="#5F5E5A"),
            boxprops=dict(linewidth=0)
        )

        for ax in [ax_bottom, ax_top]:
            bp = ax.boxplot(plot_data, **bp_kwargs)
            for patch in bp["boxes"]:
                patch.set_facecolor(color)
                patch.set_alpha(0.82)

    for ax in [ax_bottom, ax_top]:
        ax.axhline(ref_line, color=ref_color, linewidth=1.0,
                   linestyle="--", alpha=0.75, zorder=2)

    ax_bottom.set_ylim(0, break_pt)
    ax_top.set_ylim(break_pt, upper_max)

    ax_bottom.set_xticks(np.arange(n_years))
    ax_bottom.set_xticklabels(years, fontsize=FS_TICK)
    ax_top.set_xticks(np.arange(n_years))
    ax_top.set_xticklabels([])

    ax_top.spines["bottom"].set_visible(False)
    ax_bottom.spines["top"].set_visible(False)
    ax_top.tick_params(bottom=False)

    for ax in [ax_bottom, ax_top]:
        ax.spines["right"].set_visible(False)
        ax.spines[["left", "bottom", "top"]].set_linewidth(0.5)
        ax.tick_params(axis="y", labelsize=FS_TICK)

    draw_broken_marks(ax_bottom, ax_top)


def add_panel(fig, subplot_spec, df, value_col, title, ylabel,
               ref_line, ref_color, ref_label,
               break_pt, upper_max, benchmarks=None):
    """Build one broken-axis panel inside subplot_spec."""
    inner = gridspec.GridSpecFromSubplotSpec(
        2, 1,
        subplot_spec=subplot_spec,
        hspace=0.06,
        height_ratios=[1, 3]
    )
    ax_top    = fig.add_subplot(inner[0])
    ax_bottom = fig.add_subplot(inner[1])

    draw_boxplots(
        ax_bottom, ax_top, df, value_col,
        years, models, offsets, width,
        break_pt, upper_max,
        ref_line, ref_color, ref_label,
        benchmarks=benchmarks
    )

    ax_top.set_title(title, fontsize=FS_TITLE, fontweight="500", pad=10)
    ax_bottom.set_ylabel(ylabel, fontsize=FS_AXIS)


# COMPUTE Y-AXIS LIMITS
def shared_limits(df, cols):
    all_vals  = np.concatenate([df[c].dropna().values for c in cols])
    break_pt  = np.ceil(np.percentile(all_vals, 95)   * 20) / 20
    upper_max = np.ceil(np.percentile(all_vals, 99.5) * 10) / 10
    return break_pt, upper_max


# SINGLE FIGURE — two panels side by side
break_pt1, upper_max1 = shared_limits(pos_obs,  ["rel_abs_err"])
break_pt2, upper_max2 = shared_limits(zero_obs, ["pred_freq"])

fig = plt.figure(figsize=(20, 8))

outer = gridspec.GridSpec(1, 2, figure=fig, wspace=0.14)

# Left panel: ARE (obs > 0)
add_panel(
    fig, outer[0],
    df         = pos_obs,
    value_col  = "rel_abs_err",
    title      = f"Absolute Relative Error  ({n_pos_sm:,} station-months, obs > 0)",
    ylabel     = "ARE",
    ref_line   = 1.0,
    ref_color  = "#E24B4A",
    ref_label  = "Error = 1",
    break_pt   = break_pt1,
    upper_max  = upper_max1,
    benchmarks = BENCHMARKS
)

# Right panel: false alarms (obs = 0)
add_panel(
    fig, outer[1],
    df         = zero_obs,
    value_col  = "pred_freq",
    title      = f"Predicted fog frequency  ({n_zero_sm:,} station-months, obs = 0)",
    ylabel     = "Predicted fog frequency",
    ref_line   = 0.0,
    ref_color  = "#1D9E75",
    ref_label  = "Ideal prediction (0)",
    break_pt   = break_pt2,
    upper_max  = upper_max2,
    benchmarks = None
)

# Shared legend
legend_handles = [
    mpatches.Patch(facecolor=MODEL_COLORS[m], alpha=0.82, label=m)
    for m in models
]
fig.legend(handles=legend_handles, loc="lower center",
           ncol=3, fontsize=FS_LEGEND, frameon=False,
           bbox_to_anchor=(0.5, -0.05))

plt.subplots_adjust(left=0.06, right=0.97, top=0.93, bottom=0.12, wspace=0.14)

fig.savefig(
    "figure_3.png",
    dpi=300,
    bbox_inches="tight"
)

plt.show()
plt.close()

print("✓ Saved: figure_3.png")
