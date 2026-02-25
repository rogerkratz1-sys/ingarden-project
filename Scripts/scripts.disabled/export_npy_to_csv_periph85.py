import numpy as np, os, csv, sys
p = "motif_results_robustness/peripheral_85_regen_final/null_samples_summary.npy"
outdir = "motif_results_robustness/peripheral_85_regen_final"
if not os.path.exists(p):
    print("ERROR: .npy not found:", p); sys.exit(2)
arr = np.load(p, allow_pickle=True).tolist()
os.makedirs(outdir, exist_ok=True)
for i, samples in enumerate(arr):
    fname = os.path.join(outdir, f"null_samples_candidate_{i:03d}.csv")
    with open(fname, "w", newline="", encoding="utf-8") as fh:
        w = csv.writer(fh); w.writerow(["T_null"])
        try:
            seq = list(samples)
        except Exception:
            seq = [samples]
        for v in seq:
            w.writerow([v])
print("Wrote", len(arr), "candidate CSVs to", outdir)
