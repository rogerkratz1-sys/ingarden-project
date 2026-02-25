#!/usr/bin/env python3





"""
motif_discovery_test.py

Pipeline:
  - Load embedding CSV (expects header with perm_pos, dim_0 ... dim_{d-1})
  - Select peripheral points by radial distance percentile
  - Find candidate clusters with DBSCAN
  - Compute cluster density test statistic (n_points / convex_hull_area)
  - Generate null datasets (three methods) and compute Monte Carlo p-values
  - Apply Benjamini-Hochberg FDR
  - Run injection power test and stability across seeds
  - Save CSV report and diagnostic plots in outdir

Usage:
  python motif_discovery_test.py --embeddings embeddings_5000_dim8.csv --outdir motif_results
"""

from __future__ import annotations
outdir = None
# --- begin helper: write labels and candidate membership (module-level) ---
import pandas as _pd
from pathlib import Path as _Path

def write_labels_module(labels, perm_ids=None, outdir=None):
    """
    Write labels_per_perm.csv and candidate_membership_<label>.csv.
    labels: iterable of labels
    perm_ids: iterable of ids (optional)
    outdir: Path or string (optional)
    """
    try:
        _outdir = _Path(outdir) if outdir is not None else _Path('.')
    except Exception:
        _outdir = _Path('.')
    _outdir.mkdir(parents=True, exist_ok=True)

    try:
        if labels is None:
            print("Warning: write_labels_module called with labels=None")
            return
        if not isinstance(labels, list):
            try:
                labels = list(labels)
            except Exception:
                labels = [str(labels)]

        if perm_ids is None:
            perm_ids = [str(i) for i in range(len(labels))]
        else:
            try:
                perm_ids = [str(x) for x in perm_ids]
            except Exception:
                perm_ids = [str(x) for x in perm_ids]

        df_out = _pd.DataFrame({"perm_id": perm_ids, "label": [str(x) for x in labels]})
        df_out.to_csv(_outdir / "labels_per_perm.csv", index=False)

        for lab, group in df_out.groupby("label"):
            members = group["perm_id"].tolist()
            _pd.DataFrame({"perm_id": members}).to_csv(_outdir / f"candidate_membership_{lab}.csv", index=False)

        print("Wrote labels_per_perm.csv and candidate_membership_*.csv to", str(_outdir))
    except Exception as _e:
        print("Warning: write_labels_module failed:", _e)
# --- end helper ---
import argparse, os, json, time, math
import numpy as np
import pandas as pd
from sklearn.cluster import DBSCAN
from scipy.spatial import ConvexHull
from sklearn.decomposition import PCA
import matplotlib.pyplot as plt
import seaborn as sns
from typing import List, Tuple, Dict
import random

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--embeddings", required=True)
    p.add_argument("--outdir", default="motif_results")
    p.add_argument("--peripheral_pct", type=float, default=90.0,
                   help="percentile for radial distance to define peripheral set")
    p.add_argument("--dbscan_eps", type=float, default=0.5)
    p.add_argument("--dbscan_min_samples", type=int, default=5)
    p.add_argument("--null_method", choices=["shuffle_coords","bootstrap","radial_preserve"], default="radial_preserve")
    p.add_argument("--B", type=int, default=1000, help="Monte Carlo replicates")
    p.add_argument("--alpha", type=float, default=0.05)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--inject_n", type=int, default=50, help="points to inject for power test")
    p.add_argument("--inject_trials", type=int, default=50, help="injection trials for power estimate")
    p.add_argument("--stability_seeds", type=int, default=5, help="seeds for embedding stability test")
    return p.parse_args()

def load_embeddings(path: str) -> pd.DataFrame:
    df = pd.read_csv(path)
    # Expect perm_pos and dim_0..dim_k
    dims = [c for c in df.columns if c.startswith("dim_")]
    if len(dims) == 0:
        raise SystemExit("No dim_* columns found in embeddings CSV")
    return df.sort_values("perm_pos").reset_index(drop=True)

def radial_distance(X: np.ndarray) -> np.ndarray:
    # Euclidean radius from origin
    return np.linalg.norm(X, axis=1)

def select_peripheral(df: pd.DataFrame, pct: float) -> pd.DataFrame:
    dims = [c for c in df.columns if c.startswith("dim_")]
    X = df[dims].values
    r = radial_distance(X)
    thr = np.percentile(r, pct)
    mask = r >= thr
    return df.loc[mask].copy()

def find_clusters(df: pd.DataFrame, eps: float, min_samples: int) -> Tuple[np.ndarray, List[int]]:
    dims = [c for c in df.columns if c.startswith("dim_")]
    X = df[dims].values
    db = DBSCAN(eps=eps, min_samples=min_samples).fit(X)
    labels = db.labels_
    

    try:
        _perm_ids = locals().get('perm_ids', None) or globals().get('perm_ids', None)
        _outdir = locals().get('outdir', None) or globals().get('outdir', None)
        # if args.outdir exists, prefer it
        if _outdir is None and globals().get('args', None) and getattr(globals().get('args'), 'outdir', None):
            _outdir = globals().get('args').outdir
        write_labels_module(labels, perm_ids=_perm_ids, outdir=_outdir)
    except Exception as _e:
        print('Warning: write_labels_module call failed:', _e)

    unique_labels = sorted([l for l in set(labels) if l != -1])
    return labels, unique_labels

def convex_area(points: np.ndarray) -> float:
    if points.shape[0] < 3:
        return 0.0
    try:
        hull = ConvexHull(points)
        return hull.volume  # in 2D volume is area; in higher dims it's hypervolume
    except Exception:
        # fallback: small positive area to avoid division by zero
        return 1e-9

def cluster_density_stat(points: np.ndarray) -> float:
    n = points.shape[0]
    area = convex_area(points)
    if area <= 0:
        return float(n) / 1e-6
    return float(n) / area

def sample_null_shuffle_coords(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    # shuffle coordinates across points independently per dimension
    rng = np.random.RandomState(seed)
    dims = [c for c in df.columns if c.startswith("dim_")]
    X = df[dims].values.copy()
    for j in range(X.shape[1]):
        rng.shuffle(X[:, j])
    out = df.copy()
    out[dims] = X
    return out

def sample_null_bootstrap(df: pd.DataFrame, seed: int) -> pd.DataFrame:
    rng = np.random.RandomState(seed)
    dims = [c for c in df.columns if c.startswith("dim_")]
    X = df[dims].values
    idx = rng.randint(0, X.shape[0], size=X.shape[0])
    out = df.copy()
    out[dims] = X[idx]
    return out

def sample_null_radial_preserve(df_all: pd.DataFrame, df_periph: pd.DataFrame, seed: int, bins: int = 10) -> pd.DataFrame:
    # preserve radial distribution by sampling points from df_all within radial bins
    rng = np.random.RandomState(seed)
    dims = [c for c in df_all.columns if c.startswith("dim_")]
    X_all = df_all[dims].values
    r_all = radial_distance(X_all)
    # create bins
    edges = np.percentile(r_all, np.linspace(0, 100, bins+1))
    # for each periph point, sample a replacement from same radial bin
    X_per = df_periph[dims].values
    r_per = radial_distance(X_per)
    X_null = np.zeros_like(X_per)
    for i, r in enumerate(r_per):
        # find bin index
        bin_idx = np.searchsorted(edges, r, side="right") - 1
        bin_idx = max(0, min(bin_idx, bins-1))
        # candidate indices in that bin
        mask = (r_all >= edges[bin_idx]) & (r_all <= edges[bin_idx+1])
        candidates = np.where(mask)[0]
        if len(candidates) == 0:
            # fallback to random
            j = rng.randint(0, X_all.shape[0])
        else:
            j = rng.choice(candidates)
        X_null[i] = X_all[j]
    out = df_periph.copy()
    out[dims] = X_null
    return out

def compute_candidate_stats(df_all: pd.DataFrame, df_periph: pd.DataFrame, labels: np.ndarray, unique_labels: List[int]) -> List[Dict]:
    dims = [c for c in df_periph.columns if c.startswith("dim_")]
    X = df_periph[dims].values
    results = []
    for lab in unique_labels:
        mask = labels == lab
        pts = X[mask]
        if pts.shape[0] == 0:
            continue
        stat = cluster_density_stat(pts)
        center = pts.mean(axis=0)
        results.append({
            "label": int(lab),
            "size": int(pts.shape[0]),
            "stat": float(stat),
            "center": center.tolist()
        })
    return results


def monte_carlo_pvalue(candidate, df_all, df_periph, null_method, B, seed):
    """
    Robust Monte Carlo p-value: collect T_null as a list and return (p_hat, T_null).
    This preserves the existing density/count/area logic but ensures T_null is always a list.
    """
    import numpy as _np
    T_obs = candidate.get("stat", None)
    try:
        B = int(B)
    except Exception:
        B = 0
    T_null = []
    for b in range(B):
        s = int(seed) + int(b) + 1
        if null_method == "shuffle_coords":
            df_null = sample_null_shuffle_coords(df_periph, s)
        elif null_method == "bootstrap":
            df_null = sample_null_bootstrap(df_periph, s)
        else:
            df_null = sample_null_radial_preserve(df_all, df_periph, s)

        dims = [c for c in df_null.columns if c.startswith("dim_")]
        X_null = df_null[dims].values

        # compute distances to candidate center if available
        try:
            center = candidate.get("center", None)
            if center is not None:
                center_arr = _np.array(center)
                dists = _np.linalg.norm(X_null - center_arr, axis=1)
            else:
                dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])
        except Exception:
            dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])

        # radius estimate (use candidate size if present)
        try:
            k = max(1, int(candidate.get("size", 1)))
            r = float(_np.partition(dists, k-1)[k-1]) if dists.size > 0 else 0.0
        except Exception:
            r = float(_np.median(dists)) if dists.size > 0 else 0.0

        try:
            count = int(_np.sum(dists <= r))
        except Exception:
            count = 0

        try:
            pts_within = X_null[dists <= r]
            area = convex_area(pts_within) if pts_within.shape[0] >= 3 else max(1e-6, r**2)
        except Exception:
            area = max(1e-6, r**2)

        try:
            stat_val = float(count) / float(area)
        except Exception:
            stat_val = float("nan")
        T_null.append(stat_val)

    # one-sided Monte Carlo p-value with small-sample correction
    try:
        p_hat = (1 + sum(1 for t in T_null if (not _np.isnan(t)) and (T_obs is not None and t >= T_obs))) / (1 + max(1, int(B)))
    except Exception:
        p_hat = (1 + sum(1 for t in T_null if not _np.isnan(t))) / (1 + max(1, int(B)))
    return p_hat, T_null

def benjamini_hochberg(pvals: List[float], alpha: float) -> List[bool]:
    m = len(pvals)
    order = np.argsort(pvals)
    p_sorted = np.array(pvals)[order]
    thresholds = (np.arange(1, m+1) / m) * alpha
    below = p_sorted <= thresholds
    if not np.any(below):
        return [False] * m
    k = np.max(np.where(below)[0])
    selected = np.zeros(m, dtype=bool)
    selected[order[:k+1]] = True
    return selected.tolist()

def injection_power_test(df_all, df_periph, inject_n, trials, db_eps, db_min, null_method, B, seed):
    # inject tight clusters into periphery and measure detection rate
    rng = np.random.RandomState(seed)
    dims = [c for c in df_periph.columns if c.startswith("dim_")]
    X_per = df_periph[dims].values
    results = []
    for t in range(trials):
        # pick a random center from periphery and inject cluster around it
        center_idx = rng.randint(0, X_per.shape[0])
        center = X_per[center_idx]
        # tight cluster: gaussian around center with small sigma
        sigma = 0.01 * np.std(X_per, axis=0).mean()
        injected = center + rng.randn(inject_n, X_per.shape[1]) * sigma
        # create augmented periphery
        df_aug = df_periph.copy()
        df_aug = pd.concat([df_aug, pd.DataFrame(injected, columns=dims)], ignore_index=True)
        # cluster
        labels, unique = find_clusters(df_aug, eps=db_eps, min_samples=db_min)
        # check if any cluster overlaps injected points (injected are last inject_n rows)
        injected_mask = np.arange(df_aug.shape[0]) >= (df_aug.shape[0] - inject_n)
        detected = False
        for lab in unique:
            lab_mask = labels == lab
            overlap = np.sum(lab_mask & injected_mask)
            if overlap >= max(1, inject_n // 5):
                detected = True
                break
        results.append(detected)
    power = np.mean(results)
    return power

def stability_test(df_all, df_periph, eps, min_samples, seeds: List[int]):
    # run DBSCAN on periphery with different seeds by jittering slightly
    dims = [c for c in df_periph.columns if c.startswith("dim_")]
    X = df_periph[dims].values
    memberships = []
    for s in seeds:
        rng = np.random.RandomState(s)
        jitter = 1e-6 * rng.randn(*X.shape)
        Xj = X + jitter
        dfj = df_periph.copy()
        dfj[dims] = Xj
        labels, unique = find_clusters(dfj, eps=eps, min_samples=min_samples)
        # membership sets per cluster
        sets = {lab: set(np.where(labels == lab)[0].tolist()) for lab in unique}
        memberships.append(sets)
    # compute pairwise Jaccard for clusters across seeds for the largest cluster in first seed
    if len(memberships) < 2:
        return {}
    base = memberships[0]
    stability = {}
    for lab, sset in base.items():
        jaccards = []
        for other in memberships[1:]:
            # find best matching cluster by Jaccard
            best = 0.0
            for lab2, sset2 in other.items():
                inter = len(sset & sset2)
                union = len(sset | sset2)
                j = inter / union if union > 0 else 0.0
                if j > best:
                    best = j
            jaccards.append(best)
        stability[int(lab)] = float(np.mean(jaccards)) if jaccards else 0.0
    return stability

def save_report(outdir, candidates, pvals, selected, null_samples_summary, meta):
    os.makedirs(outdir, exist_ok=True)
    rows = []
    for i, c in enumerate(candidates):
        rows.append({
            "label": c["label"],
            "size": c["size"],
            "stat": c["stat"],
            "center": json.dumps(c["center"]),
            "pval": float(pvals[i]),
            "selected": bool(selected[i])
        })
    df = pd.DataFrame(rows)
    df.to_csv(os.path.join(outdir, "motif_candidates_test.csv"), index=False)
    with open(os.path.join(outdir, "meta.json"), "w", encoding="utf-8") as fh:
        json.dump(meta, fh, indent=2)
    # save null samples summary if provided
    if null_samples_summary:
        # Normalize entries so each element is an iterable (list) before saving.
        normalized = []
        for entry in null_samples_summary:
            if entry is None:
                normalized.append([])
                continue
            if isinstance(entry, dict) and 'null_samples' in entry:
                s = entry.get('null_samples')
            else:
                s = entry
            try:
                if hasattr(s, 'tolist') and not isinstance(s, (str, bytes)):
                    s_list = s.tolist()
                    normalized.append(list(s_list))
                    continue
            except Exception:
                pass
            if hasattr(s, '__iter__') and not isinstance(s, (str, bytes)):
                try:
                    normalized.append(list(s))
                    continue
                except Exception:
                    pass
            try:
                normalized.append([float(s)])
            except Exception:
                normalized.append([s])
        np.save(os.path.join(outdir, "null_samples_summary.npy"), np.array(normalized, dtype=object))
print("Saved report to", outdir)

def plot_null_histograms(outdir, candidates, null_samples_summary):
    os.makedirs(outdir, exist_ok=True)
    for i, c in enumerate(candidates):
        Tnull = null_samples_summary[i]
        plt.figure(figsize=(6,4))
        sns.histplot(Tnull, bins=40, kde=False)
        plt.axvline(c["stat"], color="red", linestyle="--", label=f"obs={c['stat']:.3g}")
        plt.title(f"Candidate {c['label']} stat distribution")
        plt.legend()
        plt.tight_layout()
        plt.savefig(os.path.join(outdir, f"null_hist_label_{c['label']}.png"))
        plt.close()

def main():
    args = parse_args()
    np.random.seed(args.seed)
    random.seed(args.seed)
    df = load_embeddings(args.embeddings)
    dims = [c for c in df.columns if c.startswith("dim_")]
    X = df[dims].values

    # peripheral selection
    df_periph = select_peripheral(df, args.peripheral_pct)
    print(f"Selected {len(df_periph)} peripheral points out of {len(df)}")

    # clustering
    labels, unique = find_clusters(df_periph, eps=args.dbscan_eps, min_samples=args.dbscan_min_samples)
    print("Found clusters:", unique)
    candidates = compute_candidate_stats(df, df_periph, labels, unique)
    if len(candidates) == 0:
        print("No candidate clusters found. Exiting.")
        return

    # Monte Carlo testing
    pvals = []
    null_samples_summary = []
    start = time.time()
    for i, cand in enumerate(candidates):
        p_hat, Tnull = monte_carlo_pvalue(cand, df, df_periph, args.null_method, args.B, args.seed + i*1000)
        pvals.append(p_hat)
        null_samples_summary.append(Tnull)
        print(f"Candidate {cand['label']} size={cand['size']} stat={cand['stat']:.6g} p={p_hat:.6g}")
    elapsed = time.time() - start
    print(f"Monte Carlo testing done in {elapsed:.1f}s")

    # FDR
    selected = benjamini_hochberg(pvals, args.alpha)
    print("Selected by BH FDR:", sum(selected), "out of", len(selected))

    # injection power test
    power = injection_power_test(df, df_periph, args.inject_n, args.inject_trials,
                                 args.dbscan_eps, args.dbscan_min_samples, args.null_method, args.B//10, args.seed+999)
    print(f"Injection power estimate (n={args.inject_n}) = {power:.3f}")

    # stability test
    seeds = [args.seed + i for i in range(args.stability_seeds)]
    stability = stability_test(df, df_periph, args.dbscan_eps, args.dbscan_min_samples, seeds)
    print("Stability per cluster (Jaccard):", stability)

    # save report and plots
    meta = {
        "embeddings": os.path.abspath(args.embeddings),
        "peripheral_pct": args.peripheral_pct,
        "dbscan_eps": args.dbscan_eps,
        "dbscan_min_samples": args.dbscan_min_samples,
        "null_method": args.null_method,
        "B": args.B,
        "alpha": args.alpha,
        "seed": args.seed,
        "n_candidates": len(candidates),
        "injection_power_estimate": float(power),
        "stability": stability
    }
    save_report(args.outdir, candidates, pvals, selected, null_samples_summary, meta)
    plot_null_histograms(args.outdir, candidates, null_samples_summary)
    print("Done. Results in", args.outdir)

if __name__ == "__main__":
    main()






