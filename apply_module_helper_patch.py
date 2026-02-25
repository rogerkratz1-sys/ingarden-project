#!/usr/bin/env python3
"""
apply_module_helper_patch.py

1) Restore the most recent backup if available (.bak_fixed, .bak2, .bak).
2) Remove any previously inserted snippet between the markers:
   "# --- begin write labels and candidate membership" and
   "# --- end write labels and candidate membership ---"
3) Insert a module-level helper near the top (after imports) that writes labels files.
4) Insert a small, indented call to that helper immediately after the first
   occurrence of "labels = db.labels_" so it runs inside the function scope.

Run from the repo folder:
    python apply_module_helper_patch.py
"""
from pathlib import Path
import shutil
import sys
import re

ROOT = Path(".")
SRC = ROOT / "motif_discovery_test.py"
BACKUPS = [
    ROOT / "motif_discovery_test.py.bak_fixed",
    ROOT / "motif_discovery_test.py.bak2",
    ROOT / "motif_discovery_test.py.bak",
    ROOT / "motif_discovery_test.py.broken4",
    ROOT / "motif_discovery_test.py.broken"
]
BACKUP_OUT = ROOT / "motif_discovery_test.py.pre_patch.bak"

if not SRC.exists():
    print(f"{SRC} not found. Run this from the folder containing motif_discovery_test.py")
    sys.exit(1)

# 1) restore latest backup as base if it exists
latest = None
for b in BACKUPS:
    if b.exists():
        latest = b
        break

if latest:
    print(f"Using backup {latest} as base.")
    base_text = latest.read_text(encoding="utf8")
else:
    print("No backup found; using current file as base.")
    base_text = SRC.read_text(encoding="utf8")

# 2) remove any existing snippet region between markers (if present)
start_marker = r"# --- begin write labels and candidate membership"
end_marker = r"# --- end write labels and candidate membership ---"

if start_marker in base_text and end_marker in base_text:
    before, rest = base_text.split(start_marker, 1)
    _, after = rest.split(end_marker, 1)
    base_text = before + after
    print("Removed existing snippet region between markers.")

# 3) prepare module-level helper to insert after imports
helper_text = r'''
# --- begin helper: write labels and candidate membership (module-level) ---
import pandas as _pd
from pathlib import Path as _Path

def write_labels_module(labels, perm_ids=None, outdir=None):
    """
    Write labels_per_perm.csv and candidate_membership_<label>.csv.
    labels: iterable of labels
    perm_ids: iterable of ids (optional)
    outdir: Path or string (optional)
    """
    try:
        _outdir = _Path(outdir) if outdir is not None else _Path('.')
    except Exception:
        _outdir = _Path('.')
    _outdir.mkdir(parents=True, exist_ok=True)

    try:
        if labels is None:
            print("Warning: write_labels_module called with labels=None")
            return
        if not isinstance(labels, list):
            try:
                labels = list(labels)
            except Exception:
                labels = [str(labels)]

        if perm_ids is None:
            perm_ids = [str(i) for i in range(len(labels))]
        else:
            try:
                perm_ids = [str(x) for x in perm_ids]
            except Exception:
                perm_ids = [str(x) for x in perm_ids]

        df_out = _pd.DataFrame({"perm_id": perm_ids, "label": [str(x) for x in labels]})
        df_out.to_csv(_outdir / "labels_per_perm.csv", index=False)

        for lab, group in df_out.groupby("label"):
            members = group["perm_id"].tolist()
            _pd.DataFrame({"perm_id": members}).to_csv(_outdir / f"candidate_membership_{lab}.csv", index=False)

        print("Wrote labels_per_perm.csv and candidate_membership_*.csv to", str(_outdir))
    except Exception as _e:
        print("Warning: write_labels_module failed:", _e)
# --- end helper ---
'''

# Insert helper after the last top-level import block.
# Heuristic: find the end of the initial import block (first blank line after imports).
lines = base_text.splitlines(keepends=True)
insert_idx = 0
# find first non-import, non-comment line after initial imports
for i, ln in enumerate(lines):
    stripped = ln.strip()
    if stripped == "":
        # skip blank lines
        continue
    # treat lines starting with "import" or "from" or comments as imports block
    if stripped.startswith("import ") or stripped.startswith("from ") or stripped.startswith("#"):
        insert_idx = i + 1
        continue
    # stop at first code line that is not import/comment
    break

# place helper after the imports block (insert_idx)
lines.insert(insert_idx, "\n" + helper_text + "\n")
print(f"Inserted module-level helper after line {insert_idx}.")

# 4) insert small call after first occurrence of "labels = db.labels_"
text_after_helper = "".join(lines)
pattern = r"(^[ \t]*labels\s*=\s*db\.labels_\s*$)"
m = re.search(pattern, text_after_helper, flags=re.MULTILINE)
if not m:
    print("Could not find 'labels = db.labels_' in file. Aborting without writing.")
    sys.exit(2)

# compute indentation from matched line
matched_line = m.group(1)
indent = re.match(r"^([ \t]*)", matched_line).group(1)

call_block = (
    indent + "try:\n"
    + indent + "    _perm_ids = locals().get('perm_ids', None) or globals().get('perm_ids', None)\n"
    + indent + "    _outdir = locals().get('outdir', None) or globals().get('outdir', None)\n"
    + indent + "    # if args.outdir exists, prefer it\n"
    + indent + "    if _outdir is None and globals().get('args', None) and getattr(globals().get('args'), 'outdir', None):\n"
    + indent + "        _outdir = globals().get('args').outdir\n"
    + indent + "    write_labels_module(labels, perm_ids=_perm_ids, outdir=_outdir)\n"
    + indent + "except Exception as _e:\n"
    + indent + "    print('Warning: write_labels_module call failed:', _e)\n"
)

# insert the call immediately after the matched line
start = m.start(1)
end = m.end(1)
new_text = text_after_helper[:end] + "\n" + call_block + text_after_helper[end:]

# backup current file before writing
shutil.copy2(SRC, BACKUP_OUT)
SRC.write_text(new_text, encoding="utf8")
print(f"Backed up current file to {BACKUP_OUT} and wrote patched file to {SRC}")
print("Patch complete. Now run the debug job (B small) and check the debug folder for labels_per_perm.csv.")