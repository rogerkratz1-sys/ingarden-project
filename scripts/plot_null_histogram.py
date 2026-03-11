#!/usr/bin/env python3
"""
plot_null_histogram.py
Usage:
  python scripts/plot_null_histogram.py --candidate 395260
"""
import argparse
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def main(args):
    repo = Path(args.repo).resolve()
    s8 = repo / "supplement" / "S-8"
    null_df = pd.read_csv(s8 / "S8_null_samples_summary.csv")
    if args.candidate is not None:
        row = null_df[null_df["candidate_id"] == int(args.candidate)]
        if row.empty:
            raise SystemExit(f"No candidate_id {args.candidate} in S8_null_samples_summary.csv")
        row = row.iloc[0]
    else:
        row = null_df.iloc[0]

    t_obs = row["T_obs"]
    percentiles = {k: row[k] for k in ["null_1pct","null_5pct","null_25pct","null_median","null_75pct","null_95pct","null_99pct"] if k in row.index}

    plt.figure(figsize=(8,4))
    # If you have raw null samples, load them and plot histogram here.
    # For now draw percentile lines and observed T
    for name, val in percentiles.items():
        plt.axvline(val, color="gray", linestyle="--", linewidth=1, alpha=0.8)
    plt.axvline(t_obs, color="red", linewidth=2, label=f"T_obs = {t_obs:.2f}")
    plt.xlabel("Test statistic (T)")
    plt.ylabel("Density (illustrative)")
    plt.title(f"Null percentiles and observed T for candidate {int(row['candidate_id'])}")
    plt.legend()
    out = Path(args.out or (s8 / f"fig_null_hist_candidate_{int(row['candidate_id'])}.png"))
    plt.tight_layout()
    plt.savefig(out, dpi=300)
    print("Wrote:", out)

if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--repo", default=".", help="Path to repo root")
    p.add_argument("--candidate", help="candidate_id to plot", required=False)
    p.add_argument("--out", help="output filename (optional)")
    args = p.parse_args()
    main(args)