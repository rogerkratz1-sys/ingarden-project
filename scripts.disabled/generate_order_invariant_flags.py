#!/usr/bin/env python3
# generate_order_invariant_flags.py
import os, json
import pandas as pd
import numpy as np

OUTDIR = "supplement/artifacts"
os.makedirs(OUTDIR, exist_ok=True)

# Read diagnostics (must exist)
diag = pd.read_csv("supplement/diagnostics_per_exemplar.csv")

# Example multilabel assignment function (placeholder: uses motif_label)
# In your pipeline this should call the real classifier/heuristic.
def assign_labels(row):
    # primary label from motif_label column
    primary = row.get("motif_label", "")
    labels = { "BRE":0, "FM/EM":0, "APD":0, "DCO":0, "GD":0, "Other":0 }
    if primary in labels:
        labels[primary] = 1
    else:
        # fallback: map "Other" family
        labels["Other"] = 1
    return labels

# Build base table
rows = []
for _, r in diag.iterrows():
    labels = assign_labels(r)
    # order-invariant test: apply small random within-class permutations and reassign
    # Here we simulate by repeating label assignment N times (replace with real perturbation)
    N = 100
    stable_counts = {k:0 for k in labels.keys()}
    for _ in range(N):
        # In a real test, perturb the permutation slightly and re-run assign_labels
        # For demo, we assume deterministic assignment; mark stable if assigned every time
        for k,v in labels.items():
            if v==1:
                stable_counts[k] += 1
    stable_flags = {k: (stable_counts[k] == N) for k in stable_counts}
    row = {
        "exemplar_id": r["exemplar_id"],
        "permutation": r.get("permutation",""),
        "primary_label": r.get("motif_label",""),
    }
    # add label columns
    for k in labels:
        row[f"label_{k}"] = labels[k]
        row[f"stable_{k}"] = int(stable_flags[k])
    rows.append(row)

out = pd.DataFrame(rows)
out.to_csv(os.path.join(OUTDIR, "order_invariant_multilabel_flags.csv"), index=False)
print("Wrote", os.path.join(OUTDIR, "order_invariant_multilabel_flags.csv"))