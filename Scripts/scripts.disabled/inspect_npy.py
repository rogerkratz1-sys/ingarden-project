import os, numpy as np
p = "motif_results_robustness/peripheral_90_regen_patch_test/null_samples_summary.npy"
print("exists", os.path.exists(p))
if os.path.exists(p):
    arr = np.load(p, allow_pickle=True).tolist()
    print("entries", len(arr))
    for i, e in enumerate(arr):
        try:
            L = len(e)
        except Exception:
            L = 1
        print(f"{i} len={L}")
