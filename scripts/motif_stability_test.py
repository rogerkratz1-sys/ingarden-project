#!/usr/bin/env python3
# motif_stability_test.py
# Computes motif stability by randomizing cover-check order.
# Usage:
#   python motif_stability_test.py [path/to/all_motifs_520.csv]

import csv
import random
import os
import sys
from collections import Counter
import pandas as pd

# Allow passing the input filename as the first CLI argument
if len(sys.argv) > 1:
    INPUT = sys.argv[1]
else:
    INPUT = "all_motifs_520.csv"

print("Using input file:", INPUT)
if not os.path.exists(INPUT):
    print("Input file not found:", INPUT)
    sys.exit(1)

# OUTPUT files
OUT_PERM = "motif_stability_per_permutation.csv"
OUT_SUMMARY = "motif_stability_summary.csv"

# CONFIG: number of random cover-check orders to sample per permutation
N_RANDOM_ORDERS = 500   # increase to 2000 for higher precision if you have time

# canonical covers used by mapping rules
COVERS = [
    (1, 3), (1, 4), (1, 5),
    (3, 8), (4, 8), (5, 6), (6, 7), (7, 8), (8, 9),
    (9, 10), (10, 11), (11, 12)
]

def parse_perm(s):
    if s is None:
        return []
    tokens = str(s).strip().split()
    return [int(t) for t in tokens if t.strip().isdigit()]

def compute_violated_covers_from_perm(perm):
    pos = {v: i for i, v in enumerate(perm)}
    violated = []
    for a, b in COVERS:
        if a in pos and b in pos and pos[a] > pos[b]:
            violated.append((a, b))
    return set(violated)

# Mapping rules (first-violated with a cover_check_order)
def classify_first_violated(violated_set, cover_check_order):
    # 1. GlobalDistortion — many violations (4 or more).
    if len(violated_set) >= 4:
        return "GlobalDistortion"
    # 2. FrontEndMove — violates any front covers (1,3), (1,4), (1,5).
    front = {(1, 3), (1, 4), (1, 5)}
    for cov in cover_check_order:
        if cov in violated_set and cov in front:
            return "FrontEndMove"
    # 3. BlockReorderExtreme — violates any block/chain covers among the set
    bre_set = {(3, 8), (4, 8), (5, 6), (6, 7), (7, 8), (8, 9)}
    for cov in cover_check_order:
        if cov in violated_set and cov in bre_set:
            return "BlockReorderExtreme"
    # 4. DualClusterOutlier — violates at least one early cover and at least one late cover
    early = front
    late = {(9, 10), (10, 11), (11, 12)}
    if any(c in violated_set for c in early) and any(c in violated_set for c in late):
        for cov in cover_check_order:
            if cov in violated_set and (cov in early or cov in late):
                return "DualClusterOutlier"
    # 5. AnchorPreservingDisorder — has violations but does not violate any front covers
    if len(violated_set) > 0 and not any(c in violated_set for c in front):
        return "AnchorPreservingDisorder"
    # 6. Other
    return "Other"

# Order-invariant classification (any-cover)
def classify_any_cover(violated_set):
    if len(violated_set) >= 4:
        return "GlobalDistortion"
    front = {(1, 3), (1, 4), (1, 5)}
    bre_set = {(3, 8), (4, 8), (5, 6), (6, 7), (7, 8), (8, 9)}
    early = front
    late = {(9, 10), (10, 11), (11, 12)}
    if any(c in violated_set for c in front):
        return "FrontEndMove"
    if any(c in violated_set for c in bre_set):
        return "BlockReorderExtreme"
    if any(c in violated_set for c in early) and any(c in violated_set for c in late):
        return "DualClusterOutlier"
    if len(violated_set) > 0 and not any(c in violated_set for c in front):
        return "AnchorPreservingDisorder"
    return "Other"

# Read input CSV (expects header with 'motif' and 'perm' columns; falls back to second column)
rows = []
with open(INPUT, newline='') as f:
    reader = csv.DictReader(f)
    for r in reader:
        perm_field = r.get("perm") or r.get("permutation") or r.get("permuted") or None
        if perm_field is None:
            # fallback: take the second column value
            vals = list(r.values())
            if len(vals) >= 2:
                perm_field = vals[1]
            else:
                perm_field = ""
        rows.append({"orig_motif": r.get("motif", ""), "perm_str": perm_field})

perms = []
random.seed(0)
for i, r in enumerate(rows):
    perm = parse_perm(r["perm_str"])
    violated = compute_violated_covers_from_perm(perm)
    baseline_order = COVERS.copy()
    baseline_label = classify_first_violated(violated, baseline_order)
    any_label = classify_any_cover(violated)

    # Stability sampling: randomize cover-check order N_RANDOM_ORDERS times
    if not violated:
        stability = 1.0
        modal_label = baseline_label
    else:
        same_count = 0
        modal_counts = Counter()
        for _ in range(N_RANDOM_ORDERS):
            order = COVERS.copy()
            random.shuffle(order)
            lab = classify_first_violated(violated, order)
            modal_counts[lab] += 1
            if lab == baseline_label:
                same_count += 1
        stability = same_count / N_RANDOM_ORDERS
        modal_label = modal_counts.most_common(1)[0][0]

    perms.append({
        "index": i,
        "orig_motif": r["orig_motif"],
        "perm_str": r["perm_str"],
        "violated_covers": ";".join(f"({a},{b})" for a, b in sorted(violated)),
        "baseline_first_label": baseline_label,
        "any_cover_label": any_label,
        "stability_fraction_first": stability,
        "modal_label_first": modal_label
    })

df = pd.DataFrame(perms)
df.to_csv(OUT_PERM, index=False)

# summary by baseline_first_label
summary_rows = []
for label, group in df.groupby("baseline_first_label"):
    total = len(group)
    unstable = int((group["stability_fraction_first"] < 0.40).sum())
    summary_rows.append({
        "baseline_first_label": label,
        "total_rows": total,
        "unstable_count": unstable,
        "fraction_unstable": unstable / total if total > 0 else 0.0
    })
summary_df = pd.DataFrame(summary_rows).sort_values("unstable_count", ascending=False)
summary_df.to_csv(OUT_SUMMARY, index=False)

print("Wrote per-permutation results to", OUT_PERM)
print("Wrote motif summary to", OUT_SUMMARY)
print()
print("Sample rows:")
print(df[["index", "orig_motif", "baseline_first_label", "any_cover_label", "stability_fraction_first"]].head(10).to_string(index=False))
print()
print("Summary:")
print(summary_df.to_string(index=False))
