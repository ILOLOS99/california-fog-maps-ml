import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.patches import ConnectionPatch
import matplotlib.colors as mcolors
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt
from scipy.stats import linregress


test_files = {
    "LightGBM":      "LightGBM_with_coords.csv",
    "XGBoost":       "XGBoost_with_coords.csv",
    "Random Forest": "Random Forest_Fixed Hyperparameters_with_coords.csv",
}

MODEL_COLORS = {
    "LightGBM":      "#378ADD",
    "XGBoost":       "#D85A30",
    "Random Forest": "#1D9E75",
}

MONTH_LABELS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
                "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

MONTHS    = list(range(1, 13))
MODELS    = ["LightGBM", "XGBoost", "Random Forest"]
ALL_YEARS = [2019, 2020, 2021, 2022, 2023, 2024]

LON_MIN, LON_MAX = -125.0, -113.5
LAT_MIN, LAT_MAX =   32.0,   42.5
PROJ = ccrs.PlateCarree()

# LOAD TEST STATIONS ONLY
all_dfs = []

for model_name in MODELS:
    df = pd.read_csv(test_files[model_name])
    df["model"] = model_name
    all_dfs.append(df)

data = pd.concat(all_dfs, ignore_index=True)

print(f"Total rows loaded: {len(data)}")

# COMPUTE SLOPES AND SLOPE ERROR
def compute_slope(values, years):
    values = np.asarray(values, dtype=float)
    years  = np.asarray(years, dtype=float)

    if len(values) < 3:
        return np.nan

    if np.any(np.isnan(values)) or np.any(np.isnan(years)):
        return np.nan

    return linregress(years, values).slope


slope_records = []

for model in MODELS:
    sub = data[data["model"] == model]

    for (lat, lon), g in sub.groupby(["latitude", "longitude"]):
        for mo in MONTHS:
            sub_mo = g[g["month_local"] == mo]

            yrs_present = list(sub_mo["year_local"].values.astype(int))

            if not all(y in yrs_present for y in ALL_YEARS):
                obs_slope = np.nan
                pred_slope = np.nan
                slope_error = np.nan
                abs_slope_error = np.nan
                squared_slope_error = np.nan

            else:
                sub_6 = (
                    sub_mo[sub_mo["year_local"].isin(ALL_YEARS)]
                    .sort_values("year_local")
                )

                years = sub_6["year_local"].values.astype(float)
                obs   = sub_6["obs_freq"].values.astype(float)
                pred  = sub_6["pred_freq"].values.astype(float)

                obs_slope  = compute_slope(obs, years)
                pred_slope = compute_slope(pred, years)

                if np.isnan(obs_slope) or np.isnan(pred_slope):
                    slope_error = np.nan
                    abs_slope_error = np.nan
                    squared_slope_error = np.nan
                else:
                    slope_error = pred_slope - obs_slope
                    abs_slope_error = abs(slope_error)
                    squared_slope_error = slope_error ** 2

            slope_records.append({
                "model": model,
                "latitude": lat,
                "longitude": lon,
                "month_local": mo,
                "obs_slope": obs_slope,
                "pred_slope": pred_slope,
                "slope_error": slope_error,
                "abs_slope_error": abs_slope_error,
                "squared_slope_error": squared_slope_error,
            })

slope_df = pd.DataFrame(slope_records)

# Convert slope quantities from proportions per year to percentage points per year.
slope_df["obs_slope_pp_per_year"] = slope_df["obs_slope"] * 100
slope_df["pred_slope_pp_per_year"] = slope_df["pred_slope"] * 100
slope_df["slope_error_pp_per_year"] = slope_df["slope_error"] * 100
slope_df["abs_slope_error_pp_per_year"] = slope_df["abs_slope_error"] * 100
slope_df["squared_slope_error_pp_per_year"] = slope_df["slope_error_pp_per_year"] ** 2

# MONTHLY SLOPE MEDIAN ABSOLUTE ERROR PER MODEL × MONTH, IN PERCENTAGE POINTS/YEAR
slope_mae_pp = {}

for model in MODELS:
    sub = slope_df[slope_df["model"] == model]

    for mo in MONTHS:
        sub_mo = sub[sub["month_local"] == mo].dropna(
            subset=["abs_slope_error_pp_per_year"]
        )

        if len(sub_mo) > 0:
            slope_mae_pp[(model, mo)] = sub_mo["abs_slope_error_pp_per_year"].median()
        else:
            slope_mae_pp[(model, mo)] = np.nan


# STATION LIST — NORTHMOST STATIONS APPEAR AT TOP
stations = (
    slope_df[["latitude", "longitude"]]
    .drop_duplicates()
    .sort_values("latitude")
    .reset_index(drop=True)
)

n_stations = len(stations)

station_to_y = {
    (row.latitude, row.longitude): i
    for i, row in stations.iterrows()
}

print(f"Unique stations: {n_stations}")

# COLOR SCALE FOR SLOPE ERROR IN PERCENTAGE POINTS/YEAR
valid_errors_pp = slope_df["slope_error_pp_per_year"].dropna().values

if len(valid_errors_pp) > 0:
    vmax = np.nanpercentile(np.abs(valid_errors_pp), 95)
else:
    vmax = 1.0

if vmax == 0 or np.isnan(vmax):
    vmax = 1.0

norm = mcolors.TwoSlopeNorm(vmin=-vmax, vcenter=0, vmax=vmax)
cmap = plt.get_cmap("RdBu_r")

# TERRAIN TILES
class ESRIShadedRelief(cimgt.GoogleWTS):
    def _image_url(self, tile):
        x, y, z = tile
        return (
            f"https://services.arcgisonline.com/ArcGIS/rest/services/"
            f"World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}"
        )

TOPO_TILER = ESRIShadedRelief()
TOPO_ZOOM  = 9

def setup_map(ax, row_i, n_rows):
    ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=PROJ)

    ax.add_image(TOPO_TILER, TOPO_ZOOM, zorder=0)

    ax.add_feature(cfeature.OCEAN,     facecolor="#C8DCF0", zorder=1)
    ax.add_feature(cfeature.LAKES,     facecolor="#C8DCF0", zorder=1, alpha=0.8)
    ax.add_feature(cfeature.STATES,    linewidth=0.6, edgecolor="#333333", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="#111111", zorder=3)
    ax.add_feature(cfeature.BORDERS,   linewidth=0.8, edgecolor="#111111", zorder=3)

    gl = ax.gridlines(
        draw_labels=True,
        linewidth=0.3,
        color="white",
        linestyle=":",
        alpha=0.5,
        zorder=4
    )

    gl.xlocator      = mticker.FixedLocator(range(-124, -113, 4))
    gl.ylocator      = mticker.FixedLocator(range(32, 43, 4))
    gl.top_labels    = False
    gl.right_labels  = False
    gl.left_labels   = True
    gl.bottom_labels = row_i == n_rows - 1

    gl.xlabel_style  = {"size": 12, "color": "#222222"}
    gl.ylabel_style  = {"size": 12, "color": "#222222"}

# GLYPH ROW DRAWING
CELL_W = 1.0
CELL_H = 0.75

def draw_glyph_row(ax, y_idx, slope_errors_pp_by_month):
    y0 = y_idx - CELL_H / 2.0

    for mo_idx, slope_error_pp in enumerate(slope_errors_pp_by_month):
        x0 = mo_idx * CELL_W

        if pd.isna(slope_error_pp):
            rect = mpatches.Rectangle(
                (x0, y0),
                CELL_W,
                CELL_H,
                facecolor="#E0E0DC",
                edgecolor="#AAAAAA",
                linewidth=0.15,
                hatch="////",
                zorder=3
            )

        else:
            rect = mpatches.Rectangle(
                (x0, y0),
                CELL_W,
                CELL_H,
                facecolor=cmap(norm(slope_error_pp)),
                edgecolor="white",
                linewidth=0.15,
                zorder=3
            )

        ax.add_patch(rect)

# BUILD FIGURE
n_rows = len(MODELS)

fig = plt.figure(figsize=(22, 18))
fig.patch.set_facecolor("#E8E8E6")

LEFT        = 0.07
RIGHT       = 0.97
TOP         = 0.92
BOTTOM      = 0.07
MAP_WIDTH   = 0.42
GLYPH_WIDTH = 0.32
GAP         = 0.01

total_h = TOP - BOTTOM
row_h   = total_h / n_rows
row_pad = 0.012

map_axes   = []
glyph_axes = []

for row_i, model in enumerate(MODELS):
    b = BOTTOM + (n_rows - 1 - row_i) * row_h + row_pad / 2
    h = row_h - row_pad

    map_pos   = [LEFT,                   b, MAP_WIDTH,   h]
    glyph_pos = [LEFT + MAP_WIDTH + GAP, b, GLYPH_WIDTH, h]

    # MAP
    map_ax = fig.add_axes(map_pos, projection=PROJ)

    setup_map(map_ax, row_i, n_rows)

    for _, srow in stations.iterrows():
        map_ax.plot(
            srow.longitude,
            srow.latitude,
            "o",
            color="black",
            markersize=6,
            markeredgewidth=0.8,
            markeredgecolor="white",
            transform=PROJ,
            zorder=5,
            alpha=0.95
        )

    map_ax.text(
        -0.15,
        0.5,
        model,
        transform=map_ax.transAxes,
        fontsize=16,
        fontweight="600",
        rotation=90,
        va="center",
        ha="center",
        color=MODEL_COLORS[model]
    )

    map_axes.append(map_ax)

    # GLYPH PANEL
    glyph_ax = fig.add_axes(glyph_pos)
    glyph_ax.set_facecolor("#F0F0EE")

    for sp in glyph_ax.spines.values():
        sp.set_visible(False)

    glyph_ax.set_xlim(-0.3, 13.5)
    glyph_ax.set_ylim(-3.5, n_stations + 1.2)
    glyph_ax.set_xticks([])
    glyph_ax.set_yticks([])

    for mo_idx, lbl in enumerate(MONTH_LABELS):
        glyph_ax.text(
            mo_idx + 0.5,
            n_stations + 0.5,
            lbl,
            ha="center",
            va="bottom",
            fontsize=13,
            color="#333333",
            fontweight="600"
        )

    sub = slope_df[slope_df["model"] == model]

    for _, srow in stations.iterrows():
        y_idx = station_to_y[(srow.latitude, srow.longitude)]

        s_data = sub[
            (sub["latitude"]  == srow.latitude) &
            (sub["longitude"] == srow.longitude)
        ]

        slope_errors_pp_by_month = []

        for mo in MONTHS:
            row_mo = s_data[s_data["month_local"] == mo]

            if len(row_mo) == 1:
                slope_errors_pp_by_month.append(
                    row_mo["slope_error_pp_per_year"].values[0]
                )
            else:
                slope_errors_pp_by_month.append(np.nan)

        draw_glyph_row(glyph_ax, y_idx, slope_errors_pp_by_month)

    # SUMMARY ROW: SLOPE MAE IN PERCENTAGE POINTS/YEAR
    SUMROW_Y = -2

    glyph_ax.axhline(
        SUMROW_Y + CELL_H / 2 + 0.5,
        color="#888888",
        linewidth=0.8,
        zorder=4
    )

    glyph_ax.text(
        -0.15,
        SUMROW_Y,
        "Slope Median AE\n(pp/yr)",
        ha="right",
        va="center",
        fontsize=8,
        color="#444444",
        style="italic"
    )

    for mo_idx in range(12):
        mo = MONTHS[mo_idx]
        mae_pp = slope_mae_pp[(model, mo)]

        x0 = mo_idx * CELL_W
        y0 = SUMROW_Y - CELL_H / 2

        rect = mpatches.Rectangle(
            (x0, y0),
            CELL_W,
            CELL_H,
            facecolor="#F0F0EE",
            edgecolor="white",
            linewidth=0.15,
            zorder=3
        )

        glyph_ax.add_patch(rect)

        if not np.isnan(mae_pp):
            glyph_ax.text(
                x0 + 0.5,
                SUMROW_Y,
                f"{mae_pp:.1f}",
                ha="center",
                va="center",
                fontsize=8,
                fontweight="600",
                color="#1A1A1A",
                zorder=4
            )

    glyph_axes.append(glyph_ax)

# ARROWS
for row_i, model in enumerate(MODELS):
    map_ax   = map_axes[row_i]
    glyph_ax = glyph_axes[row_i]

    for _, srow in stations.iterrows():
        y_idx = station_to_y[(srow.latitude, srow.longitude)]

        con = ConnectionPatch(
            xyA=(srow.longitude, srow.latitude),
            xyB=(-0.25, y_idx),
            coordsA="data",
            coordsB="data",
            axesA=map_ax,
            axesB=glyph_ax,
            arrowstyle="-|>",
            mutation_scale=10,
            connectionstyle="arc3,rad=0.0",
            color="black",
            linewidth=0.7,
            alpha=0.55,
            zorder=2
        )

        fig.add_artist(con)

# TITLE
fig.text(
    0.5,
    0.965,
    "Slope error between predicted and observed fog-frequency trends, 2019–2024",
    ha="center",
    va="bottom",
    fontsize=22,
    fontweight="bold",
    color="#1A1A1A"
)

# COLORBAR
sm = plt.cm.ScalarMappable(norm=norm, cmap=cmap)
sm.set_array([])

cbar_ax = fig.add_axes([
    LEFT + MAP_WIDTH + GAP + GLYPH_WIDTH + 0.025,
    0.22,
    0.018,
    0.56
])

cbar = fig.colorbar(sm, cax=cbar_ax)

cbar.set_label(
    "Slope error\npercentage points per year\n(predicted slope − observed slope)",
    fontsize=12,
    color="#222222"
)

cbar.ax.tick_params(labelsize=10)

# LEGEND FOR MISSING DATA
missing_handle = mpatches.Patch(
    facecolor="#E0E0DC",
    edgecolor="#AAAAAA",
    linewidth=0.5,
    hatch="////",
    label="Insufficient data"
)

fig.legend(
    handles=[missing_handle],
    loc="lower center",
    ncol=1,
    fontsize=13,
    frameon=True,
    framealpha=0.9,
    edgecolor="#CCCCCC",
    bbox_to_anchor=(0.5, 0.01)
)

# SAVE
fig.savefig(
    "figure_S22.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.show()
plt.close()

print("✓ Saved: figure_S22.png")
