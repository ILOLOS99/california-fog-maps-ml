import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches
import matplotlib.ticker as mticker
from matplotlib.patches import ConnectionPatch
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt
from itertools import combinations


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
MONTHS       = list(range(1, 13))
MODELS       = ["LightGBM", "XGBoost", "Random Forest"]
ALL_YEARS    = [2019, 2020, 2021, 2022, 2023, 2024]

YEAR_PAIRS = list(combinations(ALL_YEARS, 2))   # 15 pairs
N_PAIRS    = len(YEAR_PAIRS)                    # 15

LON_MIN, LON_MAX = -125.0, -113.5
LAT_MIN, LAT_MAX =   32.0,   42.5
PROJ = ccrs.PlateCarree()

# GROUPED HUE COLORMAP
GROUPED_COLORS = {
    0:  "#FFBDBD",
    1:  "#F06060",
    2:  "#C0131C",
    3:  "#FDDCB5",
    4:  "#F5A44A",
    5:  "#C96A0A",
    6:  "#FFF3A3",
    7:  "#F5D000",
    8:  "#A88C00",
    9:  "#B6ECD8",
    10: "#3DBD8A",
    11: "#0A7A55",
    12: "#BDDEFF",
    13: "#3D88E0",
    14: "#0A3A8C",
    15: "#000033",
}

# LOAD TEST STATIONS ONLY
all_dfs = []

for model_name in MODELS:
    df = pd.read_csv(test_files[model_name])
    df["model"] = model_name
    all_dfs.append(df)

data = pd.concat(all_dfs, ignore_index=True)
print(f"Total rows loaded: {len(data)}")

# COMPUTE KENDALL CONCORDANT PAIRS
def kendall_concordant(pred_dict, obs_dict):
    if any(y not in pred_dict or y not in obs_dict for y in ALL_YEARS):
        return np.nan

    n_conc = 0

    for yi, yj in YEAR_PAIRS:
        p_dir = np.sign(pred_dict[yj] - pred_dict[yi])
        o_dir = np.sign(obs_dict[yj]  - obs_dict[yi])

        if o_dir == 0 and p_dir == 0:
            n_conc += 1
        elif o_dir != 0 and p_dir != 0 and o_dir == p_dir:
            n_conc += 1

    return n_conc

kendall_records = []

for model in MODELS:
    sub = data[data["model"] == model]

    for (lat, lon), g in sub.groupby(["latitude", "longitude"]):
        for mo in MONTHS:
            sub_mo = g[g["month_local"] == mo]

            pred_dict = dict(zip(
                sub_mo["year_local"].astype(int),
                sub_mo["pred_freq"].astype(float)
            ))

            obs_dict = dict(zip(
                sub_mo["year_local"].astype(int),
                sub_mo["obs_freq"].astype(float)
            ))

            kendall_records.append({
                "model":        model,
                "latitude":     lat,
                "longitude":    lon,
                "month_local":  mo,
                "n_concordant": kendall_concordant(pred_dict, obs_dict),
            })

kendall_df = pd.DataFrame(kendall_records)

# STATION LIST — NORTHMOST STATIONS APPEAR AT TOP
stations = (
    kendall_df[["latitude", "longitude"]]
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

#GLYPH ROW DRAWING
CELL_W = 1.0
CELL_H = 0.75

def draw_glyph_row(ax, y_idx, n_concordant_by_month):
    y0 = y_idx - CELL_H / 2.0

    for mo_idx, n in enumerate(n_concordant_by_month):
        x0 = mo_idx * CELL_W

        if pd.isna(n):
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
            ax.add_patch(rect)
        else:
            n_int = int(round(n))
            face_col = GROUPED_COLORS[n_int]

            rect = mpatches.Rectangle(
                (x0, y0),
                CELL_W,
                CELL_H,
                facecolor=face_col,
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
    glyph_ax.set_ylim(-2.8, n_stations + 1.2)
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

    sub = kendall_df[kendall_df["model"] == model]

    for _, srow in stations.iterrows():
        y_idx = station_to_y[(srow.latitude, srow.longitude)]

        s_data = sub[
            (sub["latitude"] == srow.latitude) &
            (sub["longitude"] == srow.longitude)
        ]

        n_by_month = []

        for mo in MONTHS:
            row_mo = s_data[s_data["month_local"] == mo]

            if len(row_mo) == 1:
                n_by_month.append(row_mo["n_concordant"].values[0])
            else:
                n_by_month.append(np.nan)

        draw_glyph_row(glyph_ax, y_idx, n_by_month)

    # Separator between station rows and median row
    glyph_ax.axhline(
        -0.9,
        color="#AAAAAA",
        linewidth=0.8,
        linestyle="--",
        zorder=2
    )

    # Median row
    MEDIAN_Y = -1.8

    for mo_idx, mo in enumerate(MONTHS):
        mo_vals = kendall_df[
            (kendall_df["model"] == model) &
            (kendall_df["month_local"] == mo)
        ]["n_concordant"].dropna().values

        if len(mo_vals) == 0:
            continue

        n_int = int(round(np.median(mo_vals)))
        color = GROUPED_COLORS[n_int]

        rect = mpatches.Rectangle(
            (mo_idx * CELL_W, MEDIAN_Y),
            CELL_W,
            CELL_H,
            facecolor=color,
            edgecolor="white",
            linewidth=0.3,
            zorder=3
        )

        glyph_ax.add_patch(rect)

    glyph_ax.text(
        -0.35,
        MEDIAN_Y + CELL_H / 2,
        "Median",
        ha="right",
        va="center",
        fontsize=12,
        color="#333333",
        fontweight="600"
    )

    glyph_axes.append(glyph_ax)

# ARROWS FROM MAP STATIONS TO GLYPH ROWS
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
    "Pairwise directional agreement in predicted fog frequency across years",
    ha="center",
    va="bottom",
    fontsize=22,
    fontweight="bold",
    color="#1A1A1A"
)

# LEGEND
handles = []

for v in range(16):
    handles.append(
        mpatches.Patch(
            facecolor=GROUPED_COLORS[v],
            edgecolor="#555555",
            linewidth=0.5,
            label=str(v)
        )
    )

handles.append(
    mpatches.Patch(
        facecolor="#E0E0DC",
        edgecolor="#AAAAAA",
        linewidth=0.5,
        hatch="////",
        label="Insufficient data"
    )
)

fig.legend(
    handles=handles,
    loc="lower center",
    ncol=len(handles),
    fontsize=10,
    frameon=True,
    framealpha=0.9,
    edgecolor="#CCCCCC",
    title=(
        "Concordant year-pairs out of 15  |  "
        "color families: 0–2 red · 3–5 orange · "
        "6–8 yellow · 9–11 teal · 12–14 blue · 15 navy"
    ),
    title_fontsize=10,
    bbox_to_anchor=(0.5, 0.005)
)

# SAVE
fig.savefig(
    "figure_S21.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.show()
plt.close()

print("✓ Saved: figure_S21.png")
