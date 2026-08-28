# Produces: terrain_tpi_5000m.tif

library(terra)

out_dir <- "."
tmpdir  <- "terra_tmp"

dir.create(tmpdir, showWarnings = FALSE, recursive = TRUE)
terraOptions(memfrac = 0.8, threads = 16, tempdir = tmpdir)

tpi5000_file <- file.path(out_dir, "terrain_tpi_5000m.tif")

cat("Loading elevation raster...\n")
elev <- rast(file.path(out_dir, "terrain_elevation_m.tif"))
cat("Loaded. Res:", res(elev), "CRS:", crs(elev, describe = TRUE)$code, "\n")

# Step 1: Aggregate to ~240m
cat("Aggregating to 240m...\n")
elev_agg <- aggregate(elev, fact = 8, fun = "mean", na.rm = TRUE,
                      filename = file.path(tmpdir, "elev_agg_tmp.tif"),
                      overwrite = TRUE)
cat("Aggregated res:", res(elev_agg), "\n")

# Step 2: Focal mean at 5000m on small raster
cat("Building 5000m focal window...\n")
w5000 <- focalMat(elev_agg, 5000, "circle")
cat(sprintf("Window size: %d x %d pixels\n", nrow(w5000), ncol(w5000)))

cat("Computing focal mean...\n")
start_time <- Sys.time()
elev_mean_agg <- focal(elev_agg, w = w5000, fun = "mean", na.rm = TRUE,
                       filename = file.path(tmpdir, "elev_mean_agg_tmp.tif"),
                       overwrite = TRUE)
cat(sprintf("Focal mean done in %.1f minutes\n",
            as.numeric(difftime(Sys.time(), start_time, units = "mins"))))

# Step 3: Resample back to 30m
cat("Resampling to 30m...\n")
elev_mean_5000m <- resample(elev_mean_agg, elev, method = "bilinear",
                            filename = file.path(tmpdir, "elev_mean_5000m_tmp.tif"),
                            overwrite = TRUE)

# Step 4: TPI = elev - neighbourhood mean
cat("Computing TPI...\n")
tpi_5000m <- elev - elev_mean_5000m
names(tpi_5000m) <- "tpi_5000m"
writeRaster(tpi_5000m, tpi5000_file, overwrite = TRUE)

rm(elev, elev_agg, elev_mean_agg, elev_mean_5000m, tpi_5000m, w5000); gc()
terra::tmpFiles(remove = TRUE)

cat(sprintf("\nTotal time: %.1f minutes\n",
            as.numeric(difftime(Sys.time(), start_time, units = "mins"))))
cat("Done. Produced:\n  - terrain_tpi_5000m.tif\n")
