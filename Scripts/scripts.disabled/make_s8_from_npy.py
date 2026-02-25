import os, json, numpy as np, datetime, subprocess, csv, sys, re

# configuration: list the outdirs you produced
outdirs = {
    "peripheral_85": "motif_results_robustness/peripheral_85_regen_final",
    "peripheral_90": "motif_results_robustness/peripheral_90_regen_final",
    "peripheral_95": "motif_results_robustness/peripheral_95_regen_final"
}

# helper to compute quantiles and stats
def summarize(samples):
    a = np.array(list(samples), dtype=float)
    q = np.percentile(a, [0,1,5,25,50,75,95,99,100])
    return {
        "n": len(a),
        "mean": float(a.mean()),
        "std": float(a.std(ddof=0)),
        "min": float(q[0]),
        "p1": float(q[1]),
        "p5": float(q[2]),
        "p25": float(q[3]),
        "median": float(q[4]),
        "p75": float(q[5]),
        "p95": float(q[6]),
        "p99": float(q[7]),
        "max": float(q[8])
    }

# collect summaries per outdir
all_rows = []
for tag, od in outdirs.items():
    p = os.path.join(od, "null_samples_summary.npy")
    if not os.path.exists(p):
        print("WARNING: missing", p, file=sys.stderr)
        continue
    arr = np.load(p, allow_pickle=True).tolist()
    for cid, samples in enumerate(arr):
        s = summarize(samples)
        # try to find observed stat in candidate_membership or run log if present
        # fallback: leave observed_stat blank for manual fill if not found
        observed = ""
        # assemble row
        row = {
            "peripheral": tag,
            "candidate_id": cid,
            "observed_stat": observed,
            "null_n": s["n"],
            "null_mean": s["mean"],
            "null_sd": s["std"],
            "null_min": s["min"],
            "null_1pct": s["p1"],
            "null_5pct": s["p5"],
            "null_25pct": s["p25"],
            "null_median": s["median"],
            "null_75pct": s["p75"],
            "null_95pct": s["p95"],
            "null_99pct": s["p99"],
            "null_max": s["max"]
        }
        all_rows.append(row)

# write canonical S8_null_samples_summary.csv
out_csv = "supplement/S-8/S8_null_samples_summary.csv"
os.makedirs(os.path.dirname(out_csv), exist_ok=True)
with open(out_csv, "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh)
    header = ["peripheral","candidate_id","observed_stat","null_n","null_mean","null_sd","null_min","null_1pct","null_5pct","null_25pct","null_median","null_75pct","null_95pct","null_99pct","null_max"]
    w.writerow(header)
    for r in all_rows:
        w.writerow([r[h] for h in header])
print("Wrote", out_csv)

# create or update S8_null_histograms.txt by replacing placeholders if present
s8_txt = "supplement/S-8/S8_null_histograms.txt"
template = None
if os.path.exists(s8_txt):
    template = open(s8_txt, "r", encoding="utf-8").read()
else:
    template = ""

# simple replacement: replace tokens like <null_median_0> with values for peripheral_90 candidate 0 if present
# We'll replace tokens for each peripheral tag and candidate id pattern <null_median_{tag}_{cid}>
for r in all_rows:
    # tokens to replace
    tag = r["peripheral"]
    cid = r["candidate_id"]
    # build token patterns used in your S-8 draft (two common forms)
    tokens = {
        f"<null_min_{cid}>": str(r["null_min"]),
        f"<null_1pct_{cid}>": str(r["null_1pct"]),
        f"<null_5pct_{cid}>": str(r["null_5pct"]),
        f"<null_25pct_{cid}>": str(r["null_25pct"]),
        f"<null_median_{cid}>": str(r["null_median"]),
        f"<null_75pct_{cid}>": str(r["null_75pct"]),
        f"<null_95pct_{cid}>": str(r["null_95pct"]),
        f"<null_99pct_{cid}>": str(r["null_99pct"]),
        f"<null_max_{cid}>": str(r["null_max"]),
        f"m{cid}": str(r["null_mean"]),
        f"s{cid}": str(r["null_sd"])
    }
    for tok, val in tokens.items():
        template = template.replace(tok, val)

# write updated S8_null_histograms.txt (if template empty, create a minimal file pointing to CSV)
if not template.strip():
    template = "S8 null histograms summary\nSee S8_null_samples_summary.csv for numeric quantiles per candidate.\n"
open(s8_txt, "w", encoding="utf-8").write(template)
print("Wrote/updated", s8_txt)

# prepend provenance header to all S-8 files
commit = "unknown"
try:
    commit = subprocess.check_output(["git","rev-parse","--short","HEAD"], stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    pass
date = datetime.datetime.utcnow().isoformat() + "Z"
provenance = f"# Provenance: run_date={date} git_commit={commit} command=motif_discovery_test.py --B 1000 --null_method radial_preserve\n\n"

for fname in ["supplement/S-8/S8_null_samples_summary.csv","supplement/S-8/S8_null_histograms.txt","supplement/S-8/S8_run_commands.txt","supplement/S-8/S8_readme.txt"]:
    if os.path.exists(fname):
        content = open(fname, "r", encoding="utf-8").read()
        if not content.startswith("# Provenance:"):
            open(fname, "w", encoding="utf-8").write(provenance + content)
            print("Prepended provenance to", fname)

print("Done. Review supplement/S-8/ and commit changes.")
