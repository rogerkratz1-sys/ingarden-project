# make_candidate_memberships_from_labels.py
import pandas as pd
from pathlib import Path

outdir = Path("motif_results_robustness/peripheral_95")
labels_path = outdir / "labels_per_perm.csv"

if not labels_path.exists():
    raise SystemExit("labels_per_perm.csv not found in peripheral_95")

df = pd.read_csv(labels_path)
# infer columns
if 'perm_index' in df.columns and 'cluster' in df.columns:
    perm_col, cluster_col = 'perm_index', 'cluster'
elif 'perm' in df.columns and 'label' in df.columns:
    perm_col, cluster_col = 'perm', 'label'
else:
    perm_col, cluster_col = df.columns[0], df.columns[1]

df[perm_col] = df[perm_col].astype(int)
for k in sorted(df[cluster_col].unique()):
    members = df.loc[df[cluster_col] == k, perm_col].tolist()
    outp = outdir / f"candidate_membership_{k}.csv"
    pd.DataFrame({'perm_index': members}).to_csv(outp, index=False)
    print("Wrote", outp, "n_members=", len(members))