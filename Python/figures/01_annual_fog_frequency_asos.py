import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.cm as cm
import matplotlib.ticker as mticker
import cartopy.crs as ccrs
import cartopy.feature as cfeature
import cartopy.io.img_tiles as cimgt

data_file = "data/combined_stations_era5_CA_2019_2024_features.csv"

LON_MIN, LON_MAX = -125.0, -113.5
LAT_MIN, LAT_MAX =   32.0,   42.5
PROJ = ccrs.PlateCarree()

# TERRAIN TILES (ESRI World Shaded Relief — grayscale, no API key)
class ESRIShadedRelief(cimgt.GoogleWTS):
    def _image_url(self, tile):
        x, y, z = tile
        return (
            f"https://services.arcgisonline.com/ArcGIS/rest/services/"
            f"World_Shaded_Relief/MapServer/tile/{z}/{y}/{x}"
        )

TOPO_TILER = ESRIShadedRelief()
TOPO_ZOOM  = 7

def setup_map(ax):
    ax.set_extent([LON_MIN, LON_MAX, LAT_MIN, LAT_MAX], crs=PROJ)
    ax.add_image(TOPO_TILER, TOPO_ZOOM, zorder=0)
    ax.add_feature(cfeature.OCEAN,     facecolor="#C8DCF0", zorder=1)
    ax.add_feature(cfeature.LAKES,     facecolor="#C8DCF0", zorder=1, alpha=0.8)
    ax.add_feature(cfeature.STATES,    linewidth=0.6, edgecolor="#333333", zorder=2)
    ax.add_feature(cfeature.COASTLINE, linewidth=0.8, edgecolor="#111111", zorder=3)
    ax.add_feature(cfeature.BORDERS,   linewidth=0.8, edgecolor="#111111", zorder=3)
    gl = ax.gridlines(draw_labels=True, linewidth=0.3,
                      color="white", linestyle=":", alpha=0.6, zorder=4)
    gl.xlocator      = mticker.FixedLocator(range(-124, -113, 2))
    gl.ylocator      = mticker.FixedLocator(range(32, 43, 2))
    gl.top_labels    = False
    gl.right_labels  = False
    gl.xlabel_style  = {"size": 8, "color": "#222222"}
    gl.ylabel_style  = {"size": 8, "color": "#222222"}

# LOAD
df = pd.read_csv(data_file)

df["fog_flag"] = (
    (df["fog_occurrence"]  == "yes") |
    (df["mist_occurrence"] == "yes")
)
df["has_fog_mist_data"] = df["fog_occurrence"].notna()
df["year"]  = df["year_local"]
df["month"] = df["month_local"]

# STRICT QUALITY FILTER: 12 months, each ≥ 90 % complete
monthly = (
    df.groupby(["station", "year", "month"])
    .agg(
        hours_available=("has_fog_mist_data", "count"),
        hours_with_data=("has_fog_mist_data", "sum"),
    )
    .reset_index()
)
monthly["completeness"] = monthly["hours_with_data"] / monthly["hours_available"]
monthly["month_ok"]     = monthly["completeness"] >= 0.90

valid_years = (
    monthly.groupby(["station", "year"])
    .agg(
        months_present=("month", "count"),
        all_months_pass=("month_ok", "all"),
    )
    .reset_index()
)
valid_years = valid_years[
    (valid_years["months_present"] == 12) & valid_years["all_months_pass"]
][["station", "year"]]

print("=" * 60)
print("DATA QUALITY REPORT: STRICT CRITERIA")
print("Criteria: ALL 12 months, each ≥ 90 % complete")
print("=" * 60)
print(f"Station-years passing: {len(valid_years)}")
print(f"Stations passing:      {valid_years['station'].nunique()}\n")

# FOG FREQUENCY
df_valid = df.merge(valid_years, on=["station", "year"])

station_year = (
    df_valid.groupby(["station", "year"])
    .agg(
        hours_with_fog  =("fog_flag",          "sum"),
        hours_available =("has_fog_mist_data",  "sum"),
    )
    .reset_index()
)
station_year["yearly_fog_freq"] = (
    station_year["hours_with_fog"] / station_year["hours_available"]
)

station_avg = (
    station_year.groupby("station")
    .agg(
        avg_yearly_fog_freq=("yearly_fog_freq", "mean"),
        valid_years_count   =("year",            "count"),
    )
    .reset_index()
)

station_meta = (
    df.groupby("station")
    .agg(longitude=("longitude", "first"), latitude=("latitude", "first"))
    .reset_index()
)

stations = station_avg.merge(station_meta, on="station")

print("=" * 60)
print("FOG FREQUENCY STATISTICS")
print("=" * 60)
print(f"Stations in map : {len(stations)}")
print(f"Mean freq       : {stations['avg_yearly_fog_freq'].mean()*100:.1f} %")
print(f"Median freq     : {stations['avg_yearly_fog_freq'].median()*100:.1f} %")
print(f"Range           : {stations['avg_yearly_fog_freq'].min()*100:.1f} % – "
      f"{stations['avg_yearly_fog_freq'].max()*100:.1f} %")

p90       = stations["avg_yearly_fog_freq"].quantile(0.90)
p90_label = f"{p90*100:.1f} %"
print(f"90th pct        : {p90_label}")
print(f"Stations ≥ 90th : {(stations['avg_yearly_fog_freq'] >= p90).sum()}\n")

# COLORMAP
# Viridis-style continuous scale for stations below the 90th percentile;
# stations at or above the 90th percentile plotted as red circles.
CMAP_FOG = plt.get_cmap("viridis")
vmin = stations["avg_yearly_fog_freq"].min()
vmax = p90   # colour scale anchored to 90th pct so high-fog stations don't compress the rest
NORM_FOG = mcolors.Normalize(vmin=vmin, vmax=vmax)

stations_mid  = stations[stations["avg_yearly_fog_freq"] <  p90]
stations_high = stations[stations["avg_yearly_fog_freq"] >= p90]

# FIGURE
fig, ax = plt.subplots(
    figsize=(9, 11),
    subplot_kw={"projection": PROJ}
)
fig.patch.set_facecolor("#E8E8E6")

setup_map(ax)

# stations below 90th pct — viridis colour scale
sc = ax.scatter(
    stations_mid["longitude"].values,
    stations_mid["latitude"].values,
    c=stations_mid["avg_yearly_fog_freq"].values,
    cmap=CMAP_FOG, norm=NORM_FOG,
    s=55, alpha=0.92,
    linewidths=0,
    transform=PROJ, zorder=5,
    label="Fog frequency (< 90th pct)"
)

# stations at or above 90th pct — red dots
ax.scatter(
    stations_high["longitude"].values,
    stations_high["latitude"].values,
    c="red",
    s=55, alpha=0.92,
    linewidths=0,
    transform=PROJ, zorder=6,
    label=f"≥ {p90_label}  (90th pct, red)"
)

# suppress the high-fog entry from legend — colour speaks for itself
ax.get_legend_handles_labels()  # flush

# COLORBAR
sm = cm.ScalarMappable(cmap=CMAP_FOG, norm=NORM_FOG)
sm.set_array([])
cbar = fig.colorbar(sm, ax=ax, orientation="horizontal",
                    extend="max", pad=0.08, fraction=0.03, aspect=40)
cbar.set_label("Annual fog frequency (fraction of hours)", fontsize=11, labelpad=5)
cbar.ax.tick_params(labelsize=10)
tick_vals = np.linspace(vmin, vmax, 6)
cbar.set_ticks(tick_vals)
cbar.ax.set_xticklabels([f"{v*100:.1f} %" for v in tick_vals], fontsize=10)

# LEGEND
import matplotlib.lines as mlines
legend_handles = [
    mlines.Line2D([], [], color="red", marker="o", linestyle="None",
                  markersize=8, label=f"High Fog Frequency (> {p90_label})"),
]
ax.legend(
    handles=legend_handles,
    loc="lower left",
    fontsize=10, framealpha=0.85,
    edgecolor="#CCCCCC", facecolor="white"
)

# TITLES
ax.set_title("")
ax.text(0.0, 1.06,
        "Annual Fog Frequency at California ASOS Stations",
        fontsize=15, fontweight="bold", color="#1A1A1A",
        ha="left", va="bottom", transform=ax.transAxes)
ax.text(0.0, 1.01,
        "Fog frequency = % foggy hours per year, averaged 2019–2024",
        fontsize=12, fontweight="normal", color="#1A1A1A",
        ha="left", va="bottom", transform=ax.transAxes)

fig.savefig("figure_1.png", dpi=300, facecolor=fig.get_facecolor())
plt.close()
print("✓ Saved: figure_1.png")
