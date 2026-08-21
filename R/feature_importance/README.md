# Feature Importance

This directory contains the scripts used to evaluate feature importance for the Random Forest, XGBoost, and LightGBM models.

## Files

- `01_random_forest_shap.R` — computes SHAP-based feature importance for the Random Forest model using `fastshap` and evaluates stability across two runs.
- `02_xgboost_shap.R` — computes native XGBoost SHAP values and built-in gain-based feature importance.
- `03_lightgbm_shap.R` — computes native LightGBM SHAP values and built-in gain-based feature importance.

All analyses use held-out test stations from 2019–2024.

The Random Forest model required by `random_forest_shap.R` is archived on Zenodo:

**DOI:** https://doi.org/10.5281/zenodo.22016730
