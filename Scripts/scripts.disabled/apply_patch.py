import re, io, sys, os

fn = "motif_discovery_test.py"
if not os.path.exists(fn):
    print("ERROR: file not found:", fn)
    sys.exit(2)

with io.open(fn, "r", encoding="utf8") as fh:
    src = fh.read()

# --- Replace monte_carlo_pvalue function ---
mc_pattern = re.compile(
    r"def\s+monte_carlo_pvalue\s*\(.*?\):\s*.*?return\s+.*?$",
    re.DOTALL | re.MULTILINE
)

mc_repl = r"""def monte_carlo_pvalue(candidate, df_all, df_periph, null_method, B, seed):
    \"\"\"Robust Monte Carlo p-value: always collects T_null as a list and returns (p_hat, T_null).\"\"\"
    import numpy as _np
    T_obs = candidate.get("stat", None)
    # ensure integer B
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

        # Existing code expects r and dists to be computed from candidate center.
        # Try to reuse candidate center if present; otherwise fallback to simple density.
        try:
            center = candidate.get("center", None)
            if center is not None:
                import numpy as _np2
                center_arr = _np2.array(center)
                dists = _np2.linalg.norm(X_null - center_arr, axis=1)
            else:
                # fallback: pairwise distances to first point
                dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])
        except Exception:
            dists = _np.linalg.norm(X_null - X_null[0], axis=1) if X_null.shape[0] > 0 else _np.array([])

        # estimate radius r from candidate size if available, else median distance
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
        # fallback if T_obs is None or other issue
        p_hat = (1 + sum(1 for t in T_null if not _np.isnan(t))) / (1 + max(1, int(B)))
    return p_hat, T_null
"""

if mc_pattern.search(src):
    src = mc_pattern.sub(mc_repl, src, count=1)
    print("Replaced monte_carlo_pvalue function.")
else:
    print("Warning: monte_carlo_pvalue pattern not found. No replacement made.")

# --- Normalize null_samples_summary before saving in save_report ---
# Find the save_report function and replace the np.save block for null_samples_summary
save_pattern = re.compile(r"(def\s+save_report\s*\(.*?\):\s*.*?)(\n\s*# save null samples summary if provided\s*\n\s*if\s+null_samples_summary:.*?np\.save\(.*?\)\s*)", re.DOTALL | re.MULTILINE)
if save_pattern.search(src):
    def_block = save_pattern.search(src).group(1)
    # replacement block that normalizes entries to lists
    save_repl_block = r"""\1
    # save null samples summary if provided
    if null_samples_summary:
        # Normalize entries so each element is an iterable (list) before saving.
        normalized = []
        for entry in null_samples_summary:
            if entry is None:
                normalized.append([])
                continue
            # If entry is a dict with 'null_samples' key, extract it
            if isinstance(entry, dict) and 'null_samples' in entry:
                s = entry.get('null_samples')
            else:
                s = entry
            # convert numpy arrays to lists
            try:
                if hasattr(s, 'tolist') and not isinstance(s, (str, bytes)):
                    s_list = s.tolist()
                    normalized.append(list(s_list))
                    continue
            except Exception:
                pass
            # if iterable (list/tuple) and not string, convert to list
            if hasattr(s, '__iter__') and not isinstance(s, (str, bytes)):
                try:
                    normalized.append(list(s))
                    continue
                except Exception:
                    pass
            # otherwise wrap scalar into single-element list
            try:
                normalized.append([float(s)])
            except Exception:
                normalized.append([s])
        np.save(os.path.join(outdir, "null_samples_summary.npy"), np.array(normalized, dtype=object))
"""
    src = save_pattern.sub(save_repl_block, src, count=1)
    print("Patched save_report null_samples_summary saving block.")
else:
    print("Warning: save_report pattern not found. No replacement made.")

# Write patched file
with io.open(fn, "w", encoding="utf8") as fh:
    fh.write(src)

print("Patched file written:", fn)
