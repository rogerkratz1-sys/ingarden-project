#!/usr/bin/env python3
"""
plot_sensitivity.py
Usage:
  python scripts/plot_sensitivity.py
"""
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

def main(repo="."):
    repo = Path(repo).resolve()
    s8 = repo / "supplement" / "S-8"
    sens = pd.read_csv(s8 / "sensitivity_table_p85_90_95.csv")
    # Expect a column 'p_label' or similar; if not, adapt accordingly
    if "p_label" not in sens.columns:
        # try to infer from filename or add a default
        sens["p_label"] = sens.get("p", "p_unknown")
    plt.figure(figsize=(8,5))
    sns.lineplot(data=sens, x="B", y="T_obs", hue="p_label", marker="o")
    plt.xscale("log")
    plt.xlabel("B")
    plt.ylabel("T_obs")
    plt.title("Sensitivity of T_obs across p values")
    out = s8 / "fig_sensitivity_Tobs_by_B.png"
    plt.tight_layout()
    plt.savefig(out, dpi=300)
    print("Wrote:", out)

if __name__ == "__main__":
    main()