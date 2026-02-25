# supplement/S-8/scripts/assemble_injection.py
import glob, os, pandas as pd
out = "supplement/S-8/S8_injection_power_curves.txt"
os.makedirs(os.path.dirname(out), exist_ok=True)
files = sorted(glob.glob("motif_results_robustness/peripheral_95/injection_results/*.csv"))
if not files:
    raise SystemExit("No injection result CSVs found in motif_results_robustness/peripheral_95/injection_results/")
rows = []
for f in files:
    df = pd.read_csv(f)
    if not {'inject_size','sigma','detected'}.issubset(df.columns):
        continue
    grouped = df.groupby(['inject_size','sigma']).agg(detection_rate=('detected','mean'), trials=('detected','size')).reset_index()
    rows.append(grouped)
if not rows:
    raise SystemExit("No valid injection CSVs with required columns found.")
pd.concat(rows).to_csv(out, index=False)
print("Wrote", out)