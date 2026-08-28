# Merge ERA5-Land atmospheric and flux data

import xarray as xr

BASE = "."

PAD_TAG = {"dec_2014": "jan01_2015_pad", "aug_2015": "sep01_2015_pad"}

for tag in ["dec_2014", "aug_2015"]:
    print(f"\nMerging {tag}...")

    atmos = xr.open_mfdataset(
        [f"{BASE}/era5_land_{tag}_atmos_CA_extracted/data_0.nc",
         f"{BASE}/era5_land_{PAD_TAG[tag]}_atmos_CA_extracted/data_0.nc"],
        combine="by_coords",
        engine="netcdf4",
        chunks=None,
    )
    
    if tag == "dec_2014":
        atmos = atmos.sel(
            valid_time=(atmos.valid_time.dt.month == 12) |
                       ((atmos.valid_time.dt.month == 1) &
                        (atmos.valid_time.dt.hour <= 7))
        )
    elif tag == "aug_2015":
        atmos = atmos.sel(
            valid_time=(atmos.valid_time.dt.month == 8) |
                       ((atmos.valid_time.dt.month == 9) &
                        (atmos.valid_time.dt.hour <= 6))
        )
        
    flux  = xr.open_dataset(f"{BASE}/era5_land_{tag}_flux_deaccumulated.nc", engine="netcdf4")

    merged = xr.merge([atmos, flux], join="exact")
    print(f"  Variables: {list(merged.data_vars)}")
    print(f"  Timesteps: {len(merged.valid_time)}")

    out_file = f"{BASE}/era5_land_{tag}_merged.nc"
    merged.to_netcdf(out_file)
    print(f"  Saved → {out_file}")

print("\nDone.")
