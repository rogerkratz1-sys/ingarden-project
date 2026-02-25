#!/usr/bin/env python3
r"""
null_export_direct.py

Robust exporter: reads a null_samples_summary .npy archive and writes:
 - null_samples_candidate_<id>.csv  (one file per candidate)
 - S8_null_samples_summary.csv      (one summary CSV with quantiles and p-values)

Usage example:
  python null_export_direct.py --npy "C:\path\to\null_samples_summary.npy" --outdir "C:\path\to\outdir" --run_p 95 --B 1000
"""
from pathlib import Path
import argparse
import numpy as np
import pandas as pd
import sys

def load_npy(path):
    arr = np.load(path, allow_pickle=True)
    # Convert numpy scalar/array to Python list/dict where appropriate
    try:
        return arr.tolist()
    except Exception:
        return arr

def normalize_entries(arr):
    entries = []
    # If arr is a dict mapping candidate_id -> samples
    if isinstance(arr, dict):
        for cid, samples in arr.items():
            samples = np.asarray(samples)
            entries.append({'candidate_id': int(cid), 'null_samples': samples, 'T_obs': float(np.max(samples)) if samples.size else 0.0, 'n_points': int(samples.size)})
        return entries

    # If arr is list-like
    if hasattr(arr, '__iter__') and not isinstance(arr, (str, bytes)):
        for item in arr:
            if item is None:
                continue
            if isinstance(item, dict):
                cid = item.get('candidate_id') or item.get('label') or item.get('id')
                samples = np.asarray(item.get('null_samples') or item.get('T_null') or item.get('samples') or [])
                T_obs = item.get('T_obs') or item.get('T_obs_value') or (samples.max() if samples.size else 0.0)
                n_points = item.get('n_points') or item.get('size') or samples.size
                if cid is None:
                    # try to infer from index if present
                    cid = item.get('index') or item.get('idx')
                entries.append({'candidate_id': int(cid), 'null_samples': samples, 'T_obs': float(T_obs), 'n_points': int(n_points)})
            elif isinstance(item, (list, tuple)):
                # common tuple shapes: (cid, samples, T_obs, n_points)
                try:
                    cid = int(item[0])
                    samples = np.asarray(item[1])
                    T_obs = float(item[2]) if len(item) > 2 else (samples.max() if samples.size else 0.0)
                    n_points = int(item[3]) if len(item) > 3 else samples.size
                    entries.append({'candidate_id': cid, 'null_samples': samples, 'T_obs': T_obs, 'n_points': n_points})
                except Exception:
                    # fallback: skip malformed entry
                    continue
            else:
                # skip unknown item types
                continue
    return entries

def compute_quantiles(samples):
    return np.percentile(samples, [0,1,5,25,50,75,95,99,100])

def safe_array(x):
    arr = np.asarray(x)
    if arr.ndim == 0:
        arr = np.atleast_1d(arr)
    return arr

def main():
    parser = argparse.ArgumentParser(description="Export null samples .npy -> per-candidate CSVs and S8 summary CSV.")
    parser.add_argument("--npy", required=True, help="Path to null_samples_summary.npy")
    parser.add_argument("--outdir", required=True, help="Output directory for CSVs")
    parser.add_argument("--run_p", type=int, default=95, help="Peripheral percentile (for metadata)")
    parser.add_argument("--B", type=int, default=1000, help="Number of null replicates (for metadata)")
    args = parser.parse_args()

    npy_path = Path(args.npy)
    outdir = Path(args.outdir)
    if not npy_path.exists():
        print(f"ERROR: .npy file not found: {npy_path}", file=sys.stderr)
        sys.exit(2)
    outdir.mkdir(parents=True, exist_ok=True)

    raw = load_npy(npy_path)
    entries = normalize_entries(raw)
    if not entries:
        print("No valid candidate entries found in the .npy file.", file=sys.stderr)
        sys.exit(3)

    summary_rows = []
    for e in entries:
        cid = e.get('candidate_id')
        samples = safe_array(e.get('null_samples', []))
        if samples.size == 0:
            print(f"Warning: candidate {cid} has no null samples; skipping.", file=sys.stderr)
            continue
        T_obs = float(e.get('T_obs', samples.max()))
        n_points = int(e.get('n_points', samples.size))

        # write raw null samples CSV
        try:
            pd.DataFrame({'T_null': samples}).to_csv(outdir / f"null_samples_candidate_{cid}.csv", index=False)
        except Exception as exc:
            print(f"ERROR writing null_samples_candidate_{cid}.csv: {exc}", file=sys.stderr)
            continue

        q = compute_quantiles(samples)
        raw_p = (1 + int((samples >= T_obs).sum())) / (1 + int(samples.size))
        summary_rows.append({
            'run_p': args.run_p,
            'B': args.B,
            'candidate_id': int(cid),
            'n_points': n_points,
            'T_obs': T_obs,
            'null_min': float(q[0]),
            'null_1pct': float(q[1]),
            'null_5pct': float(q[2]),
            'null_25pct': float(q[3]),
            'null_median': float(q[4]),
            'null_75pct': float(q[5]),
            'null_95pct': float(q[6]),
            'null_99pct': float(q[7]),
            'null_max': float(q[8]),
            'raw_p_value': float(raw_p)
        })

    if summary_rows:
        pd.DataFrame(summary_rows).to_csv(outdir / "S8_null_samples_summary.csv", index=False)
        print("Export complete:", outdir)
    else:
        print("No summary rows produced; check .npy contents.", file=sys.stderr)
        sys.exit(4)

if __name__ == "__main__":
    main()