#!/usr/bin/env python3
# order_invariant_analysis.py
# Usage:
#   python order_invariant_analysis.py [path/to/all_motifs_520.csv]
# Default path: ./artifacts/all_motifs_520.csv

import os, sys, csv, re
from collections import Counter, defaultdict
import pandas as pd

# Input handling
if len(sys.argv) > 1:
    INPUT = sys.argv[1]
else:
    INPUT = os.path.join("artifacts", "all_motifs_520.csv")

print("Using input file:", INPUT)
if not os.path.exists(INPUT):
    print("Input file not found:", INPUT)
    sys.exit(1)

# Output filenames
OUT_PERM = "any_cover_labels_per_permutation.csv"
OUT_SUMMARY = "anycover_motif_summary.csv"
OUT_CONFUSION = "orig_vs_anycover_confusion.csv"
OUT_ADJ = "adjacency_any_occurrence_counts.csv"

# Canonical covers used by mapping rules
COVERS = [
    (1,3),(1,4),(1,5),
    (3,8),(4,8),(5,6),(6,7),(7,8),(8,9),
    (9,10),(10,11),(11,12)
]

# Helper: parse permutation string like "6 8 3 10 ..." into list of ints
def parse_perm(s):
    if s is None:
        return []
    tokens = str(s).strip().split()
    return [int(t) for t in tokens if t.strip().isdigit()]

# Compute violated covers: a cover (a,b) is violated if a appears after b in the permutation
def compute_violated_covers_from_perm(perm):
    pos = {v:i for i,v in enumerate(perm)}
    violated = []
    for a,b in COVERS:
        if a in pos and b in pos and pos[a] > pos[b]:
            violated.append((a,b))
    return set(violated)

# Order-invariant classification (any-cover) with deterministic priority for ties
def classify_any_cover(violated_set):
    # 1. GlobalDistortion — many violations (4 or more).
    if len(violated_set) >= 4:
        return "GlobalDistortion"
    # 2. FrontEndMove — violates any front covers (1,3), (1,4), (1,5).
    front = {(1,3),(1,4),(1,5)}
    if any(c in violated_set for c in front):
        return "FrontEndMove"
    # 3. BlockReorderExtreme — violates any block/chain covers among the set
    bre_set = {(3,8),(4,8),(5,6),(6,7),(7,8),(8,9)}
    if any(c in violated_set for c in bre_set):
        return "BlockReorderExtreme"
    # 4. DualClusterOutlier — violates at least one early cover and at least one late cover
    early = front
    late = {(9,10),(10,11),(11,12)}
    if any(c in violated_set for c in early) and any(c in violated_set for c in late):
        return "DualClusterOutlier"
    # 5. AnchorPreservingDisorder — has violations but does not violate any front covers
    if len(violated_set) > 0 and not any(c in violated_set for c in front):
        return "AnchorPreservingDisorder"
    # 6. Other
    return "Other"

# Read input CSV (accepts header 'motif' and 'perm' or motif in first column and perm in second)
df_src = pd.read_csv(INPUT, dtype=str).fillna("")
# Determine perm column
perm_col = None
for candidate in ["perm","permutation","permuted"]:
    if candidate in df_src.columns:
        perm_col = candidate
        break
if perm_col is None:
    # fallback to second column if present
    if df_src.shape[1] >= 2:
        perm_col = df_src.columns[1]
    else:
        print("Could not find a permutation column in the CSV."); sys.exit(1)

orig_motif_col = "motif" if "motif" in df_src.columns else df_src.columns[0]

# Compute violated covers and any-cover labels
rows_out = []
adj_counts = Counter()
for idx, row in df_src.iterrows():
    perm_str = row[perm_col]
    perm = parse_perm(perm_str)
    violated = compute_violated_covers_from_perm(perm)
    violated_str = ";".join(f"({a},{b})" for a,b in sorted(violated))
    # update adjacency counts
    for a,b in violated:
        adj_counts[f"({a}, {b})"] += 1
    any_label = classify_any_cover(violated)
    rows_out.append({
        "index": idx,
        "orig_motif": row.get(orig_motif_col, ""),
        "perm_str": perm_str,
        "violated_covers": violated_str,
        "any_cover_label": any_label
    })

# Write per-permutation output
out_df = pd.DataFrame(rows_out)
out_df.to_csv(OUT_PERM, index=False)

# Summary counts per computed motif
summary = out_df["any_cover_label"].value_counts().reset_index()
summary.columns = ["any_cover_label","count"]
summary.to_csv(OUT_SUMMARY, index=False)

# Confusion table: original motif vs any_cover_label
conf = pd.crosstab(out_df["orig_motif"], out_df["any_cover_label"])
conf.to_csv(OUT_CONFUSION)

# Adjacency any-occurrence counts
adj_df = pd.DataFrame([{"adjacency":k,"count_any_occurrence":v} for k,v in sorted(adj_counts.items(), key=lambda x:-x[1])])
adj_df.to_csv(OUT_ADJ, index=False)

# Console summary
print("Wrote per-permutation any-cover labels to", OUT_PERM)
print("Wrote any-cover motif summary to", OUT_SUMMARY)
print("Wrote orig vs any-cover confusion to", OUT_CONFUSION)
print("Wrote adjacency any-occurrence counts to", OUT_ADJ)
print()
print("Any-cover motif counts:")
print(summary.to_string(index=False))
print()
print("Top adjacency counts (sample):")
print(adj_df.head(10).to_string(index=False))
