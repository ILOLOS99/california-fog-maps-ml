# Produces: slope_mean_500m, northness_500m, eastness_500m, tpi_500m

library(terra)

out_dir <- "."
tmpdir  <- "terra_tmp"

dir.create(tmpdir, showWarnings = FALSE, recursive = TRUE)

terraOptions(memfrac = 0.8, threads = 16, tempdir = tmpdir)

# Output files
slope500_file <- file.path(out_dir, "terrain_slope_mean_500m.tif")
north500_file <- file.path(out_dir, "terrain_northness_500m.tif")
east500_file  <- file.path(out_dir, "terrain_eastness_500m.tif")
tpi500_file   <- file.path(out_dir, "terrain_tpi_500m.tif")

# Build focal window from lightweight raster (same resolution as DEM)
cat("Building 500m focal window...\n")
ref <- rast(file.path(out_dir, "terrain_northness.tif"))
w500 <- focalMat(ref, 500, "circle")
rm(ref); gc()

# SLOPE MEAN 500m
cat("Computing slope_mean_500m...\n")
slope_30m <- rast(file.path(out_dir, "terrain_slope_30m.tif"))
focal(slope_30m, w = w500, fun = "mean", na.rm = TRUE,
      filename = slope500_file, overwrite = TRUE)
rm(slope_30m); gc()
cat("Saved terrain_slope_mean_500m.tif\n")

# NORTHNESS 500m 
cat("Computing northness_500m...\n")
northness <- rast(file.path(out_dir, "terrain_northness.tif"))
focal(northness, w = w500, fun = "mean", na.rm = TRUE,
      filename = north500_file, overwrite = TRUE)
rm(northness); gc()
cat("Saved terrain_northness_500m.tif\n")

# EASTNESS 500m
cat("Computing eastness_500m...\n")
eastness <- rast(file.path(out_dir, "terrain_eastness.tif"))
focal(eastness, w = w500, fun = "mean", na.rm = TRUE,
      filename = east500_file, overwrite = TRUE)
rm(eastness); gc()
cat("Saved terrain_eastness_500m.tif\n")

# TPI 500m 
cat("Computing tpi_500m...\n")
elev <- rast(file.path(out_dir, "terrain_elevation_m.tif"))
elev_mean_500m_file <- file.path(tmpdir, "elev_mean_500m_tmp.tif")
elev_mean <- focal(elev, w = w500, fun = "mean", na.rm = TRUE,
                   filename = elev_mean_500m_file, overwrite = TRUE)
tpi_500m <- elev - elev_mean
names(tpi_500m) <- "tpi_500m"
writeRaster(tpi_500m, tpi500_file, overwrite = TRUE)
rm(elev, elev_mean, tpi_500m); gc()
unlink(elev_mean_500m_file)
cat("Saved terrain_tpi_500m.tif\n")

rm(w500); gc()
terra::tmpFiles(remove = TRUE)

cat("\nDone. Produced:\n")
cat("  - terrain_slope_mean_500m.tif\n")
cat("  - terrain_northness_500m.tif\n")
cat("  - terrain_eastness_500m.tif\n")
cat("  - terrain_tpi_500m.tif\n")
