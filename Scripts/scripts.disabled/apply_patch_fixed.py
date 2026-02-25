import io, os, re, sys

bak_fn = "motif_discovery_test.py.bak"
fn = "motif_discovery_test.py"

# read source (we restored from .bak above)
with io.open(fn, "r", encoding="utf8") as fh:
    src = fh.read()

# --- 1) Replace monte_carlo_pvalue function body ---
mc_start = src.find("def monte_carlo_pvalue(")
if mc_start == -1:
    print("ERROR: monte_carlo_pvalue not found in file.")
    sys.exit(2)

# find next top-level def after monte_carlo_pvalue to determine end
m_next = re.search(r"\ndef\s+\w+\s*\(", src[mc_start+1:], flags=re.MULTILINE)
if m_next:
    mc_end = mc_start + 1 + m_next.start()
else:
    mc_end = len(src)

new_mc = r'''
def monte_carlo_pvalue(candidate, df_all, df_periph, null_method, B, seed):
    """
    Robust Monte Carlo p-value: collect T_null as a list and return (p_hat, T_null).
    This preserves the existing density/count/area logic but ensures T_null is always a list.
    """
    import numpy as _np
    T_obs = candidate.get("stat", None)
    try:
        B = int(B)
    except Exception:
        B = 0
    T_null = []
    for b in range(B):
        s = int(seed) + int(b) + 1
        if null_method == "shuffle_coords":
            df_null = sample_null_shuffle_coords(df_periph, s)
        elif null_method == "bootstrap":
            df_null = sample_null_bootstrap(df_periph, s)
        else:
            df_null = sample_null_radial_preserve(df_all, df_periph, s)

        dims = [c for c in df_null.columns if c.startswith("dim_")]
        X_null = df_null[dims].values

        # compute distances to candidate center if available
        try:
            center = candidate.get("center", None)
            if center is not None:
                center_arr = _np.array(center)
                dists = _np.linalg.norm(X_null - center_arr, axis=1)
            else:
                dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])
        except Exception:
            dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])

        # radius estimate (use candidate size if present)
        try:
            k = max(1, int(candidate.get("size", 1)))
            r = float(_np.partition(dists, k-1)[k-1]) if dists.size > 0 else 0.0
        except Exception:
            r = float(_np.median(dists)) if dists.size > 0 else 0.0

        try:
            count = int(_np.sum(dists <= r))
        except Exception:
            count = 0

        try:
            pts_within = X_null[dists <= r]
            area = convex_area(pts_within) if pts_within.shape[0] >= 3 else max(1e-6, r**2)
        except Exception:
            area = max(1e-6, r**2)

        try:
            stat_val = float(count) / float(area)
        except Exception:
            stat_val = float("nan")
        T_null.append(stat_val)

    # one-sided Monte Carlo p-value with small-sample correction
    try:
        p_hat = (1 + sum(1 for t in T_null if (not _np.isnan(t)) and (T_obs is not None and t >= T_obs))) / (1 + max(1, int(B)))
    except Exception:
        p_hat = (1 + sum(1 for t in T_null if not _np.isnan(t))) / (1 + max(1, int(B)))
    return p_hat, T_null
'''

# perform replacement
src = src[:mc_start] + new_mc + src[mc_end:]

# --- 2) Normalize null_samples_summary before saving in save_report ---
# Find the save_report function start
sr_start = src.find("def save_report(")
if sr_start == -1:
    print("ERROR: save_report not found in file.")
    sys.exit(3)

# find next top-level def after save_report to determine end
m_next2 = re.search(r"\ndef\s+\w+\s*\(", src[sr_start+1:], flags=re.MULTILINE)
if m_next2:
    sr_end = sr_start + 1 + m_next2.start()
else:
    sr_end = len(src)

save_block = src[sr_start:sr_end]

# replace the np.save(null_samples_summary.npy) block if present, otherwise append normalization before the end of save_report
if "np.save(os.path.join(outdir, \"null_samples_summary.npy\"" in save_block:
    # replace the single np.save call with normalized saving block
    save_block = re.sub(
        r"if\s+null_samples_summary:\s*?\n\s*?np\.save\([^\n]*null_samples_summary\.npy[^\n]*\)\s*",
        r'''if null_samples_summary:
        # Normalize entries so each element is an iterable (list) before saving.
        normalized = []
        for entry in null_samples_summary:
            if entry is None:
                normalized.append([])
                continue
            if isinstance(entry, dict) and 'null_samples' in entry:
                s = entry.get('null_samples')
            else:
                s = entry
            try:
                if hasattr(s, 'tolist') and not isinstance(s, (str, bytes)):
                    s_list = s.tolist()
                    normalized.append(list(s_list))
                    continue
            except Exception:
                pass
            if hasattr(s, '__iter__') and not isinstance(s, (str, bytes)):
                try:
                    normalized.append(list(s))
                    continue
                except Exception:
                    pass
            try:
                normalized.append([float(s)])
            except Exception:
                normalized.append([s])
        np.save(os.path.join(outdir, "null_samples_summary.npy"), np.array(normalized, dtype=object))
''',
        save_block,
        flags=re.DOTALL
    )
else:
    # fallback: insert normalization before the end of save_report (before the final print)
    save_block = save_block.replace(
        "    # save null samples summary if provided\n    if null_samples_summary:\n        np.save(os.path.join(outdir, \"null_samples_summary.npy\"), np.array(null_samples_summary, dtype=object))\n",
        '''    # save null samples summary if provided
    if null_samples_summary:
        # Normalize entries so each element is an iterable (list) before saving.
        normalized = []
        for entry in null_samples_summary:
            if entry is None:
                normalized.append([])
                continue
            if isinstance(entry, dict) and 'null_samples' in entry:
                s = entry.get('null_samples')
            else:
                s = entry
            try:
                if hasattr(s, 'tolist') and not isinstance(s, (str, bytes)):
                    s_list = s.tolist()
                    normalized.append(list(s_list))
                    continue
            except Exception:
                pass
            if hasattr(s, '__iter__') and not isinstance(s, (str, bytes)):
                try:
                    normalized.append(list(s))
                    continue
                except Exception:
                    pass
            try:
                normalized.append([float(s)])
            except Exception:
                normalized.append([s])
        np.save(os.path.join(outdir, "null_samples_summary.npy"), np.array(normalized, dtype=object))
'''
    )

# write back the modified save_report block
src = src[:sr_start] + save_block + src[sr_end:]

# write patched file
with io.open(fn, "w", encoding="utf8") as fh:
    fh.write(src)

print("Patched file written:", fn)
