#!/usr/bin/env python3
"""
Assemble per-candidate summaries into supplement/S-8/motif_results_robustness/peripheral_95/candidates.csv

Robust to different null-sample file formats and column names.
"""
import os, glob, json
import numpy as np
import pandas as pd

IN_DIR = "motif_results_robustness/peripheral_95"
OUT_DIR = "supplement/S-8/motif_results_robustness/peripheral_95"
os.makedirs(OUT_DIR, exist_ok=True)
out_csv = os.path.join(OUT_DIR, "candidates.csv")

# helper to load null samples from a file
def load_null_samples(path):
    ext = os.path.splitext(path)[1].lower()
    if ext == ".csv":
        df = pd.read_csv(path)
        # candidate column name heuristics
        for col in ["T_null", "T", "T_values", "T_stat", "T_k"]:
            if col in df.columns:
                return df[col].to_numpy(dtype=float)
        # fallback: pick first numeric column
        numeric_cols = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c])]
        if numeric_cols:
            return df[numeric_cols[0]].to_numpy(dtype=float)
        # if single-column CSV with no header, pandas will name it something; try first column anyway
        return df.iloc[:,0].to_numpy(dtype=float)
    elif ext in [".npy", ".npz"]:
        try:
            arr = np.load(path, allow_pickle=True)
            # if npz, get first array
            if isinstance(arr, np.lib.npyio.NpzFile):
                keys = list(arr.keys())
                return arr[keys[0]]
            return arr
        except Exception:
            raise
    else:
        raise ValueError(f"Unsupported null sample file extension: {ext}")

# try to load auxiliary candidate metadata if present
meta_candidates = {}
meta_csv_path = os.path.join(IN_DIR, "candidates_raw.csv")
meta_json_path = os.path.join(IN_DIR, "candidates_meta.json")
if os.path.exists(meta_csv_path):
    try:
        meta_df = pd.read_csv(meta_csv_path)
        for _, r in meta_df.iterrows():
            cid = str(r.get("candidate_id", r.get("id", "")))
            meta_candidates[cid] = {"T_obs": r.get("T_obs", np.nan), "n_points": int(r.get("n_points", -1))}
    except Exception:
        pass
elif os.path.exists(meta_json_path):
    try:
        with open(meta_json_path, "r") as fh:
            meta = json.load(fh)
        for item in meta:
            cid = str(item.get("candidate_id", item.get("id", "")))
            meta_candidates[cid] = {"T_obs": item.get("T_obs", np.nan), "n_points": int(item.get("n_points", -1))}
    except Exception:
        pass

# find null sample files
pattern_csv = os.path.join(IN_DIR, "null_samples_candidate_*.csv")
pattern_npy = os.path.join(IN_DIR, "null_samples_candidate_*.npy")
files = sorted(glob.glob(pattern_csv) + glob.glob(pattern_npy))
if not files:
    print("No null sample files found with patterns:", pattern_csv, pattern_npy)
    print("Check motif_results_robustness/peripheral_95/ for null_samples_candidate_<id>.*")
    raise SystemExit(1)

rows = []
for fpath in files:
    fname = os.path.basename(fpath)
    # extract candidate id from filename
    # supports null_samples_candidate_<id>.csv or null_samples_candidate_<id>_seed.csv
    parts = fname.split("null_samples_candidate_")[-1]
    candidate_id = parts.split(".")[0]
    # load null samples
    try:
        t_null = load_null_samples(fpath)
        t_null = np.asarray(t_null, dtype=float)
    except Exception as e:
        print(f"Skipping {fpath}: failed to load null samples ({e})")
        continue
    # compute null summaries
    null_min = float(np.min(t_null))
    null_1pct = float(np.percentile(t_null, 1))
    null_5pct = float(np.percentile(t_null, 5))
    null_25pct = float(np.percentile(t_null, 25))
    null_median = float(np.percentile(t_null, 50))
    null_75pct = float(np.percentile(t_null, 75))
    null_95pct = float(np.percentile(t_null, 95))
    null_99pct = float(np.percentile(t_null, 99))
    null_max = float(np.max(t_null))
    # try to get observed T and n_points from meta if available
    meta = meta_candidates.get(candidate_id, {})
    T_obs = meta.get("T_obs", np.nan)
    n_points = meta.get("n_points", -1)
    # if T_obs missing, try to find a companion obs file
    obs_path_csv = os.path.join(IN_DIR, f"candidate_obs_{candidate_id}.csv")
    obs_path_json = os.path.join(IN_DIR, f"candidate_obs_{candidate_id}.json")
    if (not pd.isna(T_obs)) and (T_obs is not None):
        pass
    elif os.path.exists(obs_path_csv):
        try:
            odf = pd.read_csv(obs_path_csv)
            T_obs = float(odf.iloc[0].get("T_obs", np.nan))
            n_points = int(odf.iloc[0].get("n_points", n_points))
        except Exception:
            pass
    elif os.path.exists(obs_path_json):
        try:
            with open(obs_path_json, "r") as fh:
                od = json.load(fh)
            T_obs = float(od.get("T_obs", np.nan))
            n_points = int(od.get("n_points", n_points))
        except Exception:
            pass
    # compute raw Monte Carlo p if T_obs available
    if (not pd.isna(T_obs)) and (T_obs is not None):
        raw_p = float((t_null >= float(T_obs)).sum()) / len(t_null)
    else:
        raw_p = float(np.nan)
    rows.append({
        "candidate_id": candidate_id,
        "n_points": n_points,
        "T_obs": T_obs,
        "null_min": null_min,
        "null_1pct": null_1pct,
        "null_5pct": null_5pct,
        "null_25pct": null_25pct,
        "null_median": null_median,
        "null_75pct": null_75pct,
        "null_95pct": null_95pct,
        "null_99pct": null_99pct,
        "null_max": null_max,
        "raw_p_value": raw_p
    })

if not rows:
    print("No candidate rows assembled.")
    raise SystemExit(1)

df_out = pd.DataFrame(rows)
df_out = df_out.sort_values(by="candidate_id")
df_out.to_csv(out_csv, index=False)
print("Wrote", out_csv)