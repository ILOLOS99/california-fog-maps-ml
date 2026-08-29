library(terra)

out_dir <- "."

# Get California's actual state boundary (in lon/lat), then reproject to
# match the raster's CRS (NAD83 / California Albers, EPSG:3310)
if (!requireNamespace("maps", quietly = TRUE)) {
  install.packages("maps", repos = "https://cloud.r-project.org")
}

if (!requireNamespace("sf", quietly = TRUE)) {
  install.packages("sf", repos = "https://cloud.r-project.org")
}

ca_map <- maps::map("state", "california", fill = TRUE, plot = FALSE)
ca_sf  <- sf::st_as_sf(ca_map)
sf::st_crs(ca_sf) <- 4326
ca_boundary_ll <- vect(ca_sf)

# Labels for plot titles
labels <- c(
  dec_2014 = "December 2014",
  aug_2015 = "August 2015"
)

png(
  file.path(out_dir, "figure_6.png"),
  width = 5800,
  height = 3600,
  res = 300
)

layout(matrix(c(1, 3, 2), nrow = 1), widths = c(1, 0.08, 1))
par(mar = c(9, 9, 9, 9) + 0.1, oma = c(2, 2, 2, 2))

for (tag in c("dec_2014", "aug_2015")) {
  
  cat(sprintf("Processing %s...\n", tag))
  
  r <- rast(file.path(out_dir, sprintf("fog_frequency_%s.tif", tag)))
  
  ca_boundary <- project(ca_boundary_ll, crs(r))
  r_crop   <- crop(r, ca_boundary)
  r_masked <- mask(r_crop, ca_boundary)
  r_ll     <- project(r_masked, "EPSG:4326")
  
  plot(
    r_ll,
    main = "",
    xlab = "",
    ylab = "",
    col = hcl.colors(100, "Blues", rev = TRUE),
    axes = TRUE,
    pax = list(cex.axis = 2),
    plg = list(cex = 2.4, size = c(1, 2.5))
  )
  
  mtext(sprintf("Fog Frequency - %s", labels[tag]), side = 3, line = 4, cex = 2.3, font = 2)
  mtext("Longitude", side = 1, line = 4.5, cex = 1.4)
  mtext("Latitude",  side = 2, line = 4.5, cex = 1.4)
  
  cat(sprintf("  Plotted: %s\n", tag))
}

dev.off()
cat("\n=== DONE ===\n")
