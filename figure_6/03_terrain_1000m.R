# Produces: northness_1000m, eastness_1000m, tpi_1000m

library(terra)

out_dir <- "."
tmpdir  <- "terra_tmp"

dir.create(tmpdir, showWarnings = FALSE, recursive = TRUE)

terraOptions(memfrac = 0.8, threads = 16, tempdir = tmpdir)

# Output files
north1000_file <- file.path(out_dir, "terrain_northness_1000m.tif")
east1000_file  <- file.path(out_dir, "terrain_eastness_1000m.tif")
tpi1000_file   <- file.path(out_dir, "terrain_tpi_1000m.tif")

# Build focal window from lightweight raster (same resolution as DEM)
cat("Building 1000m focal window...\n")
ref <- rast(file.path(out_dir, "terrain_northness.tif"))
w1000 <- focalMat(ref, 1000, "circle")
rm(ref); gc()

# NORTHNESS 1000m
cat("Computing northness_1000m...\n")
northness <- rast(file.path(out_dir, "terrain_northness.tif"))
focal(northness, w = w1000, fun = "mean", na.rm = TRUE,
      filename = north1000_file, overwrite = TRUE)
rm(northness); gc()
cat("Saved terrain_northness_1000m.tif\n")

# EASTNESS 1000m
cat("Computing eastness_1000m...\n")
eastness <- rast(file.path(out_dir, "terrain_eastness.tif"))
focal(eastness, w = w1000, fun = "mean", na.rm = TRUE,
      filename = east1000_file, overwrite = TRUE)
rm(eastness); gc()
cat("Saved terrain_eastness_1000m.tif\n")

# TPI 1000m
cat("Computing tpi_1000m...\n")
elev <- rast(file.path(out_dir, "terrain_elevation_m.tif"))
elev_mean_1000m_file <- file.path(tmpdir, "elev_mean_1000m_tmp.tif")
elev_mean <- focal(elev, w = w1000, fun = "mean", na.rm = TRUE,
                   filename = elev_mean_1000m_file, overwrite = TRUE)
tpi_1000m <- elev - elev_mean
names(tpi_1000m) <- "tpi_1000m"
writeRaster(tpi_1000m, tpi1000_file, overwrite = TRUE)
rm(elev, elev_mean, tpi_1000m); gc()
unlink(elev_mean_1000m_file)
cat("Saved terrain_tpi_1000m.tif\n")

rm(w1000); gc()
terra::tmpFiles(remove = TRUE)

cat("\nDone. Produced:\n")
cat("  - terrain_northness_1000m.tif\n")
cat("  - terrain_eastness_1000m.tif\n")
cat("  - terrain_tpi_1000m.tif\n")
