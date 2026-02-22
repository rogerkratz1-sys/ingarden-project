# sensitivity_test_large.py
import csv
import random
import itertools
from collections import Counter, defaultdict
from pathlib import Path
import pandas as pd
import numpy as np

IN = Path("holdouts_with_human_with_violations.csv")
OUT_SUM = Path("sensitivity_test_summary.csv")
OUT_PER_ROW = Path("sensitivity_test_per_row.csv")
OUT_XLSX = Path("sensitivity_test_results.xlsx")

# parameters
SHUFFLES = 5000   # number of random cover-order permutations to test
PERMTEST = 2000   # permutation test iterations for agreement p-value (optional)

pairs = [(3,8),(4,8),(5,6),(6,7),(7,8),(8,9)]

def parse_perm(s):
    if pd.isna(s): return []
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

def first_violated_for_order(p, order):
    for idx in order:
        a,b = pairs[idx]
        if not adj_present(p,a,b):
            return (a,b)
    return None

# read input
df = pd.read_csv(IN, dtype=str, encoding="utf-8")
perms = [parse_perm(x) for x in df["perm_rotated"].fillna("")]

# baseline first violated using canonical order (pairs order)
orig_first = []
for p in perms:
    fv = None
    for a,b in pairs:
        if not adj_present(p,a,b):
            fv = (a,b)
            break
    orig_first.append(fv)

# run shuffles
rng = random.Random(0)
pair_indices = list(range(len(pairs)))
per_row_counts = [Counter() for _ in perms]
stability_counts = [0]*len(perms)

for s in range(SHUFFLES):
    order = pair_indices[:]
    rng.shuffle(order)
    for i,p in enumerate(perms):
        fv = first_violated_for_order(p, order)
        per_row_counts[i][fv] += 1
        if fv == orig_first[i]:
            stability_counts[i] += 1

# compute stability fractions and most common first-violated under shuffles
rows_out = []
for i in range(len(perms)):
    total = sum(per_row_counts[i].values())
    most_common, most_count = per_row_counts[i].most_common(1)[0]
    stability = stability_counts[i] / SHUFFLES
    rows_out.append({
        "row_index": i+1,
        "orig_first_violated": str(orig_first[i]),
        "most_common_first_violated": str(most_common),
        "most_common_count": most_count,
        "stability_fraction": stability
    })

# write per-row CSV
pd.DataFrame(rows_out).to_csv(OUT_PER_ROW, index=False, encoding="utf-8")

# summary stats
stabilities = [r["stability_fraction"] for r in rows_out]
summary = {
    "rows": len(perms),
    "shuffles": SHUFFLES,
    "mean_stability": np.mean(stabilities),
    "median_stability": np.median(stabilities),
    "min_stability": np.min(stabilities),
    "max_stability": np.max(stabilities)
}
pd.DataFrame([summary]).to_csv(OUT_SUM, index=False, encoding="utf-8")

# write Excel with two sheets
with pd.ExcelWriter(OUT_XLSX, engine="openpyxl") as w:
    pd.DataFrame(rows_out).to_excel(w, sheet_name="per_row", index=False)
    pd.DataFrame([summary]).to_excel(w, sheet_name="summary", index=False)

print(f"Wrote {OUT_PER_ROW}, {OUT_SUM}, {OUT_XLSX}")
print("Done")
