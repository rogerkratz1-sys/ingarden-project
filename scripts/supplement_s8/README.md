# Supplement S-8 reproducibility scripts

This folder contains the minimal scripts required to generate the data used in Supplement S-8.

**Purpose**
- Generate null samples and summaries
- Run sensitivity analyses (T_obs vs B)
- Produce the data files consumed by the plotting scripts

**Key scripts**
- compute_features.py -> produces features CSVs (input: raw texts)
- null_export_direct.py / sensitivity_analysis.py -> produce null_samples.csv, Tobs_vs_B.csv, sensitivity_summary.csv
- sensitivity_full*.py, sensitivity_grid.py -> helper/parallel variants
- plot_sensitivity.py -> visualization (already present)

**Inputs**
- ll_scored.csv (or equivalent scoring output)
- config/thresholds.json, config/weights.json
- un_manifest.json

**Outputs**
- 
ull_samples.csv, 
ull_summary.csv, m0_s0_parameters.json
- Tobs_vs_B.csv, sensitivity_summary.csv
- PNG figures (via plotting scripts)

Run the top-level README or MANIFEST.md for the full reproducibility recipe.
