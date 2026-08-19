library(elevatr)
library(sf)
library(terra)

# Set your OpenTopography API key
elevatr::set_opentopo_key("YOUR_KEY_HERE")

# California study extent
ca_bbox <- st_as_sfc(
  st_bbox(
    c(
      xmin = -124.5,
      xmax = -114.0,
      ymin = 32.5,
      ymax = 42.0
    ),
    crs = 4326
  )
)

# Download SRTM 1 Arc-Second data
dem <- get_elev_raster(
  locations = ca_bbox,
  src = "gl1",
  clip = "bbox",
  verbose = TRUE
)

# Convert to terra SpatRaster
dem <- rast(dem)

# Reproject to California Albers at 30 m
dem <- project(
  dem,
  "EPSG:3310",
  method = "bilinear",
  res = 30
)

# Remove ocean elevations while retaining valid below-sea-level land
dem <- clamp(
  dem,
  lower = -86,
  values = FALSE
)

# Save processed DEM
writeRaster(
  dem,
  "data/DEM_CA_30m_albers_clean.tif",
  overwrite = TRUE
)

cat("Processed DEM saved to data/DEM_CA_30m_albers_clean.tif\n")
