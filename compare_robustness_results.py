#!/usr/bin/env python3
"""
compare_robustness_results.py

Collect motif candidate outputs from multiple robustness runs and produce:
 - summary_compare.csv : concatenated candidate-level table with a 'run' column
 - summary_stats.csv   : one-row-per-run summary (peripheral_pct, peripheral_size, n_candidates, n_selected)

Usage:
  python compare_robustness_results.py --root /path/to/motif_results_robustness --out /path/to/output/summary_compare.csv

If --out is a directory, files will be written into that directory.
"""
import argparse
from pathlib import Path
import pandas as pd
import json
import sys

def find_run_dirs(root: Path):
    # Return immediate subdirectories of root
    return [p for p in sorted(root.iterdir()) if p.is_dir()]

def read_meta(run_dir: Path):
    meta_file = run_dir / "meta.json"
    if meta_file.exists():
        try:
            with open(meta_file, "r", encoding="utf8") as fh:
                return json.load(fh)
        except Exception:
            return {}
    return {}

def read_candidates(run_dir: Path):
    # Try common locations for motif_candidates_test.csv
    candidates_paths = [
        run_dir / "motif_candidates_test.csv",
        run_dir / "motif_results" / "motif_candidates_test.csv"
    ]
    for p in candidates_paths:
        if p.exists():
            try:
                df = pd.read_csv(p)
                return df, p
            except Exception as e:
                raise RuntimeError(f"Failed to read {p}: {e}")
    return None, None

def normalize_df(df: pd.DataFrame):
    # Ensure expected columns exist; keep everything but coerce types where sensible
    # Common columns: label, size, stat, pval, selected, center
    # We'll coerce numeric columns if present
    for col in ["size", "stat", "pval"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")
    if "selected" in df.columns:
        # normalize boolean-like values
        df["selected"] = df["selected"].astype(str).str.lower().map({"true": True, "false": False, "1": True, "0": False}).fillna(df["selected"])
    return df

def main():
    p = argparse.ArgumentParser(description="Compare motif robustness results across runs.")
    p.add_argument("--root", required=True, help="Root folder containing run subfolders (e.g., motif_results_robustness)")
    p.add_argument("--out", required=True, help="Output CSV path or directory for summary_compare.csv and summary_stats.csv")
    args = p.parse_args()

    root = Path(args.root).expanduser().resolve()
    if not root.exists() or not root.is_dir():
        print(f"Error: root folder not found: {root}", file=sys.stderr)
        sys.exit(2)

    out_path = Path(args.out).expanduser().resolve()
    if out_path.is_dir():
        out_dir = out_path
    else:
        # if out is a file, use its parent as directory and keep filename for summary_compare
        out_dir = out_path.parent
        out_dir.mkdir(parents=True, exist_ok=True)

    run_dirs = find_run_dirs(root)
    if not run_dirs:
        print(f"No run subdirectories found under {root}", file=sys.stderr)
        sys.exit(2)

    all_candidates = []
    stats_rows = []

    for run_dir in run_dirs:
        run_name = run_dir.name
        meta = read_meta(run_dir)
        peripheral_pct = meta.get("peripheral_pct") or meta.get("peripheral_pct_used") or meta.get("peripheral_pct_value") or None
        peripheral_size = meta.get("peripheral_size") or meta.get("n_peripheral") or meta.get("peripheral_n") or None

        df, src = read_candidates(run_dir)
        if df is None:
            # no candidate file found; record zero candidates and continue
            stats_rows.append({
                "run": run_name,
                "peripheral_pct": peripheral_pct,
                "peripheral_size": peripheral_size,
                "n_candidates": 0,
                "n_selected": 0,
                "candidates_path": None
            })
            continue

        df = normalize_df(df)
        # add provenance columns
        df.insert(0, "run", run_name)
        df.insert(1, "candidates_path", str(src))
        # if label column missing, create one from index
        if "label" not in df.columns:
            df.insert(2, "label", df.index.astype(str))

        all_candidates.append(df)

        # compute stats
        n_candidates = len(df)
        n_selected = int(df["selected"].sum()) if "selected" in df.columns else 0
        stats_rows.append({
            "run": run_name,
            "peripheral_pct": peripheral_pct,
            "peripheral_size": peripheral_size,
            "n_candidates": n_candidates,
            "n_selected": n_selected,
            "candidates_path": str(src)
        })

    # Concatenate candidate tables
    if all_candidates:
        combined = pd.concat(all_candidates, ignore_index=True, sort=False)
    else:
        combined = pd.DataFrame(columns=["run","candidates_path","label"])

    # Write outputs
    summary_compare_file = out_dir / "summary_compare.csv"
    summary_stats_file = out_dir / "summary_stats.csv"

    combined.to_csv(summary_compare_file, index=False)
    pd.DataFrame(stats_rows).to_csv(summary_stats_file, index=False)

    print(f"Wrote candidate-level summary to: {summary_compare_file}")
    print(f"Wrote per-run stats to: {summary_stats_file}")
    print("Done.")

if __name__ == "__main__":
    main()