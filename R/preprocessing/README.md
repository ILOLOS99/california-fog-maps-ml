# R Preprocessing

These scripts transform the ASOS and ERA5-Land station-level data into the feature dataset used for training and testing the machine learning models downstream.

## Processing Order

Run the scripts in the following order:

1. `01_merge_ERA5_with_ASOS.R`
   - Reads the annual ASOS CSV files from `data/ASOS/`.
   - Reads the monthly ERA5-Land CSV files from year-specific subdirectories under `data/ERA5-Land/` (e.g., `data/ERA5-Land/2019/`).
   - Converts ERA5-Land timestamps from UTC to local California time (`America/Los_Angeles`).
   - Filters both datasets to California stations.
   - Aligns ASOS observations with ERA5-Land data by station, local date, and local hour.
   - Uses the ERA5-Land observations as the hourly temporal framework and joins the corresponding ASOS observations.
   - Produces:
     `data/combined_stations_era5_CA_2019_2024.csv`

2. `02_prepare_DEM.R`
   - Downloads SRTM 1 Arc-Second Global elevation data for the California study region using `elevatr`.
   - Crops the DEM to the California study extent.
   - Reprojects the DEM to NAD83 / California Albers (EPSG:3310) at 30-m spatial resolution using bilinear interpolation.
   - Sets elevations below -86 m to NoData to remove ocean elevations while retaining valid below-sea-level terrestrial elevations in California.
   - Produces:
     `data/DEM_CA_30m_albers_clean.tif`

3. `03_compute_terrain_metrics.R`
   - Reads the merged station-level dataset (`data/combined_stations_era5_CA_2019_2024.csv`).
   - Uses the processed 30-m California DEM (`data/DEM_CA_30m_albers_clean.tif`).
   - Reprojects station coordinates to California Albers (EPSG:3310).
   - Calculates slope, northness, eastness, and topographic position index (TPI) at multiple spatial scales.
   - Produces:
     `data/combined_stations_era5_CA_2019_2024_terrain.csv`

4. `04_compute_coastal_distance.R`
   - Reads the terrain-enhanced dataset (`data/combined_stations_era5_CA_2019_2024_terrain.csv`).
   - Uses the GSHHG coastline dataset.
   - Calculates the distance from each station to the nearest coastline.
   - Produces:
     `data/combined_stations_era5_CA_2019_2024_terrain_coast.csv`

5. `05_feature_engineering.R`
   - Reads the terrain- and coastal-distance-enhanced dataset (`data/combined_stations_era5_CA_2019_2024_terrain_coast.csv`).
   - Derives additional meteorological, temporal, interaction, trend, and lagged features from the ERA5-Land variables.
   - Produces:
     `data/combined_stations_era5_CA_2019_2024_features.csv`

6. `06_feature_correlation_dendrogram.R`
   - Reads the feature dataset (`data/combined_stations_era5_CA_2019_2024_features.csv`).
   - Separates static terrain variables from dynamic variables.
   - Calculates pairwise correlations and hierarchical clustering using `1 - |r|` as the dissimilarity measure.
   - Uses a correlation threshold of `|r| = 0.95` (dissimilarity < 0.05) to identify highly correlated predictor groups.
   - Produces the static and dynamic correlation dendrograms.

## Required Inputs

Before running the preprocessing scripts:

- Extract the six annual ASOS ZIP archives in `data/ASOS/`.
- Generate the ERA5-Land monthly CSV files using the GEE script in `data/ERA5-Land/`.
- Place the ERA5-Land monthly CSV files in year-specific subdirectories under `data/ERA5-Land/` (e.g., `data/ERA5-Land/2019/`).
- Create a free OpenTopography account and request an API key from the [MyOpenTopo dashboard](https://portal.opentopography.org/login).
- Enter the API key in `02_prepare_DEM.R` to enable programmatic download of the SRTM 1 Arc-Second Global DEM (~30 m), which is then reprojected to a 30-m California Albers grid (EPSG:3310).

## DEM Data Source

SRTM Global 1 Arc Second DEM (~30 m).

### Citation

NASA JPL. (2013). *NASA Shuttle Radar Topography Mission Global 1 arc second* [Data set]. NASA EOSDIS Land Processes DAAC. https://doi.org/10.5067/MEaSUREs/SRTM/SRTMGL1.003

Farr, T. G., Rosen, P. A., Caro, E., et al. (2007). The Shuttle Radar Topography Mission. *Reviews of Geophysics, 45*, RG2004. https://doi.org/10.1029/2005RG000183

## Output

The final preprocessing dataset is:

`data/combined_stations_era5_CA_2019_2024_features.csv`

This dataset provides the candidate predictors used for machine learning model development.

The final predictor set is determined using the correlation dendrograms. For feature clusters merging at a dissimilarity below 0.05 (`|r| > 0.95`), one predictor is retained based on physical interpretability and relevance to fog formation.
