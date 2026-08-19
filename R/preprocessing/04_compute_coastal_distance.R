library(sf)
library(data.table)

input_csv  <- "/home/ilolos/Data to Downscale Fog - AZ & CA/combined_stations_era5_CA_2019_2024_terrain.csv"
output_csv <- "/home/ilolos/Data to Downscale Fog - AZ & CA/combined_stations_era5_CA_2019_2024_terrain_coast.csv"

lon_col <- "longitude"
lat_col <- "latitude"

gshhg_url <- "https://www.soest.hawaii.edu/pwessel/gshhg/gshhg-shp-2.3.7.zip"
gshhg_zip <- "gshhg-shp-2.3.7.zip"
gshhg_shp <- "GSHHS_shp/f/GSHHS_f_L1.shp"


# DOWNLOAD & EXTRACT GSHHG

if (!file.exists(gshhg_shp)) {
  cat("Downloading GSHHG full resolution coastline (~210 MB)...\n")
  if (!file.exists(gshhg_zip)) {
    result <- system(sprintf("wget -O '%s' '%s'", gshhg_zip, gshhg_url))
    if (result != 0) download.file(gshhg_url, gshhg_zip, mode = "wb")
  }
  cat("Extracting...\n")
  system(sprintf("unzip -q '%s'", gshhg_zip))
  cat("✓ Coastline data ready.\n\n")
} else {
  cat("Using existing GSHHG data.\n\n")
}


# LOAD DATA — unique stations only

cat("Loading dataset...\n")
dt <- fread(input_csv)
cat("Total rows: ", nrow(dt), "\n")

unique_stations <- dt[!is.na(get(lon_col)) & !is.na(get(lat_col)),
                      .(longitude = first(get(lon_col)),
                        latitude  = first(get(lat_col))),
                      by = station]
cat("Unique stations: ", nrow(unique_stations), "\n")


# LOAD & PREPARE COASTLINE

cat("\nLoading GSHHG coastline...\n")
coast_raw <- st_read(gshhg_shp, quiet = TRUE)

cat("Cropping to CA region...\n")
bbox <- st_bbox(c(xmin = -125, xmax = -113, ymin = 32, ymax = 42.5), crs = st_crs(4326))
sf_use_s2(FALSE)
coast_crop <- st_crop(coast_raw, bbox)

cat("Projecting to EPSG:3310...\n")
coast_proj <- st_transform(coast_crop, 3310)

cat("Extracting coastline vertices...\n")
coast_lines  <- st_cast(coast_proj, "MULTILINESTRING")


# PROJECT STATION POINTS

cat("Projecting", nrow(unique_stations), "station points...\n")
pts_sf   <- st_as_sf(unique_stations, coords = c("longitude", "latitude"), crs = 4326)
pts_proj <- st_transform(pts_sf, 3310)


# NEAREST COASTLINE DISTANCE

cat("Computing nearest coast distance...\n")
coast_union <- st_union(coast_lines)
dist_m      <- as.numeric(st_distance(pts_proj, coast_union))


# BUILD LOOKUP & MERGE BACK

coast_dt <- data.table(
  station                = unique_stations$station,
  proximity_to_coast_km  = dist_m / 1000
)

cat("\n=== DISTANCE TO COAST SUMMARY ===\n")
cat("Min:    ", round(min(coast_dt$proximity_to_coast_km), 2), "km\n")
cat("Median: ", round(median(coast_dt$proximity_to_coast_km), 2), "km\n")
cat("Mean:   ", round(mean(coast_dt$proximity_to_coast_km), 2), "km\n")
cat("Max:    ", round(max(coast_dt$proximity_to_coast_km), 2), "km\n")

cat("\nMerging back to full dataset...\n")
dt_final <- merge(dt, coast_dt, by = "station", all.x = TRUE)
cat("Final: ", nrow(dt_final), "rows x", ncol(dt_final), "cols\n")


# SAVE

cat("Saving to:\n  ", output_csv, "\n")
fwrite(dt_final, output_csv)
cat("\n✓ COMPLETE\n")
