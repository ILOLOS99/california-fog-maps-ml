library(data.table)
library(ggplot2)
library(ggdendro)

input_path <- "data/combined_stations_era5_CA_2019_2024_features.csv"
out_dir    <- "data"

# LOAD DATA
cat("Loading dataset...\n")
dt <- fread(input_path)
cat("Rows:", nrow(dt), "| Cols:", ncol(dt), "\n")

# DEFINE STATIC VS DYNAMIC 
static_vars <- c(
  "proximity_to_coast_km",
  "slope_30m", "slope_mean_500m", "slope_mean_1000m",
  "northness", "northness_500m", "northness_1000m",
  "eastness",  "eastness_500m",  "eastness_1000m",
  "tpi_500m",  "tpi_1000m",      "tpi_5000m"
)

exclude_cols <- c(
  "station", "station_name", "state", "timezone",
  "year_local", "month_local", "day_local", "hour_local",
  "date_local", "datetime",
  "latitude", "longitude",
  "n_obs", "dew_point_c", "air_temp_c", "wind_speed_ms",
  "precipitation_mm", "cloud_coverage",
  "fog_occurrence", "mist_occurrence",
  "has_dew_point", "has_air_temp", "has_wind_speed",
  "has_precipitation", "has_cloud_coverage", "has_fog_mist_data",
  "leaf_area_index_low_vegetation",
  static_vars
)

numeric_cols <- names(dt)[sapply(dt, is.numeric)]
dynamic_vars <- setdiff(numeric_cols, exclude_cols)

cat("\nStatic vars (", length(static_vars), "):\n")
cat(paste(" -", static_vars, collapse = "\n"), "\n\n")
cat("Dynamic vars (", length(dynamic_vars), "):\n")
cat(paste(" -", dynamic_vars, collapse = "\n"), "\n\n")

# FUNCTION TO PLOT DENDROGRAM
plot_dendrogram <- function(data_subset, var_list, title_text, filename) {
  var_list <- intersect(var_list, names(data_subset))
  cat(paste0("Computing correlation for: ", title_text,
             " (", length(var_list), " vars)...\n"))
  
  # Check for variables that are all NA or have zero variance
  all_na   <- var_list[sapply(var_list, function(v) all(is.na(data_subset[[v]])))]
  zero_var <- var_list[sapply(var_list, function(v) {
    vals <- data_subset[[v]]
    !all(is.na(vals)) && var(vals, na.rm = TRUE) == 0
  })]
  dropped <- union(all_na, zero_var)
  
  if (length(dropped) > 0) {
    cat("  Dropped (all NA or zero variance):\n")
    cat(paste("   -", dropped, collapse = "\n"), "\n")
  } else {
    cat("  No variables dropped.\n")
  }
  
  var_list <- setdiff(var_list, dropped)
  cat(paste0("  Proceeding with ", length(var_list), " vars.\n"))
  
  cor_matrix <- cor(data_subset[, ..var_list], use = "pairwise.complete.obs")
  
  # Drop vars with NA in correlation matrix
  na_cor_vars <- rownames(cor_matrix)[apply(cor_matrix, 1, function(r) any(is.na(r)))]
  if (length(na_cor_vars) > 0) {
    cat("  Dropped (NA in correlation matrix):\n")
    cat(paste("   -", na_cor_vars, collapse = "\n"), "\n")
    var_list   <- setdiff(var_list, na_cor_vars)
    cor_matrix <- cor(data_subset[, ..var_list], use = "pairwise.complete.obs")
  }
  
  dist_matrix <- as.dist(1 - abs(cor_matrix))
  hc          <- hclust(dist_matrix, method = "complete")
  
  p <- ggdendrogram(hc, rotate = TRUE, theme_dendro = FALSE) +
    geom_hline(yintercept = 0.05, color = "red", linetype = "dashed", size = 1) +
    labs(
      title    = paste0("Cluster Dendrogram: ", title_text),
      subtitle = "Red line = 0.95 correlation cutoff. Branches merging below are redundant.",
      x        = "Features",
      y        = "Dissimilarity (1 - |Correlation|)"
    ) +
    theme_minimal() +
    theme(
      axis.text.y        = element_text(size = 10),
      panel.grid.major.y = element_blank()
    )
  
  ggsave(filename, plot = p, width = 14, height = 12, dpi = 300)
  cat(paste0("✓ Saved: ", filename, "\n\n"))
}

# STATIC DENDROGRAM (unique stations only) 
station_df <- unique(dt[, c("station", static_vars), with = FALSE])
plot_dendrogram(station_df, static_vars, "Static Terrain Features",
                file.path(out_dir, "dendrogram_static.png"))

# DYNAMIC DENDROGRAM (full dataset) 
plot_dendrogram(dt, dynamic_vars, "Dynamic ERA5 + Derived Features",
                file.path(out_dir, "dendrogram_dynamic.png"))

cat("\n✓ Done.\n")
