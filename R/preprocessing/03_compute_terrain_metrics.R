library(terra)
library(sf)
library(dplyr)
library(data.table)

input_file  <- "data/combined_stations_era5_CA_2019_2024.csv"
dem_path    <- "data/DEM_CA_30m_albers_clean.tif"
output_file <- "data/combined_stations_era5_CA_2019_2024_terrain.csv"

CA_ALBERS <- "EPSG:3310"

terraOptions(threads = 16)

message("Loading data...")
dt  <- fread(file = input_file)
dem <- rast(dem_path)
message("Rows: ", nrow(dt), " | DEM res: ", round(res(dem)[1], 2), "m")

message("Preparing station locations...")
unique_stations <- dt %>%
  filter(!is.na(longitude), !is.na(latitude)) %>%
  distinct(station, longitude, latitude)
message("Unique stations: ", nrow(unique_stations))

pts_albers <- st_as_sf(unique_stations,
                       coords = c("longitude", "latitude"), crs = 4326) %>%
  st_transform(crs = CA_ALBERS)
pts_v <- vect(pts_albers)

message("Computing terrain derivatives...")
terrain_rast <- terrain(dem, v = c("slope", "aspect"), unit = "degrees")

northness <- cos(terrain_rast[["aspect"]] * pi / 180)
eastness  <- sin(terrain_rast[["aspect"]] * pi / 180)

derivs <- c(terrain_rast[["slope"]], northness, eastness)
names(derivs) <- c("slope", "northness", "eastness")

message("Building buffer geometries...")
poly_500m  <- buffer(pts_v, width = 500)
poly_1000m <- buffer(pts_v, width = 1000)
poly_5000m <- buffer(pts_v, width = 5000)

message("Extracting metrics...")
elev_pt    <- extract(dem,    pts_v,      ID = FALSE)[[1]]
elev_500m  <- extract(dem,    poly_500m,  fun = mean, na.rm = TRUE, ID = FALSE)[[1]]
elev_1000m <- extract(dem,    poly_1000m, fun = mean, na.rm = TRUE, ID = FALSE)[[1]]
elev_5000m <- extract(dem,    poly_5000m, fun = mean, na.rm = TRUE, ID = FALSE)[[1]]

pt_vals   <- extract(derivs, pts_v,      ID = FALSE)
buf_500m  <- extract(derivs, poly_500m,  fun = mean, na.rm = TRUE, ID = FALSE)
buf_1000m <- extract(derivs, poly_1000m, fun = mean, na.rm = TRUE, ID = FALSE)

message("Compiling terrain table...")
terrain_dt <- data.table(
  station = unique_stations$station,
  
  slope_30m        = pt_vals$slope,
  slope_mean_500m  = buf_500m$slope,
  slope_mean_1000m = buf_1000m$slope,
  
  northness        = pt_vals$northness,
  northness_500m   = buf_500m$northness,
  northness_1000m  = buf_1000m$northness,
  
  eastness         = pt_vals$eastness,
  eastness_500m    = buf_500m$eastness,
  eastness_1000m   = buf_1000m$eastness,
  
  tpi_500m         = elev_pt - elev_500m,
  tpi_1000m        = elev_pt - elev_1000m,
  tpi_5000m        = elev_pt - elev_5000m
)

message("Merging and saving...")
dt_final <- merge(dt, terrain_dt, by = "station", all.x = TRUE)
message("Final: ", nrow(dt_final), " rows x ", ncol(dt_final), " cols")
fwrite(dt_final, output_file)

rm(dem, terrain_rast, northness, eastness, derivs,
   pts_v, poly_500m, poly_1000m, poly_5000m)
gc()

message("✓ COMPLETE — saved to:\n  ", output_file)
