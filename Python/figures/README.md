# Figures

This directory contains Python scripts used to generate figures for the manuscript *“Mapping Fog Frequency in California: A Machine Learning Approach.”*

## Files

- `01_annual_fog_frequency_asos.py` — generates the map of annual fog frequency at California ASOS stations.
- `02_hourly_monthly_fog_patterns.py` — generates hourly and monthly fog-frequency patterns for 2019–2024.
- `03_model_error_boxplots.py` — generates model-performance boxplots using monthly observed and predicted fog frequencies.

Figures 1 and 2 use the processed feature dataset archived on Zenodo:

**DOI:** https://doi.org/10.5281/zenodo.22050395

Figure 3 uses the included model-specific monthly prediction CSV files. These are derived from the corresponding `monthly_all_years.csv` model outputs, with station coordinates added.
