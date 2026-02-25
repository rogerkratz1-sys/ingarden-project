#!/usr/bin/env python3
"""
insert_write_labels_snippet.py

Finds the line 'labels = db.labels_' in motif_discovery_test.py and inserts a
defensive snippet that writes labels_per_perm.csv and candidate_membership_*.csv
into the run outdir. Creates a backup motif_discovery_test.py.bak before editing.

Usage:
    python insert_write_labels_snippet.py
"""
from pathlib import Path
import shutil
import sys

SRC = Path("motif_discovery_test.py")
BACKUP = SRC.with_suffix(".py.bak")

if not SRC.exists():
    print(f"Error: {SRC} not found in current directory ({Path.cwd()}).", file=sys.stderr)
    sys.exit(2)

# The snippet to insert (no leading/trailing blank lines beyond what's needed)
SNIPPET = r'''
# --- begin write labels and candidate membership ---
import pandas as _pd
from pathlib import Path as _Path

# determine outdir (adapt if your script uses a different variable)
_outdir = None
if 'outdir' in globals() and _outdir is None:
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

# try to find permutation id list and labels vector under common names
perm_ids = globals().get('perm_ids') or globals().get('perm_id_list') or globals().get('permutation_ids') or globals().get('perm_id') or globals().get('perm_ids_list')
labels_vec = globals().get('labels') or globals().get('labels_vec') or globals().get('labels_per_perm') or globals().get('labels_array')

# If labels is a numpy array or sklearn output (db.labels_), ensure it's a list of strings
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
        # also write membership files grouped by label (assume second column is label)
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
        # write membership files per label
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

# Read source
text = SRC.read_text(encoding="utf8")
lines = text.splitlines(keepends=True)

# Find the first occurrence of the target line
target = "labels = db.labels_"
insert_index = None
for i, line in enumerate(lines):
    if target in line:
        insert_index = i + 1  # insert after this line
        # capture indentation of the target line to indent snippet accordingly
        leading_ws = line[:len(line) - len(line.lstrip())]
        break

if insert_index is None:
    print(f"Error: could not find the line containing '{target}' in {SRC}.", file=sys.stderr)
    sys.exit(3)

# Prepare indented snippet: indent each non-empty line by the same leading whitespace
snippet_lines = SNIPPET.splitlines()
indented = []
for s in snippet_lines:
    if s.strip() == "":
        indented.append("\n")
    else:
        indented.append(leading_ws + s + "\n")

# Backup original
shutil.copy2(SRC, BACKUP)
print(f"Backup created: {BACKUP}")

# Insert snippet
new_lines = lines[:insert_index] + indented + lines[insert_index:]
SRC.write_text("".join(new_lines), encoding="utf8")
print(f"Inserted snippet after line containing '{target}' in {SRC}.")
print("Done.")