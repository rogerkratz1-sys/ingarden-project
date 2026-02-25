# export_or_regen_nulls.py
# Usage: python export_or_regen_nulls.py
# Requires: numpy, pandas, scipy, shapely, sklearn
import json
import numpy as np
import pandas as pd
from pathlib import Path
from math import atan2, cos, sin
from random import Random
from shapely.geometry import MultiPoint
from scipy.spatial import ConvexHull

OUTDIR = Path("motif_results_robustness/peripheral_95")
EMB_PATHS = [
    Path("data/embedding.npy"),
    Path("data/embeddings_5000_dim8.csv"),
    Path("motif_results_robustness/peripheral_95/embeddings_5000_dim8.csv"),
]
CAND_MEM_GLOB = "motif_results_robustness/peripheral_95/candidate_membership_*.csv"
B = 1000
SEED = 42

def try_export_from_npy():
    # look for .npy/.npz in OUTDIR
    for ext in ("*.npy", "*.npz"):
        files = list(OUTDIR.glob(ext))
        if files:
            p = files[0]
            print("Found null file:", p)
            if p.suffix == ".npz":
                data = np.load(p, allow_pickle=True)
                key = list(data.keys())[0]
                nulls = data[key]
            else:
                nulls = np.load(p, allow_pickle=True)
            # handle shapes
            if isinstance(nulls, np.ndarray) and nulls.ndim == 2:
                B_, K = nulls.shape
                for k in range(K):
                    arr = nulls[:, k]
                    pd.DataFrame({"T_null": arr}).to_csv(OUTDIR / f"null_samples_candidate_{k}.csv", index=False)
                    print("Wrote candidate", k, "rows:", len(arr))
                return True
            if isinstance(nulls, (list, np.ndarray)):
                for k, arr in enumerate(nulls):
                    arr = np.asarray(arr).ravel()
                    pd.DataFrame({"T_null": arr}).to_csv(OUTDIR / f"null_samples_candidate_{k}.csv", index=False)
                    print("Wrote candidate", k, "rows:", len(arr))
                return True
    return False

def load_embedding():
    # try CSV then npy
    for p in EMB_PATHS:
        if p.exists():
            if p.suffix == ".csv":
                df = pd.read_csv(p, header=None)
                emb = df.values
            else:
                emb = np.load(p)
            print("Loaded embedding from", p)
            return emb
    raise FileNotFoundError("Embedding not found; place embeddings_5000_dim8.csv or embedding.npy in data/ or peripheral_95/")

def load_candidate_memberships():
    import glob
    files = glob.glob(str(OUTDIR / "candidate_membership_*.csv"))
    if not files:
        raise FileNotFoundError("No candidate_membership_*.csv found in peripheral_95")
    memberships = []
    for f in sorted(files):
        df = pd.read_csv(f)
        # expect a column 'perm_index' or similar; try to infer
        if 'perm_index' in df.columns:
            idxs = df['perm_index'].astype(int).tolist()
        elif 'index' in df.columns:
            idxs = df['index'].astype(int).tolist()
        else:
            # assume first column lists permutation ids
            idxs = df.iloc[:,0].astype(int).tolist()
        memberships.append((Path(f).name, idxs))
    return memberships

def radial_preserve_nulls(emb2d, candidate_idxs, B=1000, seed=42):
    # emb2d: Nx2 array of embedding coords (use first two dims)
    # candidate_idxs: list of permutation indices in the candidate cluster
    rng = Random(seed)
    pts = emb2d
    centroid = pts.mean(axis=0)
    rel = pts - centroid
    radii = np.sqrt((rel**2).sum(axis=1))
    angles = np.arctan2(rel[:,1], rel[:,0])
    # preserve radii distribution for the peripheral set: sample angles uniformly
    # For each replicate, randomize angles for all points, compute new coords, compute convex hull area for candidate points
    # Precompute candidate radii
    cand_radii = radii[candidate_idxs]
    n_k = len(candidate_idxs)
    T_null = np.empty(B)
    for b in range(B):
        # sample random angles uniformly for each candidate (or for all points and then pick candidate positions)
        rand_angles = rng.random() * 2*np.pi
        # For radial-preserve we preserve each candidate's radius but randomize its angle
        xs = centroid[0] + cand_radii * np.cos(rand_angles)
        ys = centroid[1] + cand_radii * np.sin(rand_angles)
        pts_b = np.column_stack([xs, ys])
        # compute convex hull area
        if n_k < 3:
            area = 0.0
        else:
            try:
                hull = ConvexHull(pts_b)
                area = hull.volume  # in 2D, volume is area
            except Exception:
                # fallback to shapely
                area = MultiPoint(pts_b.tolist()).convex_hull.area
        T_null[b] = n_k / (area + 1e-12)
    return T_null

def recompute_and_write(B=B, seed=SEED):
    emb = load_embedding()
    if emb.shape[1] < 2:
        raise RuntimeError("Embedding must have at least 2 dimensions")
    emb2d = emb[:, :2]
    memberships = load_candidate_memberships()
    for idx, (fname, idxs) in enumerate(memberships):
        print("Processing", fname, "n_points=", len(idxs))
        T_null = radial_preserve_nulls(emb2d, idxs, B=B, seed=seed+idx)
        pd.DataFrame({"T_null": T_null}).to_csv(OUTDIR / f"null_samples_candidate_{idx}.csv", index=False)
        print("Wrote", OUTDIR / f"null_samples_candidate_{idx}.csv", "rows:", len(T_null))

if __name__ == "__main__":
    # 1) try export from existing .npy/.npz
    ok = try_export_from_npy()
    if ok:
        print("Exported from existing null file.")
    else:
        print("No consolidated null .npy/.npz found; recomputing radial-preserve nulls for discovered candidates.")
        recompute_and_write()
    print("Done.")