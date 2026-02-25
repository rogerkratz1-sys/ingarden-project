#!/usr/bin/env python3
r"""
generate_S8_texts.py

Reads S8_null_samples_summary.csv and motif_candidates_test.csv from your run folders
and writes:
 - supplement/S-8/S8_null_histograms.txt
 - supplement/S-8/sensitivity_table_p85_90_95.csv
 - supplement/S-8/S8_readme.txt

Run from: C:\Users\ctint\Desktop\Scripts\repo_candidate
Usage:
  python generate_S8_texts.py
"""
import csv
import json
from pathlib import Path
from datetime import datetime
import subprocess

BASE = Path(r"C:\Users\ctint\Desktop\Scripts")
ROBUST = BASE / "motif_results_robustness"
OUTDIR = BASE / "supplement" / "S-8"
OUTDIR.mkdir(parents=True, exist_ok=True)

# Candidate run folder name patterns to check (handles _B1000 variants)
candidates = [
    ("85", ROBUST.glob("peripheral_85*")),
    ("90", ROBUST.glob("peripheral_90*")),
    ("95", ROBUST.glob("peripheral_95*")),
    # fallback: top-level motif_results
    ("", (BASE / "motif_results",))
]

# Discover runs that contain both files
runs = []
for pct, gen in candidates:
    for f in gen:
        if not isinstance(f, Path):
            f = Path(f)
        summary = f / "S8_null_samples_summary.csv"
        cands = f / "motif_candidates_test.csv"
        if summary.exists() and cands.exists():
            runs.append({"p": int(pct) if pct else "", "dir": f, "summary": summary, "cands": cands})

if not runs:
    print("No run folders found with both S8_null_samples_summary.csv and motif_candidates_test.csv. Exiting.")
    raise SystemExit(1)

# Read and index summaries and candidate tables
summaries = {}
candidates_by_run = {}
for r in runs:
    p = r["p"]
    srows = []
    with r["summary"].open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cid = row.get("candidate_id")
            srows.append(row)
    summaries[p] = srows

    cro = []
    with r["cands"].open("r", newline="") as fh:
        reader = csv.DictReader(fh)
        for row in reader:
            cro.append(row)
    candidates_by_run[p] = cro

# Build sensitivity table rows (one row per candidate per run)
sensitivity_rows = []
for r in runs:
    p = r["p"]
    meta_path = r["dir"] / "meta.json"
    B = ""
    if meta_path.exists():
        try:
            meta = json.loads(meta_path.read_text())
            B = meta.get("B", "")
        except Exception:
            B = ""
    for cand in candidates_by_run[p]:
        sensitivity_rows.append({
            "run_p": p,
            "B": B,
            "candidate_id": cand.get("label", ""),
            "n_points": cand.get("size", ""),
            "T_obs": cand.get("stat", ""),
            "raw_p_value": cand.get("pval", ""),
            "BH_selected": "yes" if cand.get("selected", "").strip().lower() == "true" else "no"
        })

# Write sensitivity table CSV
sens_path = OUTDIR / "sensitivity_table_p85_90_95.csv"
fieldnames = ["run_p","B","candidate_id","n_points","T_obs","raw_p_value","BH_selected"]
with sens_path.open("w", newline="") as fh:
    writer = csv.DictWriter(fh, fieldnames=fieldnames)
    writer.writeheader()
    for row in sorted(sensitivity_rows, key=lambda x: (str(x["run_p"]), str(x["candidate_id"]))):
        writer.writerow(row)

# Build histogram captions from summaries
captions = []
for r in runs:
    p = r["p"]
    for s in summaries[p]:
        cid = s.get("candidate_id", "")
        T_obs = s.get("T_obs", "")
        null_min = s.get("null_min", "")
        null_1pct = s.get("null_1pct", "")
        null_5pct = s.get("null_5pct", "")
        null_25pct = s.get("null_25pct", "")
        null_median = s.get("null_median", "")
        null_75pct = s.get("null_75pct", "")
        null_95pct = s.get("null_95pct", "")
        null_99pct = s.get("null_99pct", "")
        null_max = s.get("null_max", "")
        raw_p = s.get("raw_p_value", "")
        B = s.get("B", "")
        bh = s.get("BH_selected", "")
        if not bh:
            match = [c for c in candidates_by_run[p] if c.get("label","") == cid]
            if match:
                bh = "yes" if match[0].get("selected","").strip().lower() == "true" else "no"
        caption = (
            f"Candidate {cid} (p={p})\n"
            f"Observed cluster density T_obs = {T_obs}\n"
            f"Null summary: null_min = {null_min}; null_1pct = {null_1pct}; null_5pct = {null_5pct}; "
            f"null_25pct = {null_25pct}; null_median = {null_median}; null_75pct = {null_75pct}; "
            f"null_95pct = {null_95pct}; null_99pct = {null_99pct}; null_max = {null_max}\n"
            f"Monte Carlo p = {raw_p}\n"
            f"BH_selected = {bh}\n"
            f"Interpretation: Observed density compared to radial-preserving null for p={p} (B={B}).\n"
        )
        captions.append(caption)

# Write captions file
hist_path = OUTDIR / "S8_null_histograms.txt"
with hist_path.open("w", encoding="utf-8") as fh:
    fh.write("\n---\n".join(captions))

# Write readme/provenance
git_hash = "<commit-hash-not-found>"
try:
    git_hash = subprocess.check_output(["git","-C", str(BASE), "rev-parse", "--short", "HEAD"], stderr=subprocess.DEVNULL).decode().strip()
except Exception:
    pass

prov = f"Provenance: assembled_date={datetime.utcnow().strftime('%Y-%m-%d')}, git_commit={git_hash}, assembler=generate_S8_texts.py\n"
prov += "Commands used to produce diagnostics: see run logs in each run folder.\n"
prov += "Notes: S8_null_samples_summary.csv files were read from each run folder and used to create the captions and sensitivity table.\n"
(OUTDIR / "S8_readme.txt").write_text(prov, encoding="utf-8")

print("Wrote:")
print(" -", sens_path)
print(" -", hist_path)
print(" -", OUTDIR / "S8_readme.txt")