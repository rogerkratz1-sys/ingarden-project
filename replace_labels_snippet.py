#!/usr/bin/env python3
"""
replace_labels_snippet.py

Replace the previously inserted "write labels" snippet in motif_discovery_test.py
with a robust version that finds local variables and writes labels_per_perm.csv
and candidate_membership_*.csv into the run outdir.

Usage:
    python replace_labels_snippet.py
"""
from pathlib import Path
import sys, shutil

SRC = Path("motif_discovery_test.py")
BACKUP = SRC.with_suffix(".py.bak2")

if not SRC.exists():
    print(f"{SRC} not found.")
    sys.exit(1)

text = SRC.read_text(encoding="utf8")

old_start = "# --- begin write labels and candidate membership ---"
old_end = "# --- end write labels and candidate membership ---"

if old_start not in text:
    print("Could not find the previously inserted snippet. Aborting.")
    sys.exit(1)

NEW_SNIPPET = r'''
# --- begin write labels and candidate membership (robust to local scope) ---
import pandas as _pd
from pathlib import Path as _Path
import inspect as _inspect

# determine outdir (adapt if your script uses a different variable)
_outdir = None
if 'outdir' in globals():
    try:
        _outdir = _Path(outdir)
    except Exception:
        _outdir = None
if _outdir is None:
    _args = globals().get('args')
    if _args is not None and getattr(_args, 'outdir', None):
        try:
            _outdir = _Path(_args.outdir)
        except Exception:
            _outdir = None
if _outdir is None:
    _outdir = _Path('.')  # fallback to current folder
_outdir.mkdir(parents=True, exist_ok=True)

# helper to look up a name in locals then globals
def _lookup(name):
    # check current frame locals (walk up frames to find the frame where labels were created)
    frame = _inspect.currentframe()
    try:
        # walk up a few frames to find the function scope where labels exist
        for _ in range(6):
            if frame is None:
                break
            loc = frame.f_locals
            if name in loc:
                return loc[name]
            frame = frame.f_back
    finally:
        try:
            del frame
        except Exception:
            pass
    # fallback to globals
    return globals().get(name)

# try common names
perm_ids = _lookup('perm_ids') or _lookup('perm_id_list') or _lookup('permutation_ids') or _lookup('perm_id') or _lookup('perm_ids_list')
labels_vec = _lookup('labels') or _lookup('labels_vec') or _lookup('labels_per_perm') or _lookup('labels_array') or (_lookup('db').labels_ if _lookup('db') is not None else None)

# If labels is a numpy array or sklearn output, ensure it's a list of strings
if labels_vec is not None and not isinstance(labels_vec, list):
    try:
        labels_vec = list(labels_vec)
    except Exception:
        pass

# If perm_ids not found but there is a DataFrame with labels, try to use it
if (perm_ids is None or labels_vec is None) and 'labels_df' in globals():
    try:
        df_labels = globals()['labels_df']
        df_labels.to_csv(_outdir / "labels_per_perm.csv", index=False)
        if df_labels.shape[1] >= 2:
            label_col = df_labels.columns[1]
            for lab, group in df_labels.groupby(label_col):
                _pd.DataFrame({"perm_id": group.iloc[:,0].astype(str).tolist()}).to_csv(_outdir / f"candidate_membership_{lab}.csv", index=False)
        print("Wrote labels_per_perm.csv and candidate_membership_*.csv to", str(_outdir))
    except Exception:
        pass

# If we have perm_ids and labels_vec, write them out
if perm_ids is not None and labels_vec is not None:
    try:
        df_out = _pd.DataFrame({"perm_id": [str(x) for x in perm_ids], "label": [str(x) for x in labels_vec]})
        df_out.to_csv(_outdir / "labels_per_perm.csv", index=False)
        for lab, group in df_out.groupby("label"):
            members = group["perm_id"].tolist()
            _pd.DataFrame({"perm_id": members}).to_csv(_outdir / f"candidate_membership_{lab}.csv", index=False)
        print("Wrote labels_per_perm.csv and candidate_membership_*.csv to", str(_outdir))
    except Exception as _e:
        print("Warning: failed to write labels/membership:", _e)
else:
    print("Warning: perm_ids or labels_vec not found; labels_per_perm.csv not written.")
# --- end write labels and candidate membership ---
'''

# backup and replace
shutil.copy2(SRC, BACKUP)
parts = text.split(old_start)
prefix = parts[0]
suffix = parts[1]
if old_end in suffix:
    suffix = suffix.split(old_end, 1)[1]
else:
    print("Could not find end marker for the old snippet. Aborting.")
    sys.exit(1)

new_text = prefix + NEW_SNIPPET + suffix
SRC.write_text(new_text, encoding="utf8")
print(f"Replaced snippet and created backup {BACKUP}")