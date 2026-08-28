library(terra)

tiles_dir <- "."
out_dir   <- "."

for (tag in c("dec_2014", "aug_2015")) {
  cat(sprintf("Mosaicking %s...\n", tag))
  
  tile_files <- list.files(tiles_dir, pattern = sprintf("fog_tile_%s_.*\\.tif$", tag), full.names = TRUE)
  cat(sprintf("  Found %d tiles\n", length(tile_files)))
  
  tile_rasts <- lapply(tile_files, rast)
  fog_freq   <- do.call(merge, tile_rasts)
  names(fog_freq) <- paste0("fog_frequency_", tag)
  
  out_file <- file.path(out_dir, sprintf("fog_frequency_%s.tif", tag))
  writeRaster(fog_freq, out_file, overwrite = TRUE)
  
  cat(sprintf("  Saved: %s\n", out_file))
}

cat("\n=== DONE ===\n")
