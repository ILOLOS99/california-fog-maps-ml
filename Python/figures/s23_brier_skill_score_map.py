import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt

bss_file = "bss_diurnal_clim_2024.csv"

# MAP EXTENT
LON_MIN, LON_MAX = -124.5, -114.0
LAT_MIN, LAT_MAX =   32.5,   42.0
PROJ = ccrs.PlateCarree()

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

# MODEL ORDERING
MODELS = ["LightGBM", "XGBoost", "RandomForest"]

# LOAD DATA
df = pd.read_csv(bss_file)
df["model"] = pd.Categorical(df["model"], categories=MODELS, ordered=True)


# COLORMAP — symmetric cap at max positive BSS
max_pos = df["bss_overall"].clip(lower=0).max()
cap     = round(max_pos, 2)
print(f"\nColor scale capped symmetrically at ±{cap:.2f}")

CMAP_BSS = mcolors.LinearSegmentedColormap.from_list(
    "bss_rwb",
    [(0.0, "#b2182b"), (0.5, "#ffffff"), (1.0, "#2166ac")]
)
NORM_BSS = mcolors.TwoSlopeNorm(vmin=-cap, vcenter=0.0, vmax=cap)

# MAP SETUP HELPER
def setup_map(ax, col_i, row_i, n_rows, n_cols):
    ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=PROJ)
    ax.add_image(TOPO_TILER, TOPO_ZOOM, zorder=0)
    ax.add_feature(cfeature.OCEAN,     facecolor="#C8DCF0", zorder=1)
    ax.add_feature(cfeature.LAKES,     facecolor="#C8DCF0", zorder=1, alpha=0.8)
    ax.add_feature(cfeature.STATES,    linewidth=0.5, edgecolor="#333333", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.7, edgecolor="#111111", zorder=3)
    ax.add_feature(cfeature.BORDERS,   linewidth=0.7, edgecolor="#111111", zorder=3)

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
        gl2.xlabel_style  = {"size": 11, "color": "#222222"}
        gl2.ylabel_style  = {"size": 11, "color": "#222222"}

# BUILD 3×1 FIGURE (stacked vertically)
n_rows = len(MODELS)
n_cols = 1

fig, axes = plt.subplots(
    n_rows, n_cols,
    figsize=(8, 18),
    subplot_kw={"projection": PROJ},
    gridspec_kw={"hspace": 0.10},
)
fig.patch.set_facecolor("#E8E8E6")

fig.text(0.5, 0.99,
         "Brier Skill Score per ASOS Station — 2024",
         ha="center", va="top", fontsize=20, fontweight="bold", color="#1A1A1A")
fig.text(0.5, 0.972,
         "Test stations",
         ha="center", va="top", fontsize=14, color="#444444")

def squish(v):
    return np.clip(v, -cap, cap)

for row_i, model in enumerate(MODELS):
    ax = axes[row_i]
    setup_map(ax, col_i=0, row_i=row_i, n_rows=n_rows, n_cols=n_cols)

    sub = df[df["model"] == model].dropna(subset=["bss_overall"])

    ax.scatter(
        sub["longitude"].values,
        sub["latitude"].values,
        c=squish(sub["bss_overall"].values),
        cmap=CMAP_BSS, norm=NORM_BSS,
        s=120, alpha=0.90, linewidths=0.8,
        edgecolors="black",
        transform=PROJ, zorder=5
    )

    # Stats annotation
    median_bss  = sub["bss_overall"].median()
    pct_pos     = (sub["bss_overall"] > 0).mean() * 100
    stats_label = f"Median BSS: {median_bss:.3f}\n{pct_pos:.1f}% stations > 0"
    ax.text(
        0.97, 0.97, stats_label,
        transform=ax.transAxes,
        fontsize=13, va="top", ha="right", color="black",
        bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                  edgecolor="gray", alpha=0.8),
        zorder=10
    )

    # Row label (model name)
    label = model.replace("RandomForest", "Random Forest")
    ax.text(-0.14, 0.5, label,
            transform=ax.transAxes,
            fontsize=15, fontweight="600", rotation=90,
            va="center", ha="center", color="#1A1A1A")

# SHARED COLORBAR
cbar_ax = fig.add_axes([0.20, -0.01, 0.60, 0.012])
sm = cm.ScalarMappable(cmap=CMAP_BSS, norm=NORM_BSS)
sm.set_array([])
cbar = fig.colorbar(sm, cax=cbar_ax, orientation="horizontal",
                    ticks=[-cap, -cap/2, 0.0, cap/2, cap])
cbar.set_label("Brier Skill Score", fontsize=14, labelpad=8)
cbar.ax.set_xticklabels(
    [f"< −{cap:.2f}", f"−{cap/2:.2f}", "0.00", f"{cap/2:.2f}", f"> {cap:.2f}"],
    fontsize=12
)

plt.subplots_adjust(left=0.14, right=0.97, top=0.94, bottom=0.04)

# SAVE
fig.savefig(
    "figure_S23.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.show()
plt.close()

print("✓ Saved: figure_S23.png")
