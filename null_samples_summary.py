import numpy as np
import pandas as pd
from pathlib import Path

npy_path = Path(r"C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_95_B1000\null_samples_summary.npy")
out_dir = npy_path.parent

arr = np.load(npy_path, allow_pickle=True)
rows = []
for entry in arr.tolist():
    # adapt to your npy structure: try common keys
    if isinstance(entry, dict):
        cid = entry.get('candidate_id', entry.get('label'))
        samples = np.asarray(entry.get('null_samples') or entry.get('T_null') or entry.get('samples') or [])
        T_obs = float(entry.get('T_obs', entry.get('T_obs_value', samples.max() if samples.size else 0)))
        n_points = int(entry.get('n_points', entry.get('size', samples.size)))
    else:
        # fallback if entry is a tuple/list: (cid, samples, T_obs, n_points)
        try:
            cid, samples, T_obs, n_points = entry
            samples = np.asarray(samples)
        except Exception:
            continue
    if samples.size == 0:
        continue
    pd.DataFrame({'T_null': samples}).to_csv(out_dir / f"null_samples_candidate_{cid}.csv", index=False)
    q = np.percentile(samples, [0,1,5,25,50,75,95,99,100])
    raw_p = (1 + (samples >= T_obs).sum()) / (1 + len(samples))
    rows.append({
        'run_p': int(95),
        'B': int(len(samples)),
        'candidate_id': int(cid),
        'n_points': int(n_points),
        'T_obs': float(T_obs),
        'null_min': float(q[0]),
        'null_1pct': float(q[1]),
        'null_5pct': float(q[2]),
        'null_25pct': float(q[3]),
        'null_median': float(q[4]),
        'null_75pct': float(q[5]),
        'null_95pct': float(q[6]),
        'null_99pct': float(q[7]),
        'null_max': float(q[8]),
        'raw_p_value': float(raw_p)
    })

pd.DataFrame(rows).to_csv(out_dir / "S8_null_samples_summary.csv", index=False)
print("Export complete:", out_dir)