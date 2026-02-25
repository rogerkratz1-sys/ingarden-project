#!/usr/bin/env python3
"""
compute_jaccard_ari_flip.py

Usage:
  python compute_jaccard_ari_flip.py

Assumes runs are in:
  C:/Users/ctint/Desktop/Scripts/motif_results_robustness
and expects subfolders:
  peripheral_85, peripheral_90, peripheral_95

Outputs:
  jaccard_matches.csv
  flip_report.csv
Printed ARI values for pairwise comparisons.
"""
import sys
from pathlib import Path
import pandas as pd
from sklearn.metrics import adjusted_rand_score

ROOT = Path("C:/Users/ctint/Desktop/Scripts/motif_results_robustness")

RUNS = {
    "p85": ROOT / "peripheral_85",
    "p90": ROOT / "peripheral_90",
    "p95": ROOT / "peripheral_95",
}

def find_labels_file(run_dir: Path):
    # Try common locations for labels_per_perm.csv
    candidates = [
        run_dir / "labels_per_perm.csv",
        run_dir / "motif_results" / "labels_per_perm.csv",
        run_dir / "results" / "labels_per_perm.csv",
    ]
    for p in candidates:
        if p.exists():
            return p
    return None

def load_labels(run_dir: Path):
    f = find_labels_file(run_dir)
    if f is None:
        raise FileNotFoundError(f"labels_per_perm.csv not found in {run_dir}")
    df = pd.read_csv(f)
    # Expect columns: perm_id, label
    if "perm_id" not in df.columns or "label" not in df.columns:
        # try to infer: first column perm id, second label
        if df.shape[1] >= 2:
            df = df.rename(columns={df.columns[0]: "perm_id", df.columns[1]: "label"})
        else:
            raise ValueError(f"labels_per_perm.csv in {run_dir} missing expected columns")
    df = df.sort_values("perm_id").reset_index(drop=True)
    return df["perm_id"].tolist(), df["label"].astype(str).tolist()

def build_membership_from_candidates(run_dir: Path):
    """
    Build a dict label -> set(perm_id) using candidate_membership_<label>.csv if present,
    otherwise reconstruct from labels_per_perm.csv.
    """
    members = {}
    # try candidate_membership files
    found = False
    for p in run_dir.glob("candidate_membership_*.csv"):
        try:
            lab = p.stem.split("candidate_membership_")[-1]
            df = pd.read_csv(p)
            if "perm_id" in df.columns:
                members[str(lab)] = set(df["perm_id"].tolist())
            else:
                # assume first column is perm_id
                members[str(lab)] = set(df.iloc[:,0].tolist())
            found = True
        except Exception:
            continue
    if found:
        return members

    # fallback: reconstruct from labels_per_perm.csv
    labels_file = find_labels_file(run_dir)
    if labels_file is None:
        return {}
    df = pd.read_csv(labels_file)
    if "perm_id" not in df.columns or "label" not in df.columns:
        if df.shape[1] >= 2:
            df = df.rename(columns={df.columns[0]: "perm_id", df.columns[1]: "label"})
        else:
            return {}
    for _, row in df.iterrows():
        pid = row["perm_id"]
        lab = str(row["label"])
        members.setdefault(lab, set()).add(pid)
    return members

def jaccard(a, b):
    A = set(a)
    B = set(b)
    if not (A or B):
        return 0.0
    return len(A & B) / len(A | B)

def main():
    # Load labels for each run
    perm_ids = None
    labels = {}
    for key, path in RUNS.items():
        if not path.exists():
            print(f"Warning: run folder not found: {path}", file=sys.stderr)
            continue
        try:
            pids, labs = load_labels(path)
            labels[key] = labs
            if perm_ids is None:
                perm_ids = pids
            else:
                # sanity check: perm ids should match
                if pids != perm_ids:
                    print(f"Warning: perm_id ordering differs for {key}; proceeding but results may be inconsistent", file=sys.stderr)
        except Exception as e:
            print(f"Warning: could not load labels for {key}: {e}", file=sys.stderr)

    # Compute ARI pairwise
    keys = sorted(labels.keys())
    if len(keys) >= 2:
        for i in range(len(keys)):
            for j in range(i+1, len(keys)):
                k1 = keys[i]; k2 = keys[j]
                ari = adjusted_rand_score(labels[k1], labels[k2])
                print(f"ARI {k1} vs {k2}: {ari:.4f}")
    else:
        print("Not enough label vectors to compute ARI", file=sys.stderr)

    # Build membership dicts
    members = {}
    for key, path in RUNS.items():
        if not path.exists():
            members[key] = {}
            continue
        members[key] = build_membership_from_candidates(path)

    # Compute Jaccard matches for p90 candidates against p85 and p95
    jaccard_rows = []
    if "p90" in members:
        for lab90, mem90 in members["p90"].items():
            best85 = (None, 0.0)
            best95 = (None, 0.0)
            if "p85" in members:
                for lab85, mem85 in members["p85"].items():
                    score = jaccard(mem90, mem85)
                    if score > best85[1]:
                        best85 = (lab85, score)
            if "p95" in members:
                for lab95, mem95 in members["p95"].items():
                    score = jaccard(mem90, mem95)
                    if score > best95[1]:
                        best95 = (lab95, score)
            jaccard_rows.append({
                "p90_label": lab90,
                "p90_size": len(mem90),
                "best85_label": best85[0],
                "jaccard_85": best85[1],
                "best95_label": best95[0],
                "jaccard_95": best95[1],
            })
    jaccard_df = pd.DataFrame(jaccard_rows)
    jaccard_out = ROOT / "jaccard_matches.csv"
    jaccard_df.to_csv(jaccard_out, index=False)
    print(f"Wrote Jaccard matches to {jaccard_out}")

    # Flip report: permutations whose labels differ across runs
    flip_rows = []
    if perm_ids is None:
        print("No perm_id vector found; cannot build flip report", file=sys.stderr)
    else:
        # ensure we have labels for all three keys; if missing, fill with placeholder
        lab85 = labels.get("p85", ["NA"] * len(perm_ids))
        lab90 = labels.get("p90", ["NA"] * len(perm_ids))
        lab95 = labels.get("p95", ["NA"] * len(perm_ids))
        for i, pid in enumerate(perm_ids):
            a = str(lab85[i]) if i < len(lab85) else "NA"
            b = str(lab90[i]) if i < len(lab90) else "NA"
            c = str(lab95[i]) if i < len(lab95) else "NA"
            if not (a == b == c):
                flip_rows.append({
                    "perm_id": pid,
                    "label_p85": a,
                    "label_p90": b,
                    "label_p95": c
                })
    flip_df = pd.DataFrame(flip_rows)
    flip_out = ROOT / "flip_report.csv"
    flip_df.to_csv(flip_out, index=False)
    print(f"Wrote flip report to {flip_out}")
    print("Done.")

if __name__ == "__main__":
    main()