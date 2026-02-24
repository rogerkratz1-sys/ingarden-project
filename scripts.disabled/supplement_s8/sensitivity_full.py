# sensitivity_full.py
"""
Full-dataset sensitivity test and downstream analyses.

Usage:
    python sensitivity_full.py --infile human_results_clean.csv --outprefix sensitivity_full --shuffles 5000 --permtest 2000

Outputs:
    sensitivity_full_per_row.csv
    sensitivity_full_summary.csv
    sensitivity_full_results.xlsx
    sensitivity_full_plots.png
"""
import argparse
from pathlib import Path
import random
from collections import Counter
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.metrics import confusion_matrix, cohen_kappa_score

pairs = [(3,8),(4,8),(5,6),(6,7),(7,8),(8,9)]

def parse_perm(s):
    s = (s or "")
    s = str(s).strip()
    if s.startswith('"') and s.endswith('"'):
        s = s[1:-1]
    s = s.strip("[] ")
    if not s:
        return []
    return [int(x.strip()) for x in s.split(",") if x.strip()]

def adj_present(p,a,b):
    for i in range(len(p)-1):
        if (p[i]==a and p[i+1]==b) or (p[i]==b and p[i+1]==a):
            return True
    return False

def violated_covers_for_perm(p):
    viol = []
    for a,b in pairs:
        if not adj_present(p,a,b):
            viol.append((a,b))
    return viol

def first_violated_for_order(p, order):
    for idx in order:
        a,b = pairs[idx]
        if not adj_present(p,a,b):
            return (a,b)
    return None

def percent_agreement(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return float((y_true == y_pred).mean())

def safe_kappa(y_true, y_pred):
    # return NaN if only one label present in either vector
    labels = sorted(set(list(y_true) + list(y_pred)))
    if len(labels) < 2:
        return float("nan")
    try:
        return float(cohen_kappa_score(y_true, y_pred, labels=labels))
    except Exception:
        return float("nan")

def permutation_pvalue_agreement(y_true, y_pred, n_iter=2000, seed=0):
    rng = random.Random(seed)
    obs = percent_agreement(y_true, y_pred)
    count = 0
    for _ in range(n_iter):
        perm = list(y_true)
        rng.shuffle(perm)
        if percent_agreement(perm, y_pred) >= obs:
            count += 1
    return (count + 1) / (n_iter + 1), obs  # add-one smoothing

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", required=True, help="CSV with canonical dataset (must include perm_rotated and human_label)")
    parser.add_argument("--outprefix", default="sensitivity_full", help="prefix for output files")
    parser.add_argument("--shuffles", type=int, default=5000, help="number of random cover-order shuffles per row")
    parser.add_argument("--permtest", type=int, default=2000, help="permutation iterations for agreement p-value")
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    rng = random.Random(args.seed)
    IN = Path(args.infile)
    if not IN.exists():
        raise FileNotFoundError(f"Input file not found: {IN}")

    df = pd.read_csv(IN, dtype=str, encoding="utf-8").fillna("")
    perms = [parse_perm(x) for x in df.get("perm_rotated", pd.Series([""]*len(df)))]

    # compute violated_covers and rule_any_label and first_violated_seq (canonical pairs order)
    violated_list = []
    any_label = []
    first_seq = []
    for p in perms:
        viol = violated_covers_for_perm(p)
        violated_list.append(";".join(f"({a},{b})" for a,b in viol))
        any_label.append("BRE" if viol else "NOT_BRE")
        fv = None
        for a,b in pairs:
            if not adj_present(p,a,b):
                fv = (a,b)
                break
        first_seq.append(fv if fv is not None else "")

    df["violated_covers"] = violated_list
    df["rule_any_label"] = any_label
    df["first_violated_seq"] = [str(x) for x in first_seq]

    # sensitivity shuffles per row
    pair_indices = list(range(len(pairs)))
    per_row_counts = [Counter() for _ in perms]
    stability_counts = [0]*len(perms)

    print(f"Running {args.shuffles} shuffles per row on {len(perms)} rows...")
    for s in range(args.shuffles):
        order = pair_indices[:]
        rng.shuffle(order)
        for i,p in enumerate(perms):
            fv = first_violated_for_order(p, order)
            per_row_counts[i][fv] += 1
            if fv == first_seq[i]:
                stability_counts[i] += 1
    # summarize per-row
    rows_out = []
    for i in range(len(perms)):
        total = sum(per_row_counts[i].values())
        if total == 0:
            most_common = ""
            most_count = 0
            stability = 0.0
        else:
            most_common, most_count = per_row_counts[i].most_common(1)[0]
            most_common = str(most_common)
            stability = stability_counts[i] / args.shuffles
        rows_out.append({
            "row_index": i+1,
            "orig_first_violated": str(first_seq[i]),
            "most_common_first_violated": most_common,
            "most_common_count": most_count,
            "stability_fraction": stability,
            "violated_covers": df.loc[i,"violated_covers"],
            "rule_any_label": df.loc[i,"rule_any_label"],
            "first_violated_seq": df.loc[i,"first_violated_seq"],
            "human_label": df.loc[i,"human_label"] if "human_label" in df.columns else df.loc[i,"motif_label"] if "motif_label" in df.columns else ""
        })

    per_row_df = pd.DataFrame(rows_out)
    per_row_csv = f"{args.outprefix}_per_row.csv"
    per_row_df.to_csv(per_row_csv, index=False, encoding="utf-8")

    # summary stats
    stabilities = per_row_df["stability_fraction"].astype(float)
    summary = {
        "rows": len(perms),
        "shuffles": args.shuffles,
        "mean_stability": float(stabilities.mean()),
        "median_stability": float(stabilities.median()),
        "min_stability": float(stabilities.min()),
        "max_stability": float(stabilities.max())
    }
    summary_df = pd.DataFrame([summary])
    summary_csv = f"{args.outprefix}_summary.csv"
    summary_df.to_csv(summary_csv, index=False, encoding="utf-8")

    # merge per-row back into main df for downstream analyses
    merged = pd.concat([df.reset_index(drop=True), per_row_df.reset_index(drop=True)], axis=1)
    merged_csv = f"{args.outprefix}_merged.csv"
    merged.to_csv(merged_csv, index=False, encoding="utf-8")

    # downstream agreement metrics: human_label vs rule_any_label and vs first_violated_seq
    y_human = merged["human_label"].fillna("").astype(str).tolist()
    y_any = merged["rule_any_label"].fillna("").astype(str).tolist()
    y_seq = merged["first_violated_seq"].fillna("").astype(str).tolist()

    # percent agreement
    pa_any = percent_agreement(y_human, y_any)
    pa_seq = percent_agreement(y_human, y_seq)

    # kappa (safe)
    kappa_any = safe_kappa(y_human, y_any)
    kappa_seq = safe_kappa(y_human, y_seq)

    # confusion matrices (use union of labels)
    labels_union_any = sorted(set(y_human) | set(y_any))
    labels_union_seq = sorted(set(y_human) | set(y_seq))
    try:
        cm_any = confusion_matrix(y_human, y_any, labels=labels_union_any)
    except Exception:
        cm_any = None
    try:
        cm_seq = confusion_matrix(y_human, y_seq, labels=labels_union_seq)
    except Exception:
        cm_seq = None

    # permutation p-values for percent agreement
    pval_any, obs_any = permutation_pvalue_agreement(y_human, y_any, n_iter=args.permtest, seed=args.seed)
    pval_seq, obs_seq = permutation_pvalue_agreement(y_human, y_seq, n_iter=args.permtest, seed=args.seed+1)

    results = {
        "rule": ["order_invariant_any", "sequential_first"],
        "percent_agreement": [pa_any, pa_seq],
        "observed_for_permtest": [obs_any, obs_seq],
        "permtest_pvalue": [pval_any, pval_seq],
        "cohen_kappa": [kappa_any, kappa_seq],
        "labels_union": [labels_union_any, labels_union_seq]
    }
    results_df = pd.DataFrame(results)
    results_csv = f"{args.outprefix}_results.csv"
    results_df.to_csv(results_csv, index=False, encoding="utf-8")

    # write Excel workbook with sheets
    xlsx_path = f"{args.outprefix}_results.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        per_row_df.to_excel(w, sheet_name="per_row", index=False)
        summary_df.to_excel(w, sheet_name="summary", index=False)
        results_df.to_excel(w, sheet_name="agreement", index=False)
        merged.to_excel(w, sheet_name="merged", index=False)

    # plots: histogram of stability_fraction and bar of percent agreement
    plt.figure(figsize=(10,4))
    plt.subplot(1,2,1)
    plt.hist(stabilities, bins=30, color="#4C72B0", edgecolor="k")
    plt.xlabel("stability_fraction")
    plt.ylabel("count")
    plt.title("Distribution of stability_fraction (per row)")

    plt.subplot(1,2,2)
    bars = [pa_any, pa_seq]
    names = ["order_invariant_any", "sequential_first"]
    plt.bar(names, bars, color=["#55A868","#C44E52"])
    plt.ylim(0,1)
    plt.ylabel("percent agreement")
    plt.title("Agreement with human labels")
    for i,v in enumerate(bars):
        plt.text(i, v + 0.02, f"{v:.3f}", ha="center")

    plt.tight_layout()
    plot_path = f"{args.outprefix}_plots.png"
    plt.savefig(plot_path, dpi=150)
    plt.close()

    # final summary CSV
    final_summary = {
        "rows": len(perms),
        "shuffles": args.shuffles,
        "permtest_iterations": args.permtest,
        "percent_agreement_any": pa_any,
        "percent_agreement_seq": pa_seq,
        "permtest_pvalue_any": pval_any,
        "permtest_pvalue_seq": pval_seq,
        "mean_stability": summary["mean_stability"],
        "median_stability": summary["median_stability"]
    }
    pd.DataFrame([final_summary]).to_csv(f"{args.outprefix}_final_summary.csv", index=False, encoding="utf-8")

    print("Wrote:", per_row_csv, summary_csv, results_csv, xlsx_path, plot_path, merged_csv)

if __name__ == "__main__":
    main()
