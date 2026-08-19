# Hourly Model Evaluation

This directory contains the code and supporting files used to evaluate the Random Forest, XGBoost, and LightGBM models at the hourly scale on held-out California stations (test stations).

## Files

- `01_bss_diurnal_seasonal.R` — evaluates 2024 hourly model predictions using the Brier Skill Score (BSS) relative to a diurnal and seasonal climatological baseline derived from 2019–2023 observations.
- `station_splits_random_forest.rds` — Random Forest training/test station split.
- `station_splits_xgboost.rds` — XGBoost training/test station split.
- `station_splits_lightgbm.rds` — LightGBM training/test station split.

The full hourly test-set prediction files used by the evaluation script are archived on Zenodo because of their file size:

**DOI:** https://doi.org/10.5281/zenodo.22018553

Download the three prediction files from the Zenodo archive and place them in the locations specified in `01_bss_diurnal_seasonal.R` before running the evaluation.

## Brier Skill Score Evaluation

The climatological reference probability is calculated separately for each station and hour of day using a ±10-day circular day-of-year window based on observations from 2019–2023.

Stations are included when they have at least three baseline years with ≥90% data completeness and ≥90% completeness during the 2024 evaluation year.

Brier Skill Score is calculated as:

`BSS = 1 - (BS_model / BS_climatology)`

Positive BSS values indicate improved probabilistic predictions relative to the climatological baseline.
