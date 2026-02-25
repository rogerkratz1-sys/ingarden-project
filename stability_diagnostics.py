#!/usr/bin/env python3
"""
Stability diagnostics for compute_stability outputs.

Saves small CSV extracts to supplement/S-8/diagnostics and prints summaries:
 - top N unstable permutations
 - for each of those, list settings that produce non-modal labels and their flags
 - counts of how often each motif appears in multilabel_union
 - simple precedence sensitivity summary (how many perms change label across sampled precedence orders)
"""

import os
import json
import pandas as pd
from collections import Counter, defaultdict

OUT_DIR = "supplement/S-8/diagnostics"
os.makedirs(OUT_DIR, exist_ok=True)

# Config
SUMMARY_CSV = "supplement/S-8/stability_summary.csv"
MAP_CSV = "supplement/S-8/stability_map.csv"
PRECEDENCE_CSV = "supplement/S-8/precedence_ensemble.csv"
TOP_N = 20   # how many "most unstable" permutations to inspect in detail

def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    # use utf-8-sig to be robust to BOMs
    return pd.read_csv(path, encoding="utf-8-sig")

def top_unstable(summary_df, n=TOP_N):
    """Return the n permutations with lowest stability_score."""
    return summary_df.sort_values("stability_score").head(n)

def non_modal_settings_for_perm(map_df, perm_id):
    """Return rows where primary_label != modal label for a given perm_id."""
    sub = map_df[map_df["perm_id"] == perm_id].copy()
    if sub.empty:
        return sub
    modal = sub["primary_label"].mode().iloc[0]
    non_modal = sub[sub["primary_label"] != modal].sort_values("setting_id")
    # parse flags_json into a readable string
    def flags_str(j):
        try:
            d = json.loads(j)
            return ";".join(sorted([k for k, v in d.items() if v]))
        except Exception:
            return j
    if not non_modal.empty:
        non_modal = non_modal.assign(flags = non_modal["flags_json"].apply(flags_str))
    return modal, non_modal

def motif_union_counts(summary_df):
    """Count how many permutations include each motif in multilabel_union."""
    c = Counter()
    for u in summary_df["multilabel_union"].dropna():
        for motif in str(u).split(";"):
            motif = motif.strip()
            if motif:
                c[motif] += 1
    return c

def precedence_sensitivity(precedence_df):
    """
    Quick summary: for each perm_id, how many distinct primary_label values across sampled precedence orders.
    Returns a DataFrame with perm_id, n_labels, modal_label_count.
    """
    if precedence_df.empty:
        return pd.DataFrame()
    grouped = precedence_df.groupby("perm_id")["primary_label"].nunique().reset_index()
    grouped = grouped.rename(columns={"primary_label": "n_distinct_labels"})
    return grouped

def main():
    print("Loading files...")
    s = load_csv(SUMMARY_CSV)
    m = load_csv(MAP_CSV)
    p = load_csv(PRECEDENCE_CSV) if os.path.exists(PRECEDENCE_CSV) else pd.DataFrame()

    print(f"Summary rows: {len(s)}; Map rows: {len(m)}; Precedence rows: {len(p)}")

    # Top unstable permutations
    top = top_unstable(s, TOP_N)
    print(f"\nTop {TOP_N} permutations with lowest stability_score:")
    print(top[["perm_id","stability_score","modal_label","multilabel_union"]].to_string(index=False))
    top.to_csv(os.path.join(OUT_DIR, "top_unstable_summary.csv"), index=False)

    # For each top unstable perm, list non-modal settings and flags
    details = []
    for pid in top["perm_id"].tolist():
        modal_and_nonmodal = non_modal_settings_for_perm(m, pid)
        if isinstance(modal_and_nonmodal, tuple):
            modal, non_modal = modal_and_nonmodal
        else:
            modal, non_modal = None, modal_and_nonmodal
        print(f"\nperm_id = {pid}  modal_label = {modal}  non_modal_count = {len(non_modal)}")
        if not non_modal.empty:
            # print a compact sample (first 20)
            print(non_modal[["setting_id","primary_label","flags"]].head(20).to_string(index=False))
            # save full non-modal rows for this perm
            non_modal.to_csv(os.path.join(OUT_DIR, f"perm_{int(pid)}_non_modal_settings.csv"), index=False)
        details.append({"perm_id": pid, "modal_label": modal, "non_modal_count": len(non_modal)})

    pd.DataFrame(details).to_csv(os.path.join(OUT_DIR, "top_unstable_details.csv"), index=False)

    # Motif union counts
    counts = motif_union_counts(s)
    print("\nMotif counts in multilabel_union (how many permutations ever show each motif):")
    for motif, cnt in counts.most_common():
        print(f"  {motif}: {cnt}")
    pd.DataFrame(list(counts.items()), columns=["motif","count"]).to_csv(os.path.join(OUT_DIR, "motif_union_counts.csv"), index=False)

    # Precedence sensitivity summary
    if not p.empty:
        prec_summary = precedence_sensitivity(p)
        # how many perms have >1 distinct label across precedence orders?
        n_sensitive = (prec_summary["n_distinct_labels"] > 1).sum()
        print(f"\nPrecedence sensitivity: {n_sensitive} permutations change label across sampled precedence orders (out of {len(prec_summary)})")
        prec_summary.to_csv(os.path.join(OUT_DIR, "precedence_sensitivity.csv"), index=False)
    else:
        print("\nNo precedence_ensemble.csv found; skipping precedence sensitivity summary.")

    print(f"\nDiagnostics saved to {OUT_DIR}. Done.")

if __name__ == "__main__":
    main()