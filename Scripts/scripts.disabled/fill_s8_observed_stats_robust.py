import os, glob, pandas as pd, sys, csv

s8_csv = "supplement/S-8/S8_null_samples_summary.csv"
if not os.path.exists(s8_csv):
    print("ERROR: S8 CSV missing:", s8_csv); sys.exit(1)

# map peripheral tag to outdir used earlier
outdirs = {
  "peripheral_85": "motif_results_robustness/peripheral_85_regen_final",
  "peripheral_90": "motif_results_robustness/peripheral_90_regen_final",
  "peripheral_95": "motif_results_robustness/peripheral_95_regen_final"
}

df = pd.read_csv(s8_csv, dtype=str)

# normalize column names to lowercase for flexible lookup
cols = {c.lower(): c for c in df.columns}

# find candidate id column name in the S8 CSV
candidate_col = None
for name in ["candidate_id","candidate","label","id"]:
    if name in cols:
        candidate_col = cols[name]
        break
if candidate_col is None:
    # try to infer candidate column by common patterns
    for c in df.columns:
        if c.lower().startswith("cand") or c.lower().startswith("candidate"):
            candidate_col = c
            break

if candidate_col is None:
    print("WARNING: could not find a candidate id column in", s8_csv)
    print("Columns found:", list(df.columns))
    print("No changes made.")
    sys.exit(0)

# find peripheral column if present
peripheral_col = None
for name in ["peripheral","peripheral_pct","peripheral_tag"]:
    if name in cols:
        peripheral_col = cols[name]
        break

updated = 0
for idx, row in df.iterrows():
    try:
        cid = int(row[candidate_col])
    except Exception:
        # skip rows that do not parse to int
        continue
    tag = row[peripheral_col] if peripheral_col and peripheral_col in df.columns else "peripheral_90"
    od = outdirs.get(tag, tag)
    # search for motif_candidates file in outdir
    cand_file = None
    if os.path.isdir(od):
        # common locations
        candidates_paths = [
            os.path.join(od, "motif_results", "motif_candidates_test.csv"),
            os.path.join(od, "motif_candidates_test.csv"),
            os.path.join(od, "motif_results", "motif_candidates.csv"),
            os.path.join(od, "motif_candidates.csv")
        ]
        for p in candidates_paths:
            if os.path.exists(p):
                cand_file = p
                break
        if cand_file is None:
            # fallback: any motif_candidates*.csv under outdir
            matches = glob.glob(os.path.join(od, "**", "motif_candidates*.csv"), recursive=True)
            if matches:
                cand_file = matches[0]
    else:
        # if od is not a directory, try glob
        matches = glob.glob(od)
        if matches:
            od = matches[0]
            matches2 = glob.glob(os.path.join(od, "**", "motif_candidates*.csv"), recursive=True)
            if matches2:
                cand_file = matches2[0]

    if not cand_file or not os.path.exists(cand_file):
        # nothing found for this row; skip
        continue

    try:
        cdf = pd.read_csv(cand_file, dtype=str)
    except Exception:
        continue

    # try to find the row for this candidate id
    rowmatch = pd.DataFrame()
    # try label column
    for label_col in ["label","candidate","id","idx"]:
        if label_col in cdf.columns:
            rowmatch = cdf[cdf[label_col].astype(str) == str(cid)]
            if not rowmatch.empty:
                break
    if rowmatch.empty:
        # fallback: if candidate id is an index-like position
        try:
            if cid < len(cdf):
                rowmatch = cdf.iloc[[cid]]
        except Exception:
            pass

    if rowmatch.empty:
        continue

    # find a stat column
    stat_val = None
    for stat_col in ["T_obs","T_obs_candidate","stat","observed_stat","statistic","T"]:
        if stat_col in rowmatch.columns:
            stat_val = rowmatch.iloc[0][stat_col]
            break
    # fallback: try any numeric-looking column
    if stat_val is None:
        for c in rowmatch.columns:
            try:
                float(rowmatch.iloc[0][c])
                stat_val = rowmatch.iloc[0][c]
                break
            except Exception:
                continue

    if stat_val is not None:
        df.at[idx, "observed_stat"] = str(stat_val)
        updated += 1

# write back
df.to_csv(s8_csv, index=False)
print("Updated", updated, "observed_stat entries in", s8_csv)
