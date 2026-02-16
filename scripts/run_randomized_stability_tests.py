#!/usr/bin/env python3
# run_randomized_stability_tests.py
import os, math, random
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

OUTDIR = "supplement/artifacts/stability_tests"
os.makedirs(OUTDIR, exist_ok=True)
os.makedirs(os.path.join(OUTDIR,"stability_plots"), exist_ok=True)

diag = pd.read_csv("supplement/diagnostics_per_exemplar.csv")
# If reader summary exists, use it
try:
    summary = pd.read_csv("supplement/reader_ratings_summary.csv")
except:
    summary = None

# Parameters
N_BOOT = 500
rng = np.random.default_rng(42)

# Example metric to test: structural_metric rank stability under small random noise
base = diag[["exemplar_id","structural_metric"]].copy()
base["rank"] = base["structural_metric"].rank(method="min", ascending=True)

bootstrap_rows = []
for b in range(N_BOOT):
    # perturb structural_metric by small multiplicative noise (±5%)
    noise = rng.normal(loc=1.0, scale=0.05, size=len(base))
    pert = base["structural_metric"].values * noise
    pert_rank = pd.Series(pert).rank(method="min", ascending=True)
    concordance = (pert_rank.values == base["rank"].values).mean()
    bootstrap_rows.append({"bootstrap": b, "rank_concordance": concordance})
bootstrap_df = pd.DataFrame(bootstrap_rows)
bootstrap_df.to_csv(os.path.join(OUTDIR, "stability_bootstrap_samples.csv"), index=False)

# Summary
summary_df = bootstrap_df.agg({"rank_concordance":["mean","std","min","max"]}).T
summary_df.to_csv(os.path.join(OUTDIR, "stability_summary.csv"))

# Plot histogram of concordance
sns.histplot(bootstrap_df["rank_concordance"], bins=30, kde=False)
plt.xlabel("Rank concordance (fraction identical ranks)")
plt.title("Bootstrap rank concordance")
plt.tight_layout()
plt.savefig(os.path.join(OUTDIR,"stability_plots","rank_concordance.png"), dpi=200)
plt.close()

print("Wrote stability outputs to", OUTDIR)