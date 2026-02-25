import os, csv, glob, pandas as pd, sys

s8_csv = "supplement/S-8/S8_null_samples_summary.csv"
if not os.path.exists(s8_csv):
    print("ERROR: S8 CSV missing:", s8_csv); sys.exit(1)

# map peripheral tag to outdir used earlier
outdirs = {
  "peripheral_85": "motif_results_robustness/peripheral_85_regen_final",
  "peripheral_90": "motif_results_robustness/peripheral_90_regen_final",
  "peripheral_95": "motif_results_robustness/peripheral_95_regen_final"
}

# load S8 table
df = pd.read_csv(s8_csv, dtype=str)

# try to find observed stat per peripheral/candidate
for idx, row in df.iterrows():
    tag = row.get("peripheral") or row.get("peripheral_pct") or "peripheral_90"
    cid = int(row["candidate_id"])
    od = outdirs.get(tag, tag)
    cand_file = os.path.join(od, "motif_results", "motif_candidates_test.csv")
    # fallback locations
    if not os.path.exists(cand_file):
        cand_file = os.path.join(od, "motif_candidates_test.csv")
    if not os.path.exists(cand_file):
        # try any motif_candidates file in outdir
        matches = glob.glob(os.path.join(od, "**", "motif_candidates*.csv"), recursive=True)
        cand_file = matches[0] if matches else None
    if cand_file and os.path.exists(cand_file):
        try:
            cdf = pd.read_csv(cand_file)
            # try columns 'label' or 'candidate' and 'stat' or 'T_obs'
            if "label" in cdf.columns:
                rowmatch = cdf[cdf["label"].astype(str)==str(cid)]
            elif "candidate" in cdf.columns:
                rowmatch = cdf[cdf["candidate"].astype(str)==str(cid)]
            else:
                rowmatch = cdf.iloc[[cid]] if cid < len(cdf) else pd.DataFrame()
            if not rowmatch.empty:
                val = None
                for col in ["T_obs","stat","observed_stat","statistic"]:
                    if col in rowmatch.columns:
                        val = rowmatch.iloc[0][col]
                        break
                if val is None:
                    # try 'stat' fallback
                    if "stat" in rowmatch.columns:
                        val = rowmatch.iloc[0]["stat"]
                if val is not None:
                    df.at[idx, "observed_stat"] = str(val)
                    continue
        except Exception:
            pass
    # if we reach here, leave observed_stat as-is
    # optionally try to parse run_log
    # skip for brevity

# write back
df.to_csv(s8_csv, index=False)
print("Updated", s8_csv, "— review observed_stat column for any blanks.")
