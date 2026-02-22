# sensitivity_full_parallel.py
"""
Parallel full-dataset sensitivity test.

Usage:
  python sensitivity_full_parallel.py --infile human_results_clean.csv --outprefix sensitivity_full --shuffles 5000 --permtest 2000 --workers 4

Notes:
  - The script requires pandas, numpy, scikit-learn, and openpyxl for Excel output.
  - It checks for 'human_label' first; if missing it will use 'motif_label' if present, otherwise it exits.
"""
import argparse
from pathlib import Path
import random
from collections import Counter
import pandas as pd
import numpy as np
import multiprocessing as mp
from functools import partial
from sklearn.metrics import confusion_matrix, cohen_kappa_score
import matplotlib.pyplot as plt

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

def process_row(i, perm, orig_first, shuffles, seed):
    rng = random.Random(seed + i)
    pair_indices = list(range(len(pairs)))
    counts = Counter()
    stability_count = 0
    for _ in range(shuffles):
        order = pair_indices[:]
        rng.shuffle(order)
        fv = first_violated_for_order(perm, order)
        counts[fv] += 1
        if fv == orig_first:
            stability_count += 1
    if sum(counts.values()) == 0:
        most_common = ""
        most_count = 0
        stability = 0.0
    else:
        most_common, most_count = counts.most_common(1)[0]
        most_common = str(most_common)
        stability = stability_count / shuffles
    return {
        "row_index": i+1,
        "orig_first_violated": str(orig_first) if orig_first else "",
        "most_common_first_violated": most_common,
        "most_common_count": most_count,
        "stability_fraction": stability
    }

def percent_agreement(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    return float((y_true == y_pred).mean())

def safe_kappa(y_true, y_pred):
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
    return (count + 1) / (n_iter + 1), obs

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--infile", required=True)
    parser.add_argument("--outprefix", default="sensitivity_full")
    parser.add_argument("--shuffles", type=int, default=5000)
    parser.add_argument("--permtest", type=int, default=2000)
    parser.add_argument("--workers", type=int, default=max(1, mp.cpu_count()-1))
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    IN = Path(args.infile)
    if not IN.exists():
        raise FileNotFoundError(f"Input file not found: {IN}")

    df = pd.read_csv(IN, dtype=str, encoding="utf-8").fillna("")
    # check human_label
    if "human_label" in df.columns:
        label_col = "human_label"
    elif "motif_label" in df.columns:
        label_col = "motif_label"
        print("Warning: 'human_label' not found; using 'motif_label' as human labels.")
    else:
        raise SystemExit("Error: input file must contain 'human_label' or 'motif_label' column.")

    perms = [parse_perm(x) for x in df.get("perm_rotated", pd.Series([""]*len(df)))]
    # compute violated_covers and canonical first_violated_seq
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

    # prepare parallel processing
    tasks = []
    for i, p in enumerate(perms):
        orig_first = first_seq[i]
        tasks.append((i, p, orig_first))

    print(f"Starting parallel run: {len(tasks)} rows, {args.shuffles} shuffles per row, {args.workers} workers")
    with mp.Pool(processes=args.workers) as pool:
        func = partial(process_row, shuffles=args.shuffles, seed=args.seed)
        # map with starmap-like behavior
        results = pool.starmap(process_row, [(i, p, orig_first, args.shuffles, args.seed) for (i,p,orig_first) in tasks])

    per_row_df = pd.DataFrame(results)
    per_row_csv = f"{args.outprefix}_per_row.csv"
    per_row_df.to_csv(per_row_csv, index=False, encoding="utf-8")

    # summary
    stabilities = per_row_df["stability_fraction"].astype(float)
    summary = {
        "rows": len(per_row_df),
        "shuffles": args.shuffles,
        "mean_stability": float(stabilities.mean()),
        "median_stability": float(stabilities.median()),
        "min_stability": float(stabilities.min()),
        "max_stability": float(stabilities.max())
    }
    summary_df = pd.DataFrame([summary])
    summary_csv = f"{args.outprefix}_summary.csv"
    summary_df.to_csv(summary_csv, index=False, encoding="utf-8")

    # merge and downstream metrics
    merged = pd.concat([df.reset_index(drop=True), per_row_df.reset_index(drop=True)], axis=1)
    merged_csv = f"{args.outprefix}_merged.csv"
    merged.to_csv(merged_csv, index=False, encoding="utf-8")

    y_human = merged[label_col].fillna("").astype(str).tolist()
    y_any = merged["rule_any_label"].fillna("").astype(str).tolist()
    y_seq = merged["first_violated_seq"].fillna("").astype(str).tolist()

    pa_any = percent_agreement(y_human, y_any)
    pa_seq = percent_agreement(y_human, y_seq)
    kappa_any = safe_kappa(y_human, y_any)
    kappa_seq = safe_kappa(y_human, y_seq)
    pval_any, obs_any = permutation_pvalue_agreement(y_human, y_any, n_iter=args.permtest, seed=args.seed)
    pval_seq, obs_seq = permutation_pvalue_agreement(y_human, y_seq, n_iter=args.permtest, seed=args.seed+1)

    results = {
        "rule": ["order_invariant_any", "sequential_first"],
        "percent_agreement": [pa_any, pa_seq],
        "observed_for_permtest": [obs_any, obs_seq],
        "permtest_pvalue": [pval_any, pval_seq],
        "cohen_kappa": [kappa_any, kappa_seq]
    }
    results_df = pd.DataFrame(results)
    results_csv = f"{args.outprefix}_results.csv"
    results_df.to_csv(results_csv, index=False, encoding="utf-8")

    # write Excel
    xlsx_path = f"{args.outprefix}_results.xlsx"
    with pd.ExcelWriter(xlsx_path, engine="openpyxl") as w:
        per_row_df.to_excel(w, sheet_name="per_row", index=False)
        summary_df.to_excel(w, sheet_name="summary", index=False)
        results_df.to_excel(w, sheet_name="agreement", index=False)
        merged.to_excel(w, sheet_name="merged", index=False)

    # plots
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

    final_summary = {
        "rows": len(per_row_df),
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
