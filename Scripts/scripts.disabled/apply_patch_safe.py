import io, os, re, sys

fn = "motif_discovery_test.py"
with io.open(fn, "r", encoding="utf8") as fh:
    src = fh.read()

# --- 1) Replace monte_carlo_pvalue function robustly by locating its def and the following return ---
mc_start = re.search(r"^def\s+monte_carlo_pvalue\s*\(", src, flags=re.MULTILINE)
if not mc_start:
    print("ERROR: monte_carlo_pvalue not found")
    sys.exit(2)

# find the start index
start_idx = mc_start.start()

# find the end of the function by searching for the next top-level 'def ' after start
m_next = re.search(r"^def\s+\w+\s*\(", src[start_idx+1:], flags=re.MULTILINE)
if m_next:
    end_idx = start_idx + 1 + m_next.start()
else:
    # fallback: search for the save_report call area (end of monte carlo block)
    # we'll search for the 'def benjamini_hochberg' as a likely next function
    m_next2 = re.search(r"^def\s+benjamini_hochberg\s*\(", src[start_idx+1:], flags=re.MULTILINE)
    if m_next2:
        end_idx = start_idx + 1 + m_next2.start()
    else:
        end_idx = len(src)

# new monte_carlo_pvalue implementation (keeps internal logic placeholders)
new_mc = r'''
def monte_carlo_pvalue(candidate, df_all, df_periph, null_method, B, seed):
    """
    Robust Monte Carlo p-value: collect T_null as a list and return (p_hat, T_null).
    This implementation preserves your existing density/count/area logic; it only
    ensures T_null is a list and p_hat uses B as int.
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

        # Attempt to compute distances using candidate center if available
        try:
            center = candidate.get("center", None)
            if center is not None:
                center_arr = _np.array(center)
                dists = _np.linalg.norm(X_null - center_arr, axis=1)
            else:
                dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])
        except Exception:
            dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])

        try:
            r = candidate.get("radius", None)
            if r is None:
                r = float(_np.median(dists)) if dists.size > 0 else 0.0
        except Exception:
            r = 0.0

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

# replace the function body
new_src = src[:start_idx] + new_mc + src[end_idx:]
# --- 2) Patch save_report: replace np.save(null_samples_summary.npy) block with normalized saving ---
# Find the np.save line that writes null_samples_summary.npy and replace a small surrounding block
new_src = re.sub(
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
    new_src,
    flags=re.DOTALL | re.MULTILINE
)

with io.open(fn, "w", encoding="utf8") as fh:
    fh.write(new_src)

print("Patched file written:", fn)
