import pandas as pd
import matplotlib.pyplot as plt
import numpy as np

# Set publication-ready style
plt.rcParams['font.family'] = 'sans-serif'
plt.rcParams['font.sans-serif'] = ['Arial']
plt.rcParams['font.size'] = 20
plt.rcParams['axes.labelsize'] = 20
plt.rcParams['axes.titlesize'] = 22
plt.rcParams['xtick.labelsize'] = 19
plt.rcParams['ytick.labelsize'] = 19
plt.rcParams['legend.fontsize'] = 20
plt.rcParams['figure.dpi'] = 300

# Load data
lgb_path = "LightGBM_SHAP_Absolute_Values.csv"
xgb_path = "XGBoost_SHAP_Absolute_Values.csv"
rf_path  = "Random Forest_SHAP_importance.csv"

lgb_df = pd.read_csv(lgb_path)
xgb_df = pd.read_csv(xgb_path)
rf_df  = pd.read_csv(rf_path)

# Create ranking columns for XGBoost & LightGBM (rank 1 = highest SHAP value)
xgb_df['Rank_SHAP_Overall'] = xgb_df['Mean_Abs_SHAP_Overall'].rank(ascending=False)
xgb_df['Rank_SHAP_Fog']     = xgb_df['Mean_Abs_SHAP_Fog'].rank(ascending=False)
xgb_df['Rank_SHAP_NonFog']  = xgb_df['Mean_Abs_SHAP_NonFog'].rank(ascending=False)

lgb_df['Rank_SHAP_Overall'] = lgb_df['Mean_Abs_SHAP_Overall'].rank(ascending=False)
lgb_df['Rank_SHAP_Fog']     = lgb_df['Mean_Abs_SHAP_Fog'].rank(ascending=False)
lgb_df['Rank_SHAP_NonFog']  = lgb_df['Mean_Abs_SHAP_NonFog'].rank(ascending=False)

# Model colors 
LGB_COLOR = "#378ADD"   # blue
XGB_COLOR = "#D85A30"   # orange-red
RF_COLOR  = "#1D9E75"   # green

# Feature name map 
def clean_feature_name(name):
    name_map = {
        # Non-engineered — Physiographical
        'elevation_m':              'Elevation',
        'slope_30m':                'Terrain slope 30 m',
        'slope_90m':                'Terrain slope 90 m',
        # Python-style keys
        'slope_500m_mean':          'Terrain slope 500 m mean',
        'slope_2000m_mean':         'Terrain slope 2000 m mean',
        # R-style keys (XGBoost CSV)
        'slope_mean_500m':          'Terrain slope 500 m mean',
        'slope_mean_2000m':         'Terrain slope 2000 m mean',
        'tpi_500m':                 'TPI 500 m',
        'tpi_2000m':                'TPI 2000 m',
        'proximity_to_coast_km':    'Proximity to coast',
        # Aspect — Python-style
        'aspect_sin':               'Aspect sin',
        'aspect_cos':               'Aspect cos',
        # Aspect — R-style (eastness/northness)
        'eastness':                 'Aspect sin',
        'northness':                'Aspect cos',

        # Non-engineered — Climatic
        't2m_C':                                    'Air temperature at 2 m',
        # Dewpoint — Python-style
        'dewpoint':                                 'Dewpoint temperature',
        # Dewpoint — R-style
        'dewpoint_C':                               'Dewpoint temperature',
        # Wind components — Python-style
        'u10m_s':                                   '10-m zonal wind speed',
        'v10m_s':                                   '10-m meridional wind',
        # Wind components — R-style
        'u10_m_s':                                  '10-m zonal wind speed',
        'v10_m_s':                                  '10-m meridional wind',
        'surface_net_solar_radiation_hourly':        'Surface net solar radiation',
        'surface_net_thermal_radiation_hourly':      'Surface net thermal radiation',
        'total_evaporation_hourly':                 'Surface evaporation / ET',
        'total_precipitation_hourly':               'Total precipitation',
        'volumetric_soil_water_layer_1':            'Volumetric soil water (0–7 cm)',
        'skin_temperature':                         'Land-surface temperature',
        'surface_sensible_heat_flux_hourly':        'Surface sensible heat flux',
        'surface_net_solar_radiation_hourly_lag1':  'Surface net solar radiation lag-1',
        'surface_sensible_heat_flux_hourly_lag1':   'Surface sensible heat flux lag-1',
        'total_evaporation_hourly_lag1':            'Surface evaporation / ET lag-1',
        'total_precipitation_hourly_lag1':          'Total precipitation lag-1',

        # Engineered — Temporal
        # Python-style
        'hour_sin':     'Cyclical hour sin',
        'hour_cos':     'Cyclical hour cos',
        'month_sin':    'Cyclical month sin',
        'month_cos':    'Cyclical month cos',
        # R-style
        'sin_hour':     'Cyclical hour sin',
        'cos_hour':     'Cyclical hour cos',
        'sin_month':    'Cyclical month sin',
        'cos_month':    'Cyclical month cos',

        # Engineered — Climatic / Physics-based
        'dewpoint_dep':             'Dewpoint depression',
        'wind_speed':               'Wind speed',
        'vpd_kpa':                  'Vapor pressure deficit',
        'air_skin_diff':            'Air–skin temperature diff.',
        # Wind × dewpoint depression — Python-style
        'wind_x_dewpoint_dep':      'Wind × dewpoint depression',
        # Wind × dewpoint depression — R-style
        'wind_dpdep_interaction':   'Wind × dewpoint depression',
        'cooling_rate_3h':          'Cooling rate (3 h)',
        'moisture_trend_3h':        'Moisture trend (3 h)',
    }
    return name_map.get(name, name)

# FIGURE — Three side-by-side panels: LightGBM | XGBoost | Random Forest

top_n = 15

# LightGBM top features
lgb_top = (lgb_df
           .nsmallest(top_n, 'Rank_SHAP_Overall')
           .sort_values('Mean_Abs_SHAP_Overall', ascending=True)
           .copy())
lgb_top['Feature_Clean'] = lgb_top['Feature'].apply(clean_feature_name)

# XGBoost top features
xgb_top = (xgb_df
           .nsmallest(top_n, 'Rank_SHAP_Overall')
           .sort_values('Mean_Abs_SHAP_Overall', ascending=True)
           .copy())
xgb_top['Feature_Clean'] = xgb_top['Feature'].apply(clean_feature_name)

# Random Forest top features
rf_df['Feature_Clean'] = rf_df['Feature'].apply(clean_feature_name)
rf_top = (rf_df
          .nsmallest(top_n, 'Rank')
          .sort_values('Rank', ascending=False)
          .copy())

# Plot
fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(24, 8))

bar_kw = dict(alpha=0.85, edgecolor='black', linewidth=0.5)

# LightGBM
y1 = np.arange(len(lgb_top))
ax1.barh(y1, lgb_top['Mean_Abs_SHAP_Overall'], color=LGB_COLOR, **bar_kw)
ax1.set_yticks(y1)
ax1.set_yticklabels(lgb_top['Feature_Clean'])
ax1.set_xlabel('Mean Absolute SHAP Value (log-odds)', fontweight='bold')
ax1.set_title('LightGBM', fontweight='bold', pad=12, color=LGB_COLOR)
ax1.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
ax1.spines[['top', 'right']].set_visible(False)

# XGBoost
y2 = np.arange(len(xgb_top))
ax2.barh(y2, xgb_top['Mean_Abs_SHAP_Overall'], color=XGB_COLOR, **bar_kw)
ax2.set_yticks(y2)
ax2.set_yticklabels(xgb_top['Feature_Clean'])
ax2.set_xlabel('Mean Absolute SHAP Value (log-odds)', fontweight='bold')
ax2.set_title('XGBoost', fontweight='bold', pad=12, color=XGB_COLOR)
ax2.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
ax2.spines[['top', 'right']].set_visible(False)

# Random Forest
y3 = np.arange(len(rf_top))
ax3.barh(y3, rf_top['Mean_Abs_SHAP_Average'], color=RF_COLOR, **bar_kw)
ax3.set_yticks(y3)
ax3.set_yticklabels(rf_top['Feature_Clean'])
ax3.set_xlabel('Mean Absolute SHAP Value', fontweight='bold')
ax3.set_title('Random Forest', fontweight='bold', pad=12, color=RF_COLOR)
ax3.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.5)
ax3.spines[['top', 'right']].set_visible(False)

plt.tight_layout()

fig.savefig(
    "figure_7.png",
    dpi=300,
    bbox_inches="tight",
    facecolor="white"
)

plt.show()
plt.close()

print("✓ Saved: figure_7.png")
