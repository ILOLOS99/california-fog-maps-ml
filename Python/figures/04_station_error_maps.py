import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt

model_files = {
    "LightGBM":      "LightGBM_with_coords.csv",
    "XGBoost":       "XGBoost_with_coords.csv",
    "Random Forest": "Random Forest_Fixed Hyperparameters_with_coords.csv",
}
MODELS = ["LightGBM", "XGBoost", "Random Forest"]

LON_MIN, LON_MAX = -125.0, -113.5
LAT_MIN, LAT_MAX =   32.0,   42.5
PROJ = ccrs.PlateCarree()

class ESRIShadedRelief(cimgt.GoogleWTS):
    def _image_url(self, tile):
        x, y, z = tile
        return (
            f"https://services.arcgisonline.com/ArcGIS/rest/services/"
            f"World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}"
        )

TOPO_TILER = ESRIShadedRelief()
TOPO_ZOOM  = 7

def setup_map(ax, col_i, row_i, n_rows):
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

    if col_i == 0 or row_i == n_rows - 1:
        gl2 = ax.gridlines(draw_labels=True, linewidth=0, color="none", zorder=4)
        gl2.xlocator      = mticker.FixedLocator(range(-124, -113, 4))
        gl2.ylocator      = mticker.FixedLocator(range(32, 43, 4))
        gl2.top_labels    = False
        gl2.right_labels  = False
        gl2.left_labels   = (col_i == 0)
        gl2.bottom_labels = (row_i == n_rows - 1)
        gl2.xlabel_style  = {"size": 12, "color": "#222222"}
        gl2.ylabel_style  = {"size": 12, "color": "#222222"}

# LOAD DATA
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

data = pd.concat(all_dfs, ignore_index=True)

station_stats = (
    data.groupby(["model", "latitude", "longitude"])["rel_abs_err"]
    .median()
    .reset_index()
)

zero_obs = data[data["obs_freq"] == 0].copy()
station_zero = (
    zero_obs.groupby(["model", "latitude", "longitude"])["pred_freq"]
    .median()
    .reset_index()
)

# COLORMAPS
# Left column: ARE continuous 0-1, solid red above 1
CMAP_ARE = mcolors.LinearSegmentedColormap.from_list(
    "are_cont",
    [(0.0, "#1B6E93"), (0.5, "#F5C97A"), (1.0, "#791F1F")]
)
CMAP_ARE.set_over("#791F1F")
NORM_ARE = mcolors.Normalize(vmin=0.0, vmax=1.0)

# Right column: predicted freq capped at 95th percentile
cap_95 = np.percentile(station_zero["pred_freq"].dropna().values, 95)
print(f"95th pct cap for obs=0 maps: {cap_95:.4f}")

CMAP_ZERO = mcolors.LinearSegmentedColormap.from_list(
    "false_alarm",
    [(0.0, "#FFFFFF"), (0.4, "#F5C97A"), (1.0, "#791F1F")]
)
CMAP_ZERO.set_over("#1A0A0A")
NORM_ZERO = mcolors.Normalize(vmin=0.0, vmax=cap_95)

n_rows = len(MODELS)

# SINGLE FIGURE — 3 rows × 2 columns
# Left col : median ARE (obs > 0)
# Right col: median predicted fog frequency (obs = 0)
fig, axes = plt.subplots(
    n_rows, 2,
    figsize=(10, 13),
    subplot_kw={"projection": PROJ},
    gridspec_kw={"hspace": 0.12, "wspace": 0.08}
)
fig.patch.set_facecolor("#E8E8E6")
plt.subplots_adjust(left=0.13, right=0.97, top=0.88, bottom=0.14)

# Title
fig.text(0.56, 0.955,
         "Station-level Model Error Maps",
         ha="center", va="center", fontsize=18, fontweight="bold", color="#1A1A1A")

# Column headers
COL_TITLES = [
    "Median ARE  (obs > 0)",
    "Median predicted freq  (obs = 0)",
]

# Plot
for row_i, model in enumerate(MODELS):
    sub_are  = station_stats[station_stats["model"] == model]
    sub_zero = station_zero[station_zero["model"] == model]

    for col_i, (sub, cmap, norm) in enumerate([
        (sub_are,  CMAP_ARE,  NORM_ARE),
        (sub_zero, CMAP_ZERO, NORM_ZERO),
    ]):
        val_col = "rel_abs_err" if col_i == 0 else "pred_freq"
        ax = axes[row_i, col_i]
        setup_map(ax, col_i, row_i, n_rows)

        ax.scatter(
            sub["longitude"].values,
            sub["latitude"].values,
            c=sub[val_col].values,
            cmap=cmap, norm=norm,
            s=60, alpha=0.92,
            linewidths=0,
            transform=PROJ, zorder=5
        )

        if row_i == 0:
            ax.set_title(COL_TITLES[col_i], fontsize=14,
                         fontweight="600", pad=6, color="#1A1A1A")

    # Row label
    axes[row_i, 0].text(
        -0.20, 0.5, model,
        transform=axes[row_i, 0].transAxes,
        fontsize=15, fontweight="600", rotation=90,
        va="center", ha="center", color="#1A1A1A"
    )

# Colorbar — left column (ARE, continuous 0-1, red above)
cbar_are_ax = fig.add_axes([0.13, 0.055, 0.35, 0.030])
sm_are = cm.ScalarMappable(cmap=CMAP_ARE, norm=NORM_ARE)
sm_are.set_array([])
tick_vals_are = np.linspace(0, 1.0, 6)
cbar_are = fig.colorbar(sm_are, cax=cbar_are_ax, orientation="horizontal",
                        ticks=tick_vals_are, extend="max")
cbar_are.set_label("Median ARE", fontsize=12, labelpad=6)
cbar_are.ax.set_xticklabels(
    [f"{v:.2f}" for v in tick_vals_are[:-1]] + [">1.00"],
    fontsize=10
)

# Colorbar — right column (predicted freq, continuous)
cbar_zero_ax = fig.add_axes([0.55, 0.055, 0.35, 0.030])
sm_zero = cm.ScalarMappable(cmap=CMAP_ZERO, norm=NORM_ZERO)
sm_zero.set_array([])
tick_vals = np.linspace(0, cap_95, 6)
cbar_zero = fig.colorbar(sm_zero, cax=cbar_zero_ax, orientation="horizontal",
                         ticks=tick_vals, extend="max")
cbar_zero.set_label("Median predicted fog frequency", fontsize=12, labelpad=6)
cbar_zero.ax.tick_params(labelsize=10)
cbar_zero.ax.set_xticklabels(
    [f"{v:.3f}" for v in tick_vals[:-1]] + [f"≥{cap_95:.3f}"],
    fontsize=10
)

fig.savefig(
    "figure_4.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.show()
plt.close()

print("✓ Saved: figure_4.png")
