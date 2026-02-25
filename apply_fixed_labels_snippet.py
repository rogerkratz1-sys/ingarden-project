#!/usr/bin/env python3
"""
apply_fixed_labels_snippet.py

Replace the existing "write labels" snippet in motif_discovery_test.py with a
safe, local-scope aware version that writes labels_per_perm.csv and
candidate_membership_<label>.csv into the run outdir.

Usage:
    python apply_fixed_labels_snippet.py
"""
from pathlib import Path
import shutil
import sys

SRC = Path("motif_discovery_test.py")
if not SRC.exists():
    print(f"Error: {SRC} not found in current directory.")
    sys.exit(1)

# Backup current file
BACKUP = SRC.with_suffix(".py.bak_fixed")
shutil.copy2(SRC, BACKUP)
print(f"Backed up current file to {BACKUP}")

text = SRC.read_text(encoding="utf8")

# Markers for the old snippet region
old_start_marker = "# --- begin write labels and candidate membership"
old_end_marker = "# --- end write labels and candidate membership ---"

if old_start_marker not in text or old_end_marker not in text:
    print("Error: Could not find the previously inserted snippet markers in motif_discovery_test.py.")
    sys.exit(1)

# Fixed snippet to insert
NEW_SNIPPET = r'''
# --- begin write labels and candidate membership (robust to local scope, fixed) ---
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
    frame = _inspect.currentframe()
    try:
        for _ in range(8):
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
    return globals().get(name)

# try common names for perm ids and labels
perm_ids = _lookup('perm_ids') or _lookup('perm_id_list') or _lookup('permutation_ids') or _lookup('perm_id') or _lookup('perm_ids_list')

# Safely obtain labels: check explicit names first, then try db.labels_ without using truthiness
labels_candidate = _lookup('labels') or _lookup('labels_vec') or _lookup('labels_per_perm') or _lookup('labels_array')
db_obj = _lookup('db')
db_labels = None
if db_obj is not None:
    db_labels = getattr(db_obj, 'labels_', None)
# prefer explicit candidate if present, otherwise use db_labels
labels_vec = labels_candidate if labels_candidate is not None else db_labels

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
# --- end write labels and candidate membership (robust to local scope, fixed) ---
'''

# Replace the old snippet region with the new snippet
prefix, rest = text.split(old_start_marker, 1)
if old_end_marker not in rest:
    print("Error: End marker not found after start marker. Aborting.")
    sys.exit(1)
_, suffix = rest.split(old_end_marker, 1)

new_text = prefix + NEW_SNIPPET + suffix
SRC.write_text(new_text, encoding="utf8")
print("Replaced old snippet with the fixed snippet successfully.")