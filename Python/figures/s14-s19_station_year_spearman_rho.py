import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.ticker as mticker
import matplotlib.lines as mlines
from scipy.stats import spearmanr
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt

test_files = {
    "LightGBM":      "LightGBM_with_coords.csv",
    "XGBoost":       "XGBoost_with_coords.csv",
    "Random Forest": "Random Forest_Fixed Hyperparameters_with_coords.csv",
}

MODELS     = ["LightGBM", "XGBoost", "Random Forest"]
ALL_YEARS  = [2019, 2020, 2021, 2022, 2023, 2024]
MIN_MONTHS = 12

LON_MIN, LON_MAX = -125.0, -113.5
LAT_MIN, LAT_MAX =   32.0,   42.5
PROJ = ccrs.PlateCarree()

MODEL_COLORS = {
    "LightGBM":      "#378ADD",
    "XGBoost":       "#D85A30",
    "Random Forest": "#1D9E75",
}

# COLORMAP
CMAP_RHO = mcolors.LinearSegmentedColormap.from_list(
    "rho_blue",
    [
        (0.0,  "#EBF5FB"),
        (0.25, "#AED6F1"),
        (0.50, "#3498DB"),
        (0.75, "#1A5276"),
        (1.0,  "#0A1628"),
    ]
)
NORM_RHO = mcolors.Normalize(vmin=0.0, vmax=1.0)

# TERRAIN TILES
class ESRIShadedRelief(cimgt.GoogleWTS):
    def _image_url(self, tile):
        x, y, z = tile
        return (
            f"https://services.arcgisonline.com/ArcGIS/rest/services/"
            f"World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}"
        )

TOPO_TILER = ESRIShadedRelief()
TOPO_ZOOM  = 7

def setup_map(ax, row_i, n_rows):
    ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=PROJ)
    ax.add_image(TOPO_TILER, TOPO_ZOOM, zorder=0)
    ax.add_feature(cfeature.OCEAN,     facecolor="#C8DCF0", zorder=1)
    ax.add_feature(cfeature.LAKES,     facecolor="#C8DCF0", zorder=1, alpha=0.8)
    ax.add_feature(cfeature.STATES,    linewidth=0.6, edgecolor="#333333", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="#111111", zorder=3)
    ax.add_feature(cfeature.BORDERS,   linewidth=0.8, edgecolor="#111111", zorder=3)

    gl = ax.gridlines(draw_labels=False, linewidth=0.3,
                      color="white", linestyle=":", alpha=0.6, zorder=4)
    gl.xlocator = mticker.FixedLocator(range(-124, -113, 2))
    gl.ylocator = mticker.FixedLocator(range(32, 43, 2))

    gl2 = ax.gridlines(draw_labels=True, linewidth=0, color="none", zorder=4)
    gl2.xlocator      = mticker.FixedLocator(range(-124, -113, 4))
    gl2.ylocator      = mticker.FixedLocator(range(32, 43, 4))
    gl2.top_labels    = False
    gl2.right_labels  = False
    gl2.left_labels   = True
    gl2.bottom_labels = (row_i == n_rows - 1)
    gl2.xlabel_style  = {"size": 12, "color": "#222222"}
    gl2.ylabel_style  = {"size": 12, "color": "#222222"}

# LOAD DATA
all_dfs = []
for model_name, filename in test_files.items():
    df = pd.read_csv(filename)
    df["model"] = model_name
    all_dfs.append(df)

data = pd.concat(all_dfs, ignore_index=True)
print(f"Total test rows loaded: {len(data)}")

# COMPUTE SPEARMAN RHO PER STATION × YEAR × MODEL
neg_count = 0

rho_records = []
for model in MODELS:
    sub = data[data["model"] == model]
    for (lat, lon), g in sub.groupby(["latitude", "longitude"]):
        for year in ALL_YEARS:
            g_yr  = g[g["year_local"] == year]
            valid = g_yr[["obs_freq", "pred_freq"]].dropna()

            if len(valid) < MIN_MONTHS:
                continue

            rho, _ = spearmanr(valid["obs_freq"], valid["pred_freq"])

            if rho < 0:
                neg_count += 1

            rho_records.append({
                "model":     model,
                "latitude":  lat,
                "longitude": lon,
                "year":      year,
                "rho":       rho,
            })

rho_df = pd.DataFrame(rho_records)
print(f"\nNegative Spearman rho: {neg_count} station-year instances with rho < 0")

# DRAW ONE FIGURE PER YEAR
n_rows = len(MODELS)

FIGURE_LABELS = {
    2019: "S14",
    2020: "S15",
    2021: "S16",
    2022: "S17",
    2023: "S18",
    2024: "S19",
}

for year in ALL_YEARS:
    yr_df = rho_df[rho_df["year"] == year]

    fig, axes = plt.subplots(
        n_rows, 1,
        figsize=(7, 16),
        subplot_kw={"projection": PROJ},
        gridspec_kw={"hspace": 0.08}
    )
    fig.patch.set_facecolor("#E8E8E6")

    fig.text(
        0.5, 0.965,
        f"Seasonal Fog-Ranking Skill per Station — {year}",
        ha="center", va="bottom", fontsize=18, fontweight="bold", color="#1A1A1A"
    )
    

    for row_i, model in enumerate(MODELS):
        ax = axes[row_i]
        setup_map(ax, row_i, n_rows)

        sub = yr_df[yr_df["model"] == model].dropna(subset=["rho"])

        if len(sub) > 0:
            rho_vals    = sub["rho"].values
            rho_clipped = np.clip(rho_vals, 0.0, 1.0)

            ax.scatter(
                sub["longitude"].values,
                sub["latitude"].values,
                c=rho_clipped,
                cmap=CMAP_RHO, norm=NORM_RHO,
                s=55, alpha=0.92,
                linewidths=0.6,
                edgecolors=[
                    "#FF0000" if r < 0 else "none"
                    for r in rho_vals
                ],
                transform=PROJ, zorder=5
            )

        ax.text(
            -0.18, 0.5, model,
            transform=ax.transAxes,
            fontsize=15, fontweight="600", rotation=90,
            va="center", ha="center",
            color=MODEL_COLORS[model]
        )

    plt.subplots_adjust(left=0.13, right=0.97, top=0.91, bottom=0.10)

    # COLORBAR
    cbar_ax = fig.add_axes([0.20, 0.03, 0.60, 0.028])
    sm = cm.ScalarMappable(cmap=CMAP_RHO, norm=NORM_RHO)
    sm.set_array([])
    cbar = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal",
                        ticks=[0.0, 0.25, 0.5, 0.75, 1.0])
    cbar.set_label(
        "Spearman's ρ  (predicted vs observed monthly fog frequency)",
        fontsize=14, labelpad=6
    )
    cbar.ax.tick_params(labelsize=11)
    cbar.ax.set_xticklabels(["0.00", "0.25", "0.50", "0.75", "1.00"])

    # LEGEND
    legend_handles = [
        mlines.Line2D(
            [], [], marker="o", linestyle="none",
            markerfacecolor="#FFFFFF",
            markeredgecolor="#FF0000",
            markeredgewidth=1.2, markersize=7,
            label="Negative ρ  (clipped to 0 on color scale)"
        ),
    ]
    fig.legend(
        handles=legend_handles,
        loc="lower center",
        bbox_to_anchor=(0.50, -0.06),
        ncol=1, fontsize=11,
        frameon=True, framealpha=0.9,
        edgecolor="#CCCCCC",
        handletextpad=0.2,
    )

    fig_label = FIGURE_LABELS[year]
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

print("\nDone — 6 files written.")
