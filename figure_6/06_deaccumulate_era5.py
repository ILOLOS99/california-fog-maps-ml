# ERA5-Land flux de-accumulation

import xarray as xr
import numpy as np

BASE = "."

FLUX_FILES = {
    "dec_2014": {
        "main": f"{BASE}/era5_land_dec_2014_flux_CA_extracted/data_0.nc",
        "pad":  f"{BASE}/era5_land_jan01_2015_pad_flux_CA_extracted/data_0.nc",
    },
    "aug_2015": {
        "main": f"{BASE}/era5_land_aug_2015_flux_CA_extracted/data_0.nc",
        "pad":  f"{BASE}/era5_land_sep01_2015_pad_flux_CA_extracted/data_0.nc",
    },
}

FLUX_VARS = {
    "ssr":  "surface_net_solar_radiation_hourly",
    "str":  "surface_net_thermal_radiation_hourly",
    "sshf": "surface_sensible_heat_flux_hourly",
    "e":    "total_evaporation_hourly",
    "tp":   "total_precipitation_hourly",
}

def deaccumulate(ds):
    out_vars = {}
    for raw, name in FLUX_VARS.items():
        if raw not in ds:
            print(f"  WARNING: {raw} not found, skipping")
            continue
        da = ds[raw]
        hour = da.valid_time.dt.hour
        hourly = xr.where(
            hour == 1,
            da,
            da.diff(dim="valid_time", label="upper").reindex(valid_time=da.valid_time)
        )
        # Load to numpy, fill 00:00 UTC by linear interpolation
        vals = hourly.values  # [time, lat, lon]
        mask = (hour.values == 0)
        for t in np.where(mask)[0]:
            if t > 0 and t < vals.shape[0] - 1:
                vals[t] = (vals[t-1] + vals[t+1]) / 2
        hourly = xr.DataArray(vals, coords=hourly.coords, dims=hourly.dims)
        hourly.name = name
        out_vars[name] = hourly
        print(f"  De-accumulated {raw} → {name}")
    return xr.Dataset(out_vars)

for tag, paths in FLUX_FILES.items():
    print(f"\nProcessing {tag}...")

    ds = xr.open_mfdataset(
    [paths["main"], paths["pad"]],
    combine="by_coords",
    engine="netcdf4",
    chunks=None
    )
    print(f"  Loaded: {len(ds.valid_time)} timesteps")

    ds_hourly = deaccumulate(ds)

    if tag == "dec_2014":
        ds_hourly = ds_hourly.sel(
            valid_time=(ds_hourly.valid_time.dt.month == 12) |
                       ((ds_hourly.valid_time.dt.month == 1) &
                        (ds_hourly.valid_time.dt.hour >= 0) &
                        (ds_hourly.valid_time.dt.hour <= 7))
        )
    elif tag == "aug_2015":
        ds_hourly = ds_hourly.sel(
            valid_time=(ds_hourly.valid_time.dt.month == 8) |
                       ((ds_hourly.valid_time.dt.month == 9) &
                        (ds_hourly.valid_time.dt.hour >= 0) &
                        (ds_hourly.valid_time.dt.hour <= 6))
        )

    out_file = f"{BASE}/era5_land_{tag}_flux_deaccumulated.nc"
    ds_hourly.to_netcdf(out_file)
    print(f"  Saved → {out_file}")
    print(f"  Final timesteps: {len(ds_hourly.valid_time)}")

print("\nDone.")
