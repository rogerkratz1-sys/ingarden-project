import os, glob
import pandas as pd
import numpy as np

RUN_DIR = "motif_results_robustness/peripheral_95"
S8_SUMMARY = os.path.join(RUN_DIR, "S8_null_samples_summary.csv")
OUT_CSV = os.path.join(RUN_DIR, "candidates.csv")

def benjamini_hochberg(pvals):
    p = np.asarray(pvals)
    n = len(p)
    order = np.argsort(p)
    ranked = np.empty(n, dtype=float)
    ranked[order] = p[order] * n / (np.arange(1, n+1))
    for i in range(n-2, -1, -1):
        if ranked[i] > ranked[i+1]:
            ranked[i] = ranked[i+1]
    return np.minimum(ranked, 1.0)

def main():
    s8 = pd.read_csv(S8_SUMMARY)
    if 'candidate_id' not in s8.columns:
        s8 = s8.reset_index().rename(columns={'index':'candidate_id'})

    null_files = sorted(glob.glob(os.path.join(RUN_DIR, "null_samples_candidate_*.csv")))
    if len(null_files) == 0:
        raise SystemExit("No null_samples_candidate_*.csv files found in " + RUN_DIR)

    null_map = {}
    for f in null_files:
        base = os.path.basename(f)
        try:
            cid = int(base.split("null_samples_candidate_")[1].split(".csv")[0])
        except Exception:
            cid = len(null_map)
        arr = pd.read_csv(f, header=None).values.flatten()
        null_map[cid] = arr

    hat_p_list = []
    for _, row in s8.iterrows():
        try:
            cid = int(row.get('candidate_id', row.get('candidate', row.name)))
        except Exception:
            cid = int(row.name)
        T_obs = float(row['T_obs'])
        null_vals = null_map.get(cid)
        if null_vals is None:
            if len(null_map) == 1:
                null_vals = list(null_map.values())[0]
            else:
                raise SystemExit(f"No null samples found for candidate id {cid}")
        B = len(null_vals)
        hat_p = (1.0 + np.sum(null_vals >= T_obs)) / (1.0 + B)
        hat_p_list.append(hat_p)

    q_vals = benjamini_hochberg(hat_p_list)

    candidates = s8.copy()
    candidates['hat_p'] = hat_p_list
    candidates['q_value'] = q_vals

    if 'n_points' in candidates.columns:
        candidates = candidates.rename(columns={'n_points':'n_k'})
    if 'n_k' not in candidates.columns:
        candidates['n_k'] = candidates.get('n_points', "")

    out_cols = ['candidate_id', 'n_k']
    if 'A_k' in candidates.columns:
        out_cols.append('A_k')
    out_cols += ['T_obs', 'hat_p', 'q_value']

    for c in out_cols:
        if c not in candidates.columns:
            candidates[c] = ""

    candidates = candidates[out_cols]
    candidates = candidates.rename(columns={'candidate_id':'cluster_id'})
    candidates.to_csv(OUT_CSV, index=False)
    print("Wrote", OUT_CSV)
    print(candidates.head().to_string(index=False))

if __name__ == "__main__":
    main()
