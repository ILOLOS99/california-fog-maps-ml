import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.lines as mlines
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

MONTH_LABELS = ["Jan","Feb","Mar","Apr","May","Jun",
                "Jul","Aug","Sep","Oct","Nov","Dec"]

BENCHMARKS = [
    (0.50, "#0F6E56", "#E1F5EE"),
    (1.00, "#633806", "#FAEEDA"),
]

MODELS      = ["LightGBM", "XGBoost", "Random Forest"]
MONTHS      = list(range(1, 13))
N_SUBCOLS   = len(MODELS)
COL_SPACING = 1.0
SUB_WIDTH   = COL_SPACING / (N_SUBCOLS + 1)

BREAK_PT      = 2.0
BREAK_PT_ZERO = 0.02

# GLOBAL FONT SIZES
FS_SUPTITLE = 32
FS_TITLE    = 24
FS_AXIS     = 22
FS_TICK     = 19
FS_LEGEND   = 20

plt.rcParams.update({
    "font.size":        FS_TICK,
    "axes.titlesize":   FS_TITLE,
    "axes.labelsize":   FS_AXIS,
    "xtick.labelsize":  FS_TICK,
    "ytick.labelsize":  FS_TICK,
    "legend.fontsize":  FS_LEGEND,
})

# LOAD
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
pos_obs  = data[data["obs_freq"] >  0].copy()
zero_obs = data[data["obs_freq"] == 0].copy()
years    = sorted(data["year_local"].dropna().unique().astype(int))

# GLOBAL Y LIMITS
def get_ymax(df, col, pct=99, ceil_factor=10):
    vals = df[col].dropna().values
    return np.ceil(np.percentile(vals, pct) * ceil_factor) / ceil_factor

GLOBAL_POS_YMAX  = max(get_ymax(pos_obs,  "rel_abs_err", pct=99, ceil_factor=4),  2.1)
GLOBAL_ZERO_YMAX = max(get_ymax(zero_obs, "pred_freq",   pct=99, ceil_factor=20), 0.05)

print(f"Global y-max (obs>0) : {GLOBAL_POS_YMAX}")
print(f"Global y-max (obs=0) : {GLOBAL_ZERO_YMAX}")

# BROKEN AXIS MARKS
def draw_broken_marks(ax_bottom, ax_top, color="#5F5E5A"):
    d = 0.012
    for ax, y in [(ax_bottom, 1), (ax_top, 0)]:
        kw = dict(transform=ax.transAxes, color=color,
                  clip_on=False, linewidth=0.8)
        ax.plot((-d, +d), (y - d, y + d), **kw)
        ax.plot((1 - d, 1 + d), (y - d, y + d), **kw)

# BENCHMARK BAND HELPER
def add_benchmark_bands(ax, y_min, y_max):
    prev = 0
    for thresh, line_color, band_color in BENCHMARKS:
        upper_clipped = min(thresh if thresh is not None else y_max, y_max)
        lower_clipped = max(prev, y_min)
        if upper_clipped > lower_clipped:
            ax.axhspan(lower_clipped, upper_clipped,
                       color=band_color, alpha=0.30, zorder=0, linewidth=0)
        if thresh is not None and y_min < thresh < y_max:
            ax.axhline(thresh, color=line_color, linewidth=1.5,
                       linestyle=":", alpha=0.9, zorder=1)
        prev = thresh if thresh is not None else y_max
    if y_max > 1.0 and y_min < y_max:
        ax.axhspan(max(1.0, y_min), y_max, color="#FCEBEB",
                   alpha=0.30, zorder=0, linewidth=0)

# STRIP PLOT HELPER
def draw_strip(ax, yr_df, months, val_col, x_min, x_max):
    for mo in range(2, 13):
        ax.axvline((mo - 1) * COL_SPACING - COL_SPACING * 0.5 + 0.5,
                   color="#DDDDDD", linewidth=0.5, zorder=0)

    for mo_idx, mo in enumerate(months):
        month_center = mo_idx * COL_SPACING + 0.5
        sub_xs = np.linspace(
            month_center - SUB_WIDTH * (N_SUBCOLS - 1) / 2,
            month_center + SUB_WIDTH * (N_SUBCOLS - 1) / 2,
            N_SUBCOLS
        )

        for mi, model in enumerate(MODELS):
            sub = yr_df[
                (yr_df["model"]       == model) &
                (yr_df["month_local"] == mo)
            ][val_col].dropna().values

            if len(sub) == 0:
                continue

            ax.scatter(
                np.full(len(sub), sub_xs[mi]),
                sub,
                color=MODEL_COLORS[model],
                s=90, alpha=0.70,
                linewidths=0,
                marker="o",
                zorder=3
            )

    ax.set_xlim(x_min, x_max)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_linewidth(0.5)
    ax.tick_params(axis="y", labelsize=FS_TICK)


# ONE FIGURE PER YEAR
FIGURE_LABELS = {
    2019: "S1",
    2020: "S2",
    2021: "S3",
    2022: "S4",
    2023: "S5",
    2024: "S6",
}

for yr in years:
    yr_pos  = pos_obs[pos_obs["year_local"]   == yr]
    yr_zero = zero_obs[zero_obs["year_local"]  == yr]

    x_min = 0
    x_max = len(MONTHS) * COL_SPACING
    xtick_pos = [mo_idx * COL_SPACING + 0.5 for mo_idx, _ in enumerate(MONTHS)]

    def make_xtick_labels(yr_df):
        labels = []
        for mo in MONTHS:
            counts = [
                len(yr_df[
                    (yr_df["model"] == model) &
                    (yr_df["month_local"] == mo)
                ])
                for model in MODELS
            ]
            n = max(counts) if counts else 0
            labels.append(f"{MONTH_LABELS[mo-1]}\n(n={n})")
        return labels

    xtick_labels_pos  = make_xtick_labels(yr_pos)
    xtick_labels_zero = make_xtick_labels(yr_zero)

    # FIGURE LAYOUT
    fig = plt.figure(figsize=(32, 20))
    fig.patch.set_facecolor("#FAFAF8")

    outer = gridspec.GridSpec(2, 1, figure=fig,
                              height_ratios=[3, 2], hspace=0.55)

    inner_top = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=outer[0],
        hspace=0.06, height_ratios=[1, 3]
    )
    inner_bot = gridspec.GridSpecFromSubplotSpec(
        2, 1, subplot_spec=outer[1],
        hspace=0.06, height_ratios=[1, 3]
    )
    ax_top_upper = fig.add_subplot(inner_top[0])
    ax_top_lower = fig.add_subplot(inner_top[1])
    ax_bot_upper = fig.add_subplot(inner_bot[0])
    ax_bot_lower = fig.add_subplot(inner_bot[1])

    fig.text(0.5, 0.99,
             f"Station-level ARE and Predicted Frequency by Month — {yr}",
             ha="center", va="top",
             fontsize=FS_SUPTITLE, fontweight="bold", color="#1A1A1A")

    # TOP PANEL (broken axis)
    add_benchmark_bands(ax_top_lower, 0,        BREAK_PT)
    add_benchmark_bands(ax_top_upper, BREAK_PT, GLOBAL_POS_YMAX)

    for ax in [ax_top_lower, ax_top_upper]:
        draw_strip(ax, yr_pos, MONTHS, "rel_abs_err", x_min, x_max)

    ax_top_lower.set_ylim(0,        BREAK_PT)
    ax_top_upper.set_ylim(BREAK_PT, GLOBAL_POS_YMAX)

    ax_top_lower.set_xticks(xtick_pos)
    ax_top_lower.set_xticklabels(xtick_labels_pos, fontsize=FS_TICK)
    ax_top_upper.set_xticks(xtick_pos)
    ax_top_upper.set_xticklabels([])

    ax_top_upper.spines["bottom"].set_visible(False)
    ax_top_lower.spines["top"].set_visible(False)
    ax_top_upper.tick_params(bottom=False)

    ax_top_lower.set_ylabel("ARE", fontsize=FS_AXIS)
    ax_top_upper.set_title(
        "Station-months where observed frequency > 0",
        fontsize=FS_TITLE, fontweight="normal", pad=8, color="#333333"
    )
    draw_broken_marks(ax_top_lower, ax_top_upper)

    # BOTTOM PANEL (broken axis)
    for ax in [ax_bot_lower, ax_bot_upper]:
        ax.axhline(0, color="#1D9E75", linewidth=1.5,
                   linestyle="--", alpha=0.6, zorder=0)
        draw_strip(ax, yr_zero, MONTHS, "pred_freq", x_min, x_max)

    ax_bot_lower.set_ylim(0,             BREAK_PT_ZERO)
    ax_bot_upper.set_ylim(BREAK_PT_ZERO, GLOBAL_ZERO_YMAX)

    ax_bot_lower.set_xticks(xtick_pos)
    ax_bot_lower.set_xticklabels(xtick_labels_zero, fontsize=FS_TICK)
    ax_bot_upper.set_xticks(xtick_pos)
    ax_bot_upper.set_xticklabels([])

    ax_bot_upper.spines["bottom"].set_visible(False)
    ax_bot_lower.spines["top"].set_visible(False)
    ax_bot_upper.tick_params(bottom=False)

    ax_bot_lower.set_ylabel("Predicted fog frequency", fontsize=FS_AXIS)
    ax_bot_upper.set_title(
        "Station-months where observed frequency = 0",
        fontsize=FS_TITLE, fontweight="normal", pad=8, color="#333333"
    )
    draw_broken_marks(ax_bot_lower, ax_bot_upper)

    # LEGEND
    model_handles = [
        mpatches.Patch(facecolor=MODEL_COLORS[m], alpha=0.82, label=m)
        for m in MODELS
    ]
    fig.legend(
        handles=model_handles,
        loc="lower center", ncol=3,
        fontsize=FS_LEGEND, frameon=False,
        bbox_to_anchor=(0.5, -0.02)
    )

    plt.subplots_adjust(left=0.05, right=0.99, top=0.94, bottom=0.10)
    fig_label = FIGURE_LABELS[yr]
    out_file = f"figure_{fig_label}.png"

    fig.savefig(
        out_file,
        dpi=300,
        bbox_inches="tight",
        facecolor=fig.get_facecolor()
    )

    plt.show()
    plt.close()

    print(f"✓ Saved: {out_file}")
