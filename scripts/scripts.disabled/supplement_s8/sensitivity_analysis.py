#!/usr/bin/env python3
"""
sensitivity_analysis.py

Recompute contrasts after removing features used in motif rules.

Inputs
------
- data.csv : per-permutation data with metrics as columns
- contrasts.csv : list of contrasts to evaluate
- metric_rule_overlap_table.csv : produced by compute_overlap_table.py

Outputs
-------
- sensitivity_no_rule_features.csv : contrast statistics (cliff's delta, p-values)
  computed on reduced data (rule features removed)
"""
import argparse
import pandas as pd
import numpy as np
from pathlib import Path
from scipy import stats

def cliffs_delta(a, b):
    if len(a)==0 or len(b)==0:
        return np.nan
    u, _ = stats.mannwhitneyu(a, b, alternative='two-sided')
    nA, nB = len(a), len(b)
    return (2.0 * u) / (nA * nB) - 1.0

def main(args):
    df = pd.read_csv(args.data)
    contrasts = pd.read_csv(args.contrasts)
    overlap = pd.read_csv(args.overlap)
    rule_metrics = set(overlap.loc[overlap['tautology_flag']=="Yes", 'metric'].tolist())

    # Build reduced dataframe by dropping rule metrics
    reduced_df = df.drop(columns=[c for c in rule_metrics if c in df.columns], errors='ignore')

    rows = []
    for _, r in contrasts.iterrows():
        metric = r['metric']
        gA = r['groupA']
        gB = r['groupB']
        if metric not in reduced_df.columns:
            rows.append({
                "metric": metric,
                "groupA": gA,
                "groupB": gB,
                "status": "metric_removed_by_rule_filter",
                "cliffs_delta_reduced": np.nan,
                "nA": np.nan,
                "nB": np.nan
            })
            continue
        a = reduced_df.loc[df['primary_label']==gA, metric].dropna().values
        b = reduced_df.loc[df['primary_label']==gB, metric].dropna().values
        cd = cliffs_delta(a, b)
        rows.append({
            "metric": metric,
            "groupA": gA,
            "groupB": gB,
            "status": "computed",
            "cliffs_delta_reduced": cd,
            "nA": len(a),
            "nB": len(b)
        })
    out = pd.DataFrame(rows)
    out.to_csv(Path(args.outdir) / "sensitivity_no_rule_features.csv", index=False)
    print("Wrote:", Path(args.outdir) / "sensitivity_no_rule_features.csv")

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("--data", required=True)
    p.add_argument("--contrasts", required=True)
    p.add_argument("--overlap", required=True)
    p.add_argument("--outdir", default=".")
    args = p.parse_args()
    main(args)