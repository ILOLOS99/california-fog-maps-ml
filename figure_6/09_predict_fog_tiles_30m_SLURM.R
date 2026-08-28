library(terra)
library(lightgbm)
library(ncdf4)
library(future.apply)

# Get tile ID from command line
args    <- commandArgs(trailingOnly = TRUE)
tile_id <- as.integer(args[1])
cat(sprintf("Tile %d starting...\n", tile_id))

# Paths
model_dir <- "../R/models/lightgbm"
terrain_dir <- "."
era5_dir    <- "."
out_dir     <- "."
tmpdir      <- file.path("terra_tmp", sprintf("tile%03d", tile_id))

dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
dir.create(tmpdir,  recursive = TRUE, showWarnings = FALSE)

options(parallelly.maxWorkers.localhost = 4)
options(future.globals.maxSize = 3 * 1024^3)
N_WORKERS     <- 4
TERRA_THREADS <- 1

terraOptions(memfrac = 0.6, threads = TERRA_THREADS, tempdir = tmpdir)

# Model and features
model    <- lgb.load(file.path(model_dir, "lightgbm_model_final.txt"))
features <- readRDS(file.path(model_dir, "session_summary.rds"))$features

terrain_features <- c(
  "proximity_to_coast_km",
  "elevation_m", "slope_30m", "slope_mean_500m",
  "northness", "northness_500m", "northness_1000m",
  "eastness",  "eastness_500m",  "eastness_1000m",
  "tpi_500m",  "tpi_1000m",      "tpi_5000m"
)
era5_features <- features[!features %in% terrain_features]

# Tile extent
ref      <- rast(file.path(terrain_dir, "terrain_elevation_m.tif"))
e        <- ext(ref)
x_breaks <- seq(e[1], e[2], length.out = 17)
y_breaks <- seq(e[3], e[4], length.out = 9)

row      <- ceiling(tile_id / 16)
col      <- tile_id - (row - 1) * 16
tile_ext <- c(x_breaks[col], x_breaks[col+1], y_breaks[row], y_breaks[row+1])

# Worker function
run_worker <- function(worker_id, timestep_idx, tile_ext,
                       arrays, lon, lat, spatial_vars,
                       terrain_dir, tmpdir, features,
                       terrain_features, era5_features,
                       model_path, TERRA_THREADS, tag, tile_id) {
  library(terra)
  library(lightgbm)
  
  wdir <- file.path(tmpdir, paste0("w", worker_id))
  dir.create(wdir, recursive = TRUE, showWarnings = FALSE)
  terraOptions(memfrac = 0.6, threads = TERRA_THREADS, tempdir = wdir)
  
  model <- lgb.load(model_path)
  
  terrain_stack <- c(
    rast(file.path(terrain_dir, "terrain_proximity_to_coast_km.tif")),
    rast(file.path(terrain_dir, "terrain_elevation_m.tif")),
    rast(file.path(terrain_dir, "terrain_slope_30m.tif")),
    rast(file.path(terrain_dir, "terrain_slope_mean_500m.tif")),
    rast(file.path(terrain_dir, "terrain_northness.tif")),
    rast(file.path(terrain_dir, "terrain_northness_500m.tif")),
    rast(file.path(terrain_dir, "terrain_northness_1000m.tif")),
    rast(file.path(terrain_dir, "terrain_eastness.tif")),
    rast(file.path(terrain_dir, "terrain_eastness_500m.tif")),
    rast(file.path(terrain_dir, "terrain_eastness_1000m.tif")),
    rast(file.path(terrain_dir, "terrain_tpi_500m.tif")),
    rast(file.path(terrain_dir, "terrain_tpi_1000m.tif")),
    rast(file.path(terrain_dir, "terrain_tpi_5000m.tif"))
  )
  names(terrain_stack) <- terrain_features
  terrain_stack <- crop(terrain_stack, tile_ext)
  
  t_vals           <- values(terrain_stack, mat = TRUE)
  colnames(t_vals) <- terrain_features
  n_pixels         <- nrow(t_vals)
  
  template <- rast(
    nrows = length(lat), ncols = length(lon),
    xmin  = min(lon) - 0.05, xmax = max(lon) + 0.05,
    ymin  = min(lat) - 0.05, ymax = max(lat) + 0.05,
    crs   = "EPSG:4326"
  )
  
  era5_target <- rast(terrain_stack[[1]])
  fog_sum     <- numeric(n_pixels)
  fog_count   <- integer(n_pixels)
  
  for (i in timestep_idx) {
    tryCatch({
      layers <- lapply(era5_features, function(v) {
        if (v %in% spatial_vars) {
          rast(t(arrays[[v]][, , i]), extent = ext(template), crs = crs(template))
        } else {
          r <- template
          values(r) <- arrays[[v]][i]
          r
        }
      })
      era5_slice        <- rast(layers)
      names(era5_slice) <- era5_features
      era5_30m          <- project(era5_slice, era5_target, method = "near")
      e_vals            <- values(era5_30m, mat = TRUE)
      colnames(e_vals)  <- era5_features
      
      feat_mat <- cbind(t_vals, e_vals)[, features, drop = FALSE]
      preds    <- rep(NA_real_, n_pixels)
      valid    <- complete.cases(feat_mat)
      if (any(valid))
        preds[valid] <- predict(model, feat_mat[valid, , drop = FALSE])
      
      valid_pred            <- !is.na(preds)
      fog_sum[valid_pred]   <- fog_sum[valid_pred]   + preds[valid_pred]
      fog_count[valid_pred] <- fog_count[valid_pred] + 1L
      
    }, error = function(e) {
      cat(sprintf("Worker %d tile %d timestep %d ERROR: %s\n",
                  worker_id, tile_id, i, conditionMessage(e)))
    })
    
    if (i %% 24 == 0) {
      terra::tmpFiles(remove = TRUE)
      gc()
    }
  }
  
  sum_file   <- file.path(tmpdir, sprintf("partial_sum_%s_tile%03d_w%02d.tif", tag, tile_id, worker_id))
  count_file <- file.path(tmpdir, sprintf("partial_count_%s_tile%03d_w%02d.tif", tag, tile_id, worker_id))
  
  fog_sum_rast           <- rast(terrain_stack[[1]])
  values(fog_sum_rast)   <- fog_sum
  fog_count_rast         <- rast(terrain_stack[[1]])
  values(fog_count_rast) <- fog_count
  
  writeRaster(fog_sum_rast,   sum_file,   overwrite = TRUE)
  writeRaster(fog_count_rast, count_file, overwrite = TRUE)
  
  return(list(sum = sum_file, count = count_file))
}

# Main: loop over configs
configs <- list(
  dec_2014 = file.path(era5_dir, "era5_land_dec_2014_features.nc"),
  aug_2015 = file.path(era5_dir, "era5_land_aug_2015_features.nc")
)

for (tag in names(configs)) {
  out_file <- file.path(out_dir, sprintf("fog_tile_%s_%03d.tif", tag, tile_id))
  
  if (file.exists(out_file)) {
    cat(sprintf("Tile %d %s already exists, skipping.\n", tile_id, tag))
    next
  }
  
  cat(sprintf("Processing %s...\n", tag))
  start_time <- Sys.time()
  
  # Load ERA5 ONCE in main process
  nc           <- suppressWarnings(nc_open(configs[[tag]]))
  lon          <- ncvar_get(nc, "longitude")
  lat          <- ncvar_get(nc, "latitude")
  n_times      <- length(ncvar_get(nc, "valid_time"))
  arrays       <- lapply(era5_features, function(v) suppressWarnings(ncvar_get(nc, v)))
  names(arrays) <- era5_features
  nc_close(nc)
  
  spatial_vars <- era5_features[sapply(arrays, function(a) length(dim(a)) == 3)]
  
  worker_idx <- split(seq_len(n_times),
                      cut(seq_len(n_times), N_WORKERS, labels = FALSE))
  
  plan(multisession, workers = N_WORKERS)
  
  results <- future_lapply(
    seq_len(N_WORKERS),
    function(w) run_worker(
      worker_id        = w,
      timestep_idx     = worker_idx[[w]],
      tile_ext         = tile_ext,
      arrays           = arrays,
      lon              = lon,
      lat              = lat,
      spatial_vars     = spatial_vars,
      terrain_dir      = terrain_dir,
      tmpdir           = tmpdir,
      features         = features,
      terrain_features = terrain_features,
      era5_features    = era5_features,
      model_path       = file.path(model_dir, "lightgbm_model_final.txt"),
      TERRA_THREADS    = TERRA_THREADS,
      tag              = tag,
      tile_id          = tile_id
    ),
    future.seed = NULL
  )
  
  plan(sequential)
  
  fog_sum_tile   <- Reduce(`+`, lapply(results, function(r) rast(r$sum)))
  fog_count_tile <- Reduce(`+`, lapply(results, function(r) rast(r$count)))
  fog_freq_tile  <- ifel(fog_count_tile > 0, fog_sum_tile / fog_count_tile, NA)
  
  writeRaster(fog_freq_tile, out_file, overwrite = TRUE)
  unlink(unlist(lapply(results, unlist)))
  terra::tmpFiles(remove = TRUE)
  
  cat(sprintf("Tile %d %s done in %.1f min\n", tile_id, tag,
              as.numeric(difftime(Sys.time(), start_time, units = "mins"))))
}

cat(sprintf("Tile %d complete.\n", tile_id))
