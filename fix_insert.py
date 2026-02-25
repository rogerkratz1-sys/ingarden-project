#!/usr/bin/env python3
"""
fix_insert.py

Restore motif_discovery_test.py from backup and re-insert the robust snippet
immediately after the line 'labels = db.labels_' preserving indentation.

Usage:
    python fix_insert.py
"""
from pathlib import Path
import shutil
import sys

ROOT = Path(".")
SRC = ROOT / "motif_discovery_test.py"
BACKUPS = [ROOT / "motif_discovery_test.py.bak2", ROOT / "motif_discovery_test.py.bak"]
BROKEN = ROOT / "motif_discovery_test.py.broken"

# The snippet to insert (no leading/trailing blank lines beyond what's needed)
SNIPPET = [
"# --- begin write labels and candidate membership (robust to local scope) ---",
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
"    # check current frame locals (walk up frames to find the frame where labels were created)",
"    frame = _inspect.currentframe()",
"    try:",
"        # walk up a few frames to find the function scope where labels exist",
"        for _ in range(6):",
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
"    # fallback to globals",
"    return globals().get(name)",
"",
"# try common names",
"perm_ids = _lookup('perm_ids') or _lookup('perm_id_list') or _lookup('permutation_ids') or _lookup('perm_id') or _lookup('perm_ids_list')",
"labels_vec = _lookup('labels') or _lookup('labels_vec') or _lookup('labels_per_perm') or _lookup('labels_array') or (_lookup('db').labels_ if _lookup('db') is not None else None)",
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
"# --- end write labels and candidate membership ---",
""
]

def find_backup():
    for b in BACKUPS:
        if b.exists():
            return b
    return None

def main():
    # locate backup
    backup = find_backup()
    if backup is None:
        print("No backup found (looked for .bak2 and .bak). Aborting.", file=sys.stderr)
        sys.exit(1)

    # restore backup content as base
    base_text = backup.read_text(encoding="utf8")
    lines = base_text.splitlines(keepends=True)

    # find target line
    target = "labels = db.labels_"
    insert_idx = None
    leading_ws = ""
    for i, ln in enumerate(lines):
        if target in ln:
            insert_idx = i + 1
            leading_ws = ln[:len(ln) - len(ln.lstrip())]
            break

    if insert_idx is None:
        print(f"Could not find the target line '{target}' in backup {backup}. Aborting.", file=sys.stderr)
        sys.exit(2)

    # prepare indented snippet
    indented = []
    for s in SNIPPET:
        if s == "":
            indented.append("\n")
        else:
            indented.append(leading_ws + s + "\n")

    # backup current broken file if exists
    if SRC.exists():
        shutil.copy2(SRC, BROKEN)
        print(f"Backed up current file to {BROKEN}")

    # write new file: prefix + snippet + suffix
    new_lines = lines[:insert_idx] + indented + lines[insert_idx:]
    SRC.write_text("".join(new_lines), encoding="utf8")
    print(f"Restored from {backup} and inserted snippet after '{target}'.")
    print("Wrote fixed file to", SRC)

if __name__ == "__main__":
    main()