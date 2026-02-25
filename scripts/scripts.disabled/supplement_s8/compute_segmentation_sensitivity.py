#!/usr/bin/env python3
# compute_segmentation_sensitivity.py
# Requires: pandas, numpy
import os
import glob
import pandas as pd
import numpy as np
import argparse

parser = argparse.ArgumentParser()
parser.add_argument("--input_dir", default=r"C:\Users\ctint\Desktop\Scripts\supplement", help="Folder with parse CSVs")
args = parser.parse_args()
INPUT_DIR = args.input_dir
OUTPUT_PERM_CSV = os.path.join(INPUT_DIR, "segmentation_sensitivity_per_permutation.csv")
OUTPUT_SUMMARY_CSV = os.path.join(INPUT_DIR, "segmentation_sensitivity_summary_by_motif.csv")

# discover candidate CSVs that look like parse outputs
all_csvs = sorted(glob.glob(os.path.join(INPUT_DIR, "*.csv")))
candidates = []
for fp in all_csvs:
    try:
        df = pd.read_csv(fp, nrows=1)
        cols = set(df.columns)
        if "permutation_id" in cols and any(c.startswith("flag_") for c in cols):
            candidates.append(fp)
    except Exception:
        continue

if not candidates:
    raise SystemExit(f"No suitable parse CSVs found in {INPUT_DIR}. Expected CSVs with 'permutation_id' and 'flag_' columns.")

print("Discovered parse files:", candidates)

# load parses
parses = {}
for fp in candidates:
    name = os.path.splitext(os.path.basename(fp))[0]
    df = pd.read_csv(fp, dtype={"permutation_id": str})
    flag_cols = [c for c in df.columns if c.startswith("flag_")]
    # ensure flag columns exist and are numeric 0/1
    for c in flag_cols:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0).astype(int)
    parses[name] = df.set_index("permutation_id")

# diagnostic: check for duplicate permutation_id in each parse file
for name, df in parses.items():
    dup_idx = df.index[df.index.duplicated(keep=False)]
    if len(dup_idx) > 0:
        unique_dups = sorted(set(dup_idx))
        print(f"Warning: parse '{name}' has {len(unique_dups)} duplicated permutation_id(s). Examples: {unique_dups[:10]}")
    print(f"{name}: {df.shape[0]} rows, {df.index.nunique()} unique permutation_id")

# ensure common permutation ids
all_ids = set.intersection(*(set(df.index) for df in parses.values()))
if len(all_ids) == 0:
    raise SystemExit("No common permutation_id across discovered parse files.")
all_ids = sorted(all_ids)

# determine motif flag names from union of flag columns
motif_flags = sorted({c for df in parses.values() for c in df.columns if c.startswith("flag_")})
if not motif_flags:
    raise SystemExit("No motif flag columns found in discovered parse files.")

rows = []
for pid in all_ids:
    flags_matrix = []
    primary_labels = []
    for parse_name, df in parses.items():
        raw = df.loc[pid]
        # raw may be a Series (unique index) or DataFrame (duplicates); handle both
        if isinstance(raw, pd.DataFrame):
            row = raw.iloc[0]   # deterministic: take first matching row
        else:
            row = raw
        # build flag vector safely (coerce missing to 0)
        flag_vector = []
        for f in motif_flags:
            val = row.get(f, 0)
            try:
                flag_vector.append(int(val) if pd.notna(val) else 0)
            except Exception:
                flag_vector.append(0)
        flags_matrix.append(flag_vector)
        primary_labels.append(str(row.get("primary_label", "")))
    flags_matrix = np.array(flags_matrix)  # shape (n_parses, n_flags)

    # Compute flag sensitivity per motif: fraction of parses where flag==1
    flag_sens = flags_matrix.mean(axis=0)  # values in [0,1]

    # Determine canonical label: prefer a file named 'multi_label_per_permutation_canonical' if present
    canonical_df = parses.get("multi_label_per_permutation_canonical")
    if canonical_df is None:
        canonical_df = list(parses.values())[0]
        print("Note: 'multi_label_per_permutation_canonical' not found; using first discovered parse as canonical.")
    # safe extraction of canonical_label as scalar
    canonical_raw = canonical_df.loc[pid]
    if isinstance(canonical_raw, pd.DataFrame):
        canonical_label = str(canonical_raw.iloc[0].get("primary_label", ""))
    else:
        canonical_label = str(canonical_raw.get("primary_label", ""))

    # compute primary-label sensitivity (safe scalar comparisons)
    primary_match_frac = sum(1 for lab in primary_labels if lab == canonical_label) / len(primary_labels)

    # Compute multi-label sensitivity: fraction of parses with >1 flag true
    multi_flag_frac = float((flags_matrix.sum(axis=1) > 1).mean())

    # Aggregate row
    rowd = {
        "permutation_id": pid,
        "canonical_primary_label": canonical_label,
        "primary_label_sensitivity": float(primary_match_frac),
        "multi_label_fraction": multi_flag_frac
    }
    for i, f in enumerate(motif_flags):
        rowd[f + "_sensitivity"] = float(flag_sens[i])
    rows.append(rowd)

perm_df = pd.DataFrame(rows).set_index("permutation_id")
perm_df.to_csv(OUTPUT_PERM_CSV)

# Summary by canonical motif
summary_rows = []
for motif in sorted(perm_df["canonical_primary_label"].unique()):
    subset = perm_df[perm_df["canonical_primary_label"] == motif]
    if subset.empty:
        continue
    summary_rows.append({
        "motif": motif,
        "n": len(subset),
        "median_primary_label_sensitivity": float(subset["primary_label_sensitivity"].median()),
        "iqr_primary_label_sensitivity": float(subset["primary_label_sensitivity"].quantile(0.75) - subset["primary_label_sensitivity"].quantile(0.25)),
        "pct_primary_label_sensitivity_ge_0.5": float((subset["primary_label_sensitivity"] >= 0.5).mean()),
        "median_multi_label_fraction": float(subset["multi_label_fraction"].median())
    })

summary_df = pd.DataFrame(summary_rows).set_index("motif")
summary_df.to_csv(OUTPUT_SUMMARY_CSV)

print("Wrote:", OUTPUT_PERM_CSV)
print("Wrote:", OUTPUT_SUMMARY_CSV)