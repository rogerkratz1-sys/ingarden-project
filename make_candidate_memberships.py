# make_candidate_memberships.py
import re
import ast
import pandas as pd
from pathlib import Path

OUTDIR = Path("motif_results_robustness/peripheral_95")
CAND_PATH = OUTDIR / "candidates.csv"

if not CAND_PATH.exists():
    raise SystemExit("candidates.csv not found in motif_results_robustness/peripheral_95")

df = pd.read_csv(CAND_PATH, dtype=str, keep_default_na=False)
print("Loaded candidates.csv with columns:", df.columns.tolist())

# candidate id column heuristics
if 'candidate_id' in df.columns:
    id_col = 'candidate_id'
elif 'id' in df.columns:
    id_col = 'id'
elif 'candidate' in df.columns:
    id_col = 'candidate'
else:
    id_col = None

# membership column heuristics
possible_members_cols = ['members', 'member_indices', 'indices', 'members_list', 'membership', 'memberships']
members_col = None
for c in possible_members_cols:
    if c in df.columns:
        members_col = c
        break

def parse_members_cell(cell):
    s = str(cell).strip()
    if s == "" or s.lower() in ("nan", "none"):
        return []
    # try JSON / Python list
    try:
        val = ast.literal_eval(s)
        if isinstance(val, (list, tuple)):
            return [int(x) for x in val]
    except Exception:
        pass
    # remove surrounding brackets and split on common delimiters
    s2 = re.sub(r'^[\[\(\{]\s*', '', s)
    s2 = re.sub(r'\s*[\]\)\}]\s*$', '', s2)
    parts = re.split(r'[;,]\s*|\s+\|\s+|\s+', s2)
    ints = []
    for p in parts:
        p = p.strip()
        if p == '':
            continue
        # strip quotes
        p = p.strip('"\'')
        # try int
        try:
            ints.append(int(p))
        except Exception:
            # try to extract digits
            m = re.findall(r'-?\d+', p)
            for mm in m:
                ints.append(int(mm))
    return ints

if members_col:
    print("Using membership column:", members_col)
    for _, row in df.iterrows():
        cid = row[id_col] if id_col else str(_)
        raw = row[members_col]
        members = parse_members_cell(raw)
        outp = OUTDIR / f"candidate_membership_{cid}.csv"
        pd.DataFrame({'perm_index': members}).to_csv(outp, index=False)
        print("Wrote", outp, "n_members=", len(members))
else:
    # try to find any column that looks like a list per row
    found = False
    for c in df.columns:
        sample = df[c].iloc[0]
        if isinstance(sample, str) and (re.search(r'[\[\(].*[\]\)]', sample) or re.search(r'\d+[,;]\s*\d+', sample)):
            members_col = c
            found = True
            break
    if found:
        print("Inferred membership column:", members_col)
        for _, row in df.iterrows():
            cid = row[id_col] if id_col else str(_)
            raw = row[members_col]
            members = parse_members_cell(raw)
            outp = OUTDIR / f"candidate_membership_{cid}.csv"
            pd.DataFrame({'perm_index': members}).to_csv(outp, index=False)
            print("Wrote", outp, "n_members=", len(members))
    else:
        # fallback: if candidates.csv contains a column per permutation (rare), try to derive by cluster label
        # look for a column named 'cluster' or 'label' and a column 'perm_index' in another file
        raise SystemExit("Could not find a membership column in candidates.csv. Inspect the file and rerun or provide labels_per_perm.csv.")