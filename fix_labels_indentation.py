#!/usr/bin/env python3
from pathlib import Path
import shutil
import sys

ROOT = Path(".")
SRC = ROOT / "motif_discovery_test.py"
BACKUP_CANDIDATES = [
    ROOT / "motif_discovery_test.py.bak_fixed",
    ROOT / "motif_discovery_test.py.bak2",
    ROOT / "motif_discovery_test.py.bak",
]
BROKEN = ROOT / "motif_discovery_test.py.broken4"

SNIPPET_LINES = [
    "# --- begin write labels and candidate membership (robust to local scope, fixed) ---",
    "import pandas as _pd",
    "from pathlib import Path as _Path",
    "import inspect as _inspect",
    "",
    "# determine outdir (adapt if your script uses a different variable)",
    "_outdir = None",
    "if 'outdir' in globals():",
    "    try:",
    "        _outdir = _Path(outdir)",
    "    except Exception:",
    "        _outdir = None",
    "if _outdir is None:",
    "    _args = globals().get('args')",
    "    if _args is not None and getattr(_args, 'outdir', None):",
    "        try:",
    "            _outdir = _Path(_args.outdir)",
    "        except Exception:",
    "            _outdir = None",
    "if _outdir is None:",
    "    _outdir = _Path('.')  # fallback to current folder",
    "_outdir.mkdir(parents=True, exist_ok=True)",
    "",
    "# helper to look up a name in locals then globals",
    "def _lookup(name):",
    "    frame = _inspect.currentframe()",
    "    try:",
    "        for _ in range(8):",
    "            if frame is None:",
    "                break",
    "            loc = frame.f_locals",
    "            if name in loc:",
    "                return loc[name]",
    "            frame = frame.f_back",
    "    finally:",
    "        try:",
    "            del frame",
    "        except Exception:",
    "            pass",
    "    return globals().get(name)",
    "",
    "# try common names for perm ids and labels",
    "perm_ids = _lookup('perm_ids') or _lookup('perm_id_list') or _lookup('permutation_ids') or _lookup('perm_id') or _lookup('perm_ids_list')",
    "",
    "# Safely obtain labels: check explicit names first, then try db.labels_ without using truthiness",
    "labels_candidate = _lookup('labels') or _lookup('labels_vec') or _lookup('labels_per_perm') or _lookup('labels_array')",
    "db_obj = _lookup('db')",
    "db_labels = None",
    "if db_obj is not None:",
    "    db_labels = getattr(db_obj, 'labels_', None)",
    "labels_vec = labels_candidate if labels_candidate is not None else db_labels",
    "",
    "# If labels is a numpy array or sklearn output, ensure it's a list of strings",
    "if labels_vec is not None and not isinstance(labels_vec, list):",
    "    try:",
    "        labels_vec = list(labels_vec)",
    "    except Exception:",
    "        pass",
    "",
    "# If perm_ids not found but there is a DataFrame with labels, try to use it",
    "if (perm_ids is None or labels_vec is None) and 'labels_df' in globals():",
    "    try:",
    "        df_labels = globals()['labels_df']",
    "        df_labels.to_csv(_outdir / \"labels_per_perm.csv\", index=False)",
    "        if df_labels.shape[1] >= 2:",
    "            label_col = df_labels.columns[1]",
    "            for lab, group in df_labels.groupby(label_col):",
    "                _pd.DataFrame({\"perm_id\": group.iloc[:,0].astype(str).tolist()}).to_csv(_outdir / f\"candidate_membership_{lab}.csv\", index=False)",
    "        print(\"Wrote labels_per_perm.csv and candidate_membership_*.csv to\", str(_outdir))",
    "    except Exception:",
    "        pass",
    "",
    "# If we have perm_ids and labels_vec, write them out",
    "if perm_ids is not None and labels_vec is not None:",
    "    try:",
    "        df_out = _pd.DataFrame({\"perm_id\": [str(x) for x in perm_ids], \"label\": [str(x) for x in labels_vec]})",
    "        df_out.to_csv(_outdir / \"labels_per_perm.csv\", index=False)",
    "        for lab, group in df_out.groupby(\"label\"):",
    "            members = group[\"perm_id\"].tolist()",
    "            _pd.DataFrame({\"perm_id\": members}).to_csv(_outdir / f\"candidate_membership_{lab}.csv\", index=False)",
    "        print(\"Wrote labels_per_perm.csv and candidate_membership_*.csv to\", str(_outdir))",
    "    except Exception as _e:",
    "        print(\"Warning: failed to write labels/membership:\", _e)",
    "else:",
    "    print(\"Warning: perm_ids or labels_vec not found; labels_per_perm.csv not written.\")",
    "# --- end write labels and candidate membership (robust to local scope, fixed) ---",
    ""
]
def find_latest_backup():
    for b in BACKUP_CANDIDATES:
        if b.exists():
            return b
    return None

def main():
    if not SRC.exists():
        print('Error: motif_discovery_test.py not found in current directory.')
        sys.exit(1)

    latest = find_latest_backup()
    if latest is None:
        print('No backup found (.bak_fixed, .bak2, .bak). Aborting.')
        sys.exit(2)

    base_text = latest.read_text(encoding='utf8')
    lines = base_text.splitlines(keepends=True)

    target = 'labels = db.labels_'
    insert_idx = None
    leading_ws = ''
    for i, ln in enumerate(lines):
        if target in ln:
            insert_idx = i + 1
            leading_ws = ln[:len(ln) - len(ln.lstrip())]
            break

    if insert_idx is None:
        print(f"Could not find '{target}' in backup {latest}. Aborting.")
        sys.exit(3)

    indented = []
    for s in SNIPPET_LINES:
        if s == '':
            indented.append('\n')
        else:
            indented.append(leading_ws + s + '\n')

    if SRC.exists():
        shutil.copy2(SRC, BROKEN)
        print(f"Backed up current file to {BROKEN}")

    new_lines = lines[:insert_idx] + indented + lines[insert_idx:]
    SRC.write_text(''.join(new_lines), encoding='utf8')
    print(f"Restored from {latest} and inserted snippet after '{target}'. Wrote fixed file to {SRC}")

if __name__ == '__main__':
    main()
