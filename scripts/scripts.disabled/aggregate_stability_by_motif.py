#!/usr/bin/env python3
# aggregate_stability_by_motif.py
import pandas as pd
import sys
import os

# Config: change if your canonical file has a different name
INPUT_FN = "sensitivity_full_merged.csv"
OUTPUT_FN = "stability_below_0.40_by_motif.csv"
THRESHOLD = 0.40

if not os.path.exists(INPUT_FN):
    sys.exit(f"File not found: {INPUT_FN}")

df = pd.read_csv(INPUT_FN, dtype=str).fillna("")
if "stability_fraction" not in df.columns:
    sys.exit("stability_fraction column not found in CSV")

# ensure numeric
df["stability_fraction"] = pd.to_numeric(df["stability_fraction"], errors="coerce")

# pick motif column (in order of preference)
if "motif_label" in df.columns:
    motif_col = "motif_label"
elif "human_mapped" in df.columns:
    motif_col = "human_mapped"
elif "rule_any_label" in df.columns:
    motif_col = "rule_any_label"
else:
    sys.exit("No motif label column found (expected motif_label or human_mapped or rule_any_label)")

df[motif_col] = df[motif_col].fillna("UNLABELED")

# compute totals and flagged counts
total_per_motif = df.groupby(motif_col).size().reset_index(name="total_rows")
flag_mask = df["stability_fraction"] < THRESHOLD
flagged_per_motif = df[flag_mask].groupby(motif_col).size().reset_index(name="count_below_0.40")

summary = total_per_motif.merge(flagged_per_motif, on=motif_col, how="left").fillna(0)
summary["count_below_0.40"] = summary["count_below_0.40"].astype(int)
summary["fraction_below_0.40"] = summary["count_below_0.40"] / summary["total_rows"]

summary = summary.sort_values("count_below_0.40", ascending=False)

summary.to_csv(OUTPUT_FN, index=False)

print(f"motif_col used: {motif_col}")
print()
print("Rows with stability_fraction < {0:.2f} by motif:".format(THRESHOLD))
print(summary.to_string(index=False))
print()
print(f"Total rows with stability_fraction < {THRESHOLD}: {flag_mask.sum()} (out of {len(df)})")
print(f"Wrote {OUTPUT_FN}")
