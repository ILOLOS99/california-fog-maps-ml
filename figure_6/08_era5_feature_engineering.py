import xarray as xr
import numpy as np
import pandas as pd

BASE = "."

for tag in ["dec_2014", "aug_2015"]:
    print(f"\nProcessing {tag}...")

    ds = xr.open_dataset(f"{BASE}/era5_land_{tag}_merged.nc", engine="netcdf4")

    # UNIT CONVERSIONS 
    ds["t2m_C"]                         = ds["t2m"] - 273.15
    ds["dewpoint_C"]                    = ds["d2m"] - 273.15
    ds["u10_m_s"]                       = ds["u10"]
    ds["v10_m_s"]                       = ds["v10"]
    ds["skin_temperature"] = ds["skt"]  # keep in Kelvin
    ds["volumetric_soil_water_layer_1"] = ds["swvl1"]

    # BASIC DERIVED 
    ds["wind_speed"]             = np.sqrt(ds["u10_m_s"]**2 + ds["v10_m_s"]**2)
    ds["dewpoint_dep"]           = ds["t2m_C"] - ds["dewpoint_C"]
    ds["air_skin_diff"]    = ds["t2m_C"] - ds["skin_temperature"]  # °C - K, matches training
    ds["wind_dpdep_interaction"] = ds["wind_speed"] * ds["dewpoint_dep"]

    # VPD 
    A, B = 17.27, 237.7
    es = 0.6108 * np.exp((A * ds["t2m_C"])      / (B + ds["t2m_C"]))
    ea = 0.6108 * np.exp((A * ds["dewpoint_C"])  / (B + ds["dewpoint_C"]))
    ds["vpd_kpa"] = es - ea

    # LAG1 FEATURES (before local time filter)
    lag1_vars = [
        "total_precipitation_hourly",
        "total_evaporation_hourly",
        "surface_net_solar_radiation_hourly",
        "surface_sensible_heat_flux_hourly",
    ]
    time_diff1 = np.concatenate([[np.timedelta64("NaT")],
              np.array(ds.valid_time.values[1:]) - np.array(ds.valid_time.values[:-1])])
    valid1 = xr.DataArray(time_diff1 == np.timedelta64(1, "h"), dims=["valid_time"])

    for v in lag1_vars:
        ds[f"{v}_lag1"] = ds[v].shift(valid_time=1).where(valid1)

    # 3H TREND FEATURES (before local time filter)
    time_diff3 = np.concatenate([[np.timedelta64("NaT")]*3,
              np.array(ds.valid_time.values[3:]) - np.array(ds.valid_time.values[:-3])])
    valid3 = xr.DataArray(time_diff3 == np.timedelta64(3, "h"), dims=["valid_time"])

    t2m_lag3 = ds["t2m_C"].shift(valid_time=3)
    dew_lag3 = ds["dewpoint_C"].shift(valid_time=3)

    ds["cooling_rate_3h"]   = (t2m_lag3 - ds["t2m_C"]).where(valid3)
    ds["moisture_trend_3h"] = (ds["dewpoint_C"] - dew_lag3).where(valid3)

    # UTC → LOCAL TIME + FILTER
    tz_offset = -8 if tag == "dec_2014" else -7
    local_time = pd.DatetimeIndex(ds.valid_time.values) + pd.Timedelta(hours=tz_offset)

    ds = ds.assign(local_time=("valid_time", local_time))

    target_month = 12 if tag == "dec_2014" else 8
    mask = local_time.month == target_month
    ds = ds.isel(valid_time=mask)
    local_time = local_time[mask]
    print(f"  Timesteps after local time filter: {len(ds.valid_time)}")

    # CYCLICAL TIME (use local time)
    hour  = local_time.hour
    month = local_time.month

    ds["sin_hour"]  = ("valid_time", np.sin(2 * np.pi * hour  / 24))
    ds["cos_hour"]  = ("valid_time", np.cos(2 * np.pi * hour  / 24))
    ds["sin_month"] = ("valid_time", np.sin(2 * np.pi * month / 12))
    ds["cos_month"] = ("valid_time", np.cos(2 * np.pi * month / 12))

    # KEEP ONLY MODEL FEATURES
    keep = [
        "t2m_C", "dewpoint_C", "u10_m_s", "v10_m_s", "wind_speed",
        "skin_temperature", "volumetric_soil_water_layer_1",
        "dewpoint_dep", "vpd_kpa", "air_skin_diff", "wind_dpdep_interaction",
        "surface_net_thermal_radiation_hourly",
        "surface_net_solar_radiation_hourly",
        "surface_sensible_heat_flux_hourly",
        "total_evaporation_hourly",
        "total_precipitation_hourly",
        "total_precipitation_hourly_lag1",
        "total_evaporation_hourly_lag1",
        "surface_net_solar_radiation_hourly_lag1",
        "surface_sensible_heat_flux_hourly_lag1",
        "cooling_rate_3h", "moisture_trend_3h",
        "sin_hour", "cos_hour", "sin_month", "cos_month",
        "local_time",
    ]
    ds_out = ds[keep]

    out_file = f"{BASE}/era5_land_{tag}_features.nc"
    ds_out.to_netcdf(out_file)
    print(f"  Saved → {out_file}")
    print(f"  Variables: {list(ds_out.data_vars)}")

print("\nDone.")
