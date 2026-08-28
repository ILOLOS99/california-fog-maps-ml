library(terra)
library(sf)
library(rnaturalearth)   # install if needed; requires rnaturalearthhires for scale=10

out_dir <- "."
CA_ALBERS <- "EPSG:3310"
terraOptions(memfrac = 0.8, threads = 16)

coast_file <- file.path(out_dir, "terrain_proximity_to_coast_km.tif")

# Load reference raster for alignment
ref <- rast(file.path(out_dir, "terrain_elevation_m.tif"))

# Get high-res coastline, project to Albers
cat("Loading coastline...\n")
coast <- ne_coastline(scale = 10, returnclass = "sf") |>
  st_transform(CA_ALBERS) |>
  st_crop(st_buffer(st_as_sfc(st_bbox(ref), crs = CA_ALBERS), 100000)) |>
  vect()

# Rasterize coastline onto 30m grid (coastline pixels = 1, rest = NA)
cat("Rasterizing coastline...\n")
coast_rast <- rasterize(coast, ref, field = 1)

# Distance to nearest coastline pixel (meters → km)
cat("Computing distances (this will take a while)...\n")
dist_km <- distance(coast_rast) / 1000
names(dist_km) <- "proximity_to_coast_km"

writeRaster(dist_km, coast_file, overwrite = TRUE)
cat("Done. Saved terrain_proximity_to_coast_km.tif\n")
