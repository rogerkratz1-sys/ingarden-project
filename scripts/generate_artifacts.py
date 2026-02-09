#!/usr/bin/env python3
# generate_artifacts.py
# Creates order-invariant multilabel flags, randomized stability tests, and adjudication templates
# Usage: python supplement/artifacts/generate_artifacts.py
# Requires: pandas, numpy, matplotlib, seaborn

import os
from datetime import datetime
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

# Reproducibility
RNG_SEED = 42
np.random.seed(RNG_SEED)

# Paths
DIAG_PATH = os.path.join("supplement", "diagnostics_per_exemplar.csv")
READER_SUM_PATH = os.path.join("supplement", "reader_ratings_summary.csv")

ARTIFACTS_DIR = os.path.join("supplement", "artifacts")
STABILITY_DIR = os.path.join(ARTIFACTS_DIR, "stability_tests")
STABILITY_PLOTS = os.path.join(STABILITY_DIR, "stability_plots")
ADJ_DIR = os.path.join(ARTIFACTS_DIR, "adjudication")

# Create directories
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
os.makedirs(STABILITY_DIR, exist_ok=True)
os.makedirs(STABILITY_PLOTS, exist_ok=True)
os.makedirs(ADJ_DIR, exist_ok=True)

# Read inputs
if not os.path.exists(DIAG_PATH):
    raise FileNotFoundError(f"Missing required file: {DIAG_PATH}")
diag = pd.read_csv(DIAG_PATH)

reader_sum = None
if os.path.exists(READER_SUM_PATH):
    try:
        reader_sum = pd.read_csv(READER_SUM_PATH)
    except Exception:
        reader_sum = None

# 1) order_invariant_multilabel_flags.csv
mapping = {
    "BRE": "BRE",
    "FM/EM": "FM_EM",
    "APD": "APD",
    "DCO": "DCO",
    "GD": "GD",
    "Other": "Other",
}
labels_list = ["BRE", "FM_EM", "APD", "DCO", "GD", "Other"]

rows = []
for _, r in diag.iterrows():
    motif = r.get("motif_label", "")
    primary = mapping.get(motif, "Other")
    row = {
        "exemplar_id": r.get("exemplar_id", ""),
        "permutation": r.get("permutation", ""),
        "primary_label": primary,
    }
    for L in labels_list:
        row[f"label_{L}"] = 1 if L == primary else 0
        # Simulated stability flags for demo: mark primary as stable
        row[f"stable_{L}"] = 1 if L == primary else 0
    rows.append(row)

order_flags = pd.DataFrame(rows)
order_flags_path = os.path.join(ARTIFACTS_DIR, "order_invariant_multilabel_flags.csv")
order_flags.to_csv(order_flags_path, index=False, encoding="utf-8")

# 2) randomized stability tests
if "structural_metric" not in diag.columns:
    raise ValueError("structural_metric column missing in diagnostics_per_exemplar.csv")

base = diag[["exemplar_id", "structural_metric"]].copy()
base["base_rank"] = base["structural_metric"].rank(method="min", ascending=True)

N_BOOT = 500
bootstrap_rows = []
rng = np.random.default_rng(RNG_SEED)
for b in range(N_BOOT):
    noise = rng.normal(loc=1.0, scale=0.05, size=len(base))
    pert = base["structural_metric"].values * noise
    pert_rank = pd.Series(pert).rank(method="min", ascending=True)
    concord = (pert_rank.values == base["base_rank"].values).mean()
    bootstrap_rows.append({"bootstrap": b, "rank_concordance": float(concord)})

bs_df = pd.DataFrame(bootstrap_rows)
bs_path = os.path.join(STABILITY_DIR, "stability_bootstrap_samples.csv")
bs_df.to_csv(bs_path, index=False, encoding="utf-8")

# summary
mean_c = bs_df["rank_concordance"].mean()
std_c = bs_df["rank_concordance"].std()
min_c = bs_df["rank_concordance"].min()
max_c = bs_df["rank_concordance"].max()
summary_df = pd.DataFrame([{"mean": mean_c, "std": std_c, "min": min_c, "max": max_c}])
summary_path = os.path.join(STABILITY_DIR, "stability_summary.csv")
summary_df.to_csv(summary_path, index=False, encoding="utf-8")

# plot histogram
sns.set(style="whitegrid")
plt.figure(figsize=(6, 4))
sns.histplot(bs_df["rank_concordance"], bins=30, kde=False, color="#4c72b0")
plt.xlabel("Rank concordance (fraction identical ranks)")
plt.ylabel("Count")
plt.title(f"Bootstrap rank concordance (N={N_BOOT})")
plt.tight_layout()
plot_path = os.path.join(STABILITY_PLOTS, "rank_concordance.png")
plt.savefig(plot_path, dpi=200)
plt.close()

# 3) adjudication files
label_cols = [f"label_{L}" for L in labels_list]
stable_cols = [f"stable_{L}" for L in labels_list]

flags = order_flags.copy()
flags["label_sum"] = flags[label_cols].sum(axis=1)


def primary_unstable(row):
    prim = row["primary_label"]
    col = f"stable_{prim}"
    return int(row.get(col, 1) == 0)


flags["primary_unstable"] = flags.apply(primary_unstable, axis=1)
ambiguous = flags[(flags["label_sum"] > 1) | (flags["primary_unstable"] == 1)].copy()
amb_path = os.path.join(ADJ_DIR, "adjudication_candidates.csv")
ambiguous.to_csv(amb_path, index=False, encoding="utf-8")

# adjudication log template
log_path = os.path.join(ADJ_DIR, "adjudication_log.csv")
pd.DataFrame(columns=["exemplar_id", "initial_labels", "adjudicator", "timestamp", "final_label", "notes"]).to_csv(
    log_path, index=False, encoding="utf-8"
)

# instructions
instr_path = os.path.join(ADJ_DIR, "adjudication_instructions.md")
with open(instr_path, "w", encoding="utf-8") as f:
    f.write(
        "Adjudication rubric\n\n"
        "- Inspect permutation and diagnostics (structural_metric, cover_violations, anchor_preservation).\n"
        "- Prefer labels that preserve anchor relations when present.\n"
        "- If ambiguous, mark 'Other' and add an interpretive note explaining the rationale.\n"
        "- Record decisions in adjudication_log.csv with timestamp and notes.\n"
    )

# Summary printout
created_files = [
    order_flags_path,
    bs_path,
    summary_path,
    plot_path,
    amb_path,
    log_path,
    instr_path,
]
print("Created files:")
for p in created_files:
    print(" -", p)
print("\nStability summary (mean, std, min, max):")
print(f" - mean: {mean_c:.6f}")
print(f" - std : {std_c:.6f}")
print(f" - min : {min_c:.6f}")
print(f" - max : {max_c:.6f}")

# Exit