#!/usr/bin/env python3
"""
scripts/sensitivity_grid.py

Compute motif counts and ARI across a grid of tau_K_high and tau_B values.
Outputs:
 - artifacts/sensitivity_counts_blockreorder.csv  (heatmap counts for BlockReorderExtreme)
 - artifacts/sensitivity_summary.csv             (per-grid ARI and counts)
 - figures/sensitivity_grid_blockreorder.png     (heatmap)
 - figures/sensitivity_motif_trends.png          (motif counts vs tau_K_high)
"""
import json
from pathlib import Path
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.cluster import KMeans
from sklearn.metrics import adjusted_rand_score
import warnings
warnings.filterwarnings("ignore")

ROOT = Path(".")
DATA = ROOT / "data"
ART = ROOT / "artifacts"
FIG = ROOT / "figures"
ART.mkdir(exist_ok=True)
FIG.mkdir(exist_ok=True)

# Parameters to sweep
tau_K_high_vals = np.array([0.50, 0.55, 0.60, 0.65, 0.70, 0.75, 0.80])
tau_B_vals = np.array([1, 2, 3, 4, 5])

# Clustering settings (tune to match your pipeline)
KMEANS_K = 6
# HDBSCAN fallback: if not installed, skip HDBSCAN ARI
try:
    import hdbscan
    HDBSCAN_AVAILABLE = True
except Exception:
    HDBSCAN_AVAILABLE = False

# Load data
scored = pd.read_csv(DATA / "all_scored.csv")
coords = pd.read_csv(DATA / "combined_coords_nystrom_rotated_v5.csv")
rules_orig = pd.read_csv(ART / "assigned_motifs.csv")

# Ensure index alignment: rules indexed by 'index'
rules_idx = rules_orig.set_index("index")["motif_label"]

# Helper: apply deterministic rules (same logic as earlier) to scored df
def apply_rules(scored_df, tau_K_high, tau_B, tau_A=1, tau_S=3, tau_dual=0.85):
    df = scored_df.copy()
    max_k = df["kendall_distance"].max()
    med_k = df["kappa_disp"].median()
    kf = df["kendall_distance"] / max_k
    kr = 1.0 - kf
    labels = np.array(["Other"] * len(df), dtype=object)
    mask_a = (kf >= tau_K_high) & (df["block_reversals"] >= tau_B)
    labels[mask_a] = "BlockReorderExtreme"
    mask_b = (~mask_a) & (df["anchor_violations"] >= tau_A) & (df["kappa_disp"] >= med_k)
    labels[mask_b] = "AnchorPreservingDisorder"
    mask_c = (~mask_a) & (~mask_b) & (df["swap_count"] >= tau_S)
    labels[mask_c] = "FrontEndMove"
    mask_d = (~mask_a) & (~mask_b) & (~mask_c) & (kr >= tau_dual)
    labels[mask_d] = "DualClusterOutlier"
    mask_e = (~mask_a) & (~mask_b) & (~mask_c) & (~mask_d) & (df["kappa_disp"] >= med_k * 1.5)
    labels[mask_e] = "GlobalDistortion"
    return pd.DataFrame({"index": df["index"], "motif_label": labels})

# Map rule labels to coords indices: if rules cover fewer indices, reindex and fill "Other"
def labels_for_coords(rules_df, coords_df):
    r = rules_df.set_index("index").reindex(coords_df["index"]).reset_index()
    r["motif_label"] = r["motif_label"].fillna("Other")
    return r["motif_label"].values

# Prepare results containers
rows = []
block_counts = np.zeros((len(tau_B_vals), len(tau_K_high_vals)), dtype=int)
motif_types = ["BlockReorderExtreme","AnchorPreservingDisorder","FrontEndMove","DualClusterOutlier","GlobalDistortion","Other"]

for i, tau_B in enumerate(tau_B_vals):
    for j, tau_K_high in enumerate(tau_K_high_vals):
        # compute rule labels on scored
        rules_df = apply_rules(scored, tau_K_high=tau_K_high, tau_B=tau_B)
        # map to coords
        rule_labels_coords = labels_for_coords(rules_df, coords)
        # clustering on coords mds_x, mds_y
        X = coords[["x","y"]].values
        # KMeans
        kmeans = KMeans(n_clusters=KMEANS_K, random_state=0).fit(X)
        klabels = kmeans.labels_
        ari_k = adjusted_rand_score(rule_labels_coords, klabels)
        # HDBSCAN if available
        if HDBSCAN_AVAILABLE:
            clusterer = hdbscan.HDBSCAN(min_cluster_size=15)
            hlabels = clusterer.fit_predict(X)
            ari_h = adjusted_rand_score(rule_labels_coords, hlabels)
        else:
            ari_h = np.nan
        # motif counts (on scored, not coords) and averaged over coords mapping
        counts = rules_df["motif_label"].value_counts().reindex(motif_types, fill_value=0)
        block_counts[i, j] = counts["BlockReorderExtreme"]
        rows.append({
            "tau_B": int(tau_B),
            "tau_K_high": float(tau_K_high),
            "ari_kmeans": float(ari_k),
            "ari_hdbscan": float(ari_h) if not np.isnan(ari_h) else "",
            **{f"count_{m}": int(counts[m]) for m in motif_types}
        })

# Save summary CSV
summary = pd.DataFrame(rows)
summary.to_csv(ART / "sensitivity_summary.csv", index=False)

# Save heatmap CSV for BlockReorderExtreme
heat_df = pd.DataFrame(block_counts, index=tau_B_vals, columns=tau_K_high_vals)
heat_df.to_csv(ART / "sensitivity_counts_blockreorder.csv")

# Plot heatmap
plt.figure(figsize=(8,5))
sns.heatmap(heat_df, annot=True, fmt="d", cmap="viridis")
plt.title("BlockReorderExtreme counts")
plt.xlabel("tau_K_high")
plt.ylabel("tau_B")
plt.tight_layout()
plt.savefig(FIG / "sensitivity_grid_blockreorder.png", dpi=200)
plt.close()

# Plot motif trends averaged over tau_B
avg_by_tauK = summary.groupby("tau_K_high")[[f"count_{m}" for m in motif_types]].mean()
plt.figure(figsize=(8,5))
for m in motif_types:
    plt.plot(avg_by_tauK.index.astype(float), avg_by_tauK[f"count_{m}"], label=m)
plt.xlabel("tau_K_high")
plt.ylabel("Average motif count (over tau_B)")
plt.title("Motif counts vs tau_K_high")
plt.legend()
plt.tight_layout()
plt.savefig(FIG / "sensitivity_motif_trends.png", dpi=200)
plt.close()

print("Wrote artifacts/sensitivity_summary.csv and figures in figures/ and artifacts/")
