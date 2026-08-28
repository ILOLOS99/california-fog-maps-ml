# Produces: elevation_m, slope_30m, northness, eastness

library(terra)

dem_path <- "DEM_CA_30m_albers_clean.tif"
out_dir  <- "."
tmpdir   <- "terra_tmp"

dir.create(tmpdir, showWarnings = FALSE, recursive = TRUE)

terraOptions(memfrac = 0.8, threads = 16, tempdir = tmpdir)

cat("Loading DEM...\n")
dem <- rast(dem_path)
cat("DEM loaded. Res:", res(dem), "CRS:", crs(dem, describe = TRUE)$code, "\n")

# Output files
elev_file   <- file.path(out_dir, "terrain_elevation_m.tif")
slope30_file <- file.path(out_dir, "terrain_slope_30m.tif")
north_file  <- file.path(out_dir, "terrain_northness.tif")
east_file   <- file.path(out_dir, "terrain_eastness.tif")

# ELEVATION 
cat("Saving elevation_m...\n")
elev <- dem
names(elev) <- "elevation_m"
writeRaster(elev, elev_file, overwrite = TRUE)
rm(elev); gc()
cat("Saved terrain_elevation_m.tif\n")

# SLOPE 30m
cat("Computing slope_30m...\n")
slope_30m <- terrain(dem, v = "slope", unit = "degrees",
                     filename = slope30_file, overwrite = TRUE)
names(slope_30m) <- "slope_30m"
cat("Saved terrain_slope_30m.tif\n")

# NORTHNESS / EASTNESS 
cat("Computing northness and eastness...\n")
aspect_file <- file.path(tmpdir, "aspect_tmp.tif")
aspect <- terrain(dem, v = "aspect", unit = "degrees",
                  filename = aspect_file, overwrite = TRUE)

northness <- cos(aspect * pi / 180)
names(northness) <- "northness"
writeRaster(northness, north_file, overwrite = TRUE)
cat("Saved terrain_northness.tif\n")

eastness <- sin(aspect * pi / 180)
names(eastness) <- "eastness"
writeRaster(eastness, east_file, overwrite = TRUE)
cat("Saved terrain_eastness.tif\n")

rm(dem, slope_30m, aspect, northness, eastness); gc()
unlink(aspect_file)
terra::tmpFiles(remove = TRUE)

cat("\nDone. Produced:\n")
cat("  - terrain_elevation_m.tif\n")
cat("  - terrain_slope_30m.tif\n")
cat("  - terrain_northness.tif\n")
cat("  - terrain_eastness.tif\n")
