# Figures

This directory contains Python scripts used to generate figures for the manuscript *“Mapping Fog Frequency in California: A Machine Learning Approach.”*

## Files

- `01_annual_fog_frequency_asos.py` — generates the map of annual fog frequency at California ASOS stations.
- `02_hourly_monthly_fog_patterns.py` — generates hourly and monthly fog-frequency patterns for 2019–2024.
- `03_model_error_boxplots.py` — generates model-performance boxplots using monthly observed and predicted fog frequencies.
- `04_station_error_maps.py` — generates station-level maps of model errors and predictions for station-months with zero observed fog frequency.
- `05_s7-s12_monthly_bias.py` — generates Figure 5 and Supplementary Figures S7–S12, showing monthly prediction residuals for 2019–2024 and their spatial distributions.
- `07_SHAP_comparison.py` — generates Figure 7 comparing SHAP-based feature importance across LightGBM, XGBoost, and Random Forest.
- `08_s24_dewpoint_depression_SHAP.py` — generates Figure 8 and Supplementary Figure S24, showing the relationship between dewpoint depression and SHAP values for LightGBM and XGBoost, respectively.
- `s1-s6_monthly_error_distributions.py` — generates Supplementary Figures S1–S6, showing station-level ARE and predicted fog frequency by month for 2019–2024.
- `s13_spearman_rho_monthly.py` — generates Supplementary Figure S13, showing monthly Spearman’s ρ between observed and predicted fog frequency for LightGBM, XGBoost, and Random Forest.
- `s14-s19_station_year_spearman_rho.py` — generates Supplementary Figures S14–S19, mapping station-level Spearman’s ρ between observed and predicted monthly fog frequency for 2019–2024.

Figures 1 and 2 use the processed feature dataset archived on Zenodo:

**DOI:** https://doi.org/10.5281/zenodo.22050395

Figures 3–5 and Supplementary Figures S1–S19 use the included model-specific monthly prediction CSV files. These are derived from the corresponding `monthly_all_years.csv` outputs from the model evaluation workflows, with station latitude and longitude added; the underlying prediction and observation values were not modified:

- LightGBM: `monthly_all_years.csv` → `LightGBM_with_coords.csv`
- XGBoost: `monthly_all_years.csv` → `XGBoost_with_coords.csv`
- Random Forest: `monthly_all_years.csv` → `Random Forest_Fixed Hyperparameters_with_coords.csv`

Figure 7 uses the included model-specific SHAP importance CSV files. These are renamed copies of outputs produced by the feature-importance analyses in `R/feature_importance/`; the underlying values were not modified:

- LightGBM: `importance_shap_by_class_test.csv` → `LightGBM_SHAP_Absolute_Values.csv`
- XGBoost: `importance_shap_by_class_test.csv` → `XGBoost_SHAP_Absolute_Values.csv`
- Random Forest: `importance_global.csv` → `Random Forest_SHAP_importance.csv`

Figure 8 and Supplementary Figure S24 use the included dewpoint-depression SHAP CSV files. These are renamed copies of outputs produced by the corresponding feature-importance analyses; the underlying values were not modified:

- LightGBM: `dewpoint_dep_beeswarm_test.csv` → `LightGBM_dewpoint_dep_beeswarm.csv`
- XGBoost: `dewpoint_dep_beeswarm_test.csv` → `XGBoost_dewpoint_dep_beeswarm.csv`
