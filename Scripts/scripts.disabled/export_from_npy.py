import numpy as np, os, math
p = "motif_results_robustness/peripheral_90_test/null_samples_summary.npy"
out = "motif_results_robustness/peripheral_90_test"
os.makedirs(out, exist_ok=True)
arr = np.load(p, allow_pickle=True).tolist()

def iter_samples(s):
    if s is None:
        return []
    # iterable (but not string/bytes)
    if isinstance(s, (list, tuple, set)) or (hasattr(s, "__iter__") and not isinstance(s, (str, bytes))):
        try:
            for x in s:
                yield x
            return
        except TypeError:
            pass
    # single numeric
    if isinstance(s, (int, float)) and not (isinstance(s, float) and math.isnan(s)):
        yield s
        return
    try:
        yield float(s)
    except Exception:
        return

for entry in arr:
    try:
        if isinstance(entry, dict):
            cid = entry.get('candidate_id', entry.get('label', entry.get('id', 'unknown')))
            samples = entry.get('null_samples') or entry.get('T_null') or entry.get('samples') or []
        else:
            cid = entry[0] if len(entry) > 0 else 'unknown'
            samples = entry[1] if len(entry) > 1 else []
    except Exception:
        continue
    cid_str = str(cid).replace(' ', '_')
    fn = os.path.join(out, f'null_samples_candidate_{cid_str}.csv')
    with open(fn, 'w', encoding='utf8') as fh:
        fh.write('T_null\n')
        for v in iter_samples(samples):
            fh.write(str(v) + '\n')
print("Wrote per-candidate CSVs to", out)
