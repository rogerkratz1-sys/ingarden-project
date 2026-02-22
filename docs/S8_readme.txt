# Supplement S-8 README

**Title**: Supplement S-8 — Type I Error Diagnostic Runbook and Outputs  
**Assembled date**: 2026-02-21  
**Assembler**: local analysis scripts run from `C:\Users\ctint\Desktop\Scripts\repo_candidate`  
**Canonical run folders used**:  
- `C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_85`  
- `C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_90`  
- `C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_95`  

---

## Purpose
This supplement contains the plaintext outputs, run manifests, and reproduction commands for the Type I error diagnostic described in Appendix I. It includes per-candidate null summaries, injection power results, stability diagnostics, and a compact sensitivity table for peripheral cutoffs (p = 85, 90, 95). All files are UTF-8 plain text so they can be hosted directly in the repository.

---

## Files included in supplement/S-8
**Primary supplement files** (place under `supplement/S-8/`):
- **S8_readme.txt** — this README and provenance header.  
- **S8_null_samples_summary.csv** — canonical per-candidate null quantiles and raw p values.  
- **S8_null_histograms.txt** — textual figure captions and per-candidate null summaries.  
- **sensitivity_table_p85_90_95.csv** — compact sensitivity table (one row per candidate per run).  
- **S8_injection_power_curves.txt** — injection results (inject_size, sigma, detection_rate, trials).  
- **S8_stability_matrix.txt** — pairwise Jaccard overlaps across jitter seeds.  
- **S8_methods_equations.txt** — verbatim equations and parameter table (duplicate of Appendix I).  
- **S8_run_commands.txt** — exact commands used to run diagnostics and plotting snippets.

**Canonical run folders** (include these in the repository or provide as linked artifacts):
- `motif_results_robustness/peripheral_85/`  
- `motif_results_robustness/peripheral_90/`  
- `motif_results_robustness/peripheral_95/`  

Each run folder should contain:
- `motif_candidates_test.csv` — candidate table (label, size, stat, center, pval, selected).  
- `meta.json` — run metadata (parameters, B, seed, runtime).  
- `null_samples_candidate_<id>.csv` — raw null samples (recommended).  
- `null_hist_label_<id>.png` — optional histogram images.  
- `run_manifest.json` or `run.log` — run manifest and logs.

---

## What was produced today
Files assembled and written to `C:\Users\ctint\Desktop\Scripts\supplement\S-8\`:
- `S8_readme.txt` (this file)  
- `S8_null_histograms.txt`  
- `sensitivity_table_p85_90_95.csv`  
- `S8_run_commands.txt`  

Scripts created or used (location: `C:\Users\ctint\Desktop\Scripts\repo_candidate`):
- `null_export_direct.py` — exporter: `.npy` → per-candidate CSVs + `S8_null_samples_summary.csv`.  
- `assemble_S8_final.ps1` — PowerShell assembly script to discover run folders and write supplement files.  
- `generate_S8_texts.py` — Python script to generate textual captions and the sensitivity CSV.

---

## How to reproduce the assembly locally
1. Ensure canonical run folders exist under `motif_results_robustness` (peripheral_85, peripheral_90, peripheral_95).  
2. Place the exporter and assembly scripts in `C:\Users\ctint\Desktop\Scripts\repo_candidate`.  
3. Export null samples for each run (example p = 85):
```powershell
python "C:\Users\ctint\Desktop\Scripts\repo_candidate\null_export_direct.py" --npy "C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_85\null_samples_summary.npy" --outdir "C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_85" --run_p 85 --B 1000