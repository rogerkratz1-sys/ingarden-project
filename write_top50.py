import pandas as pd
s = pd.read_csv("supplement/S-8/stability_summary.csv", encoding="utf-8-sig")
s.sort_values("stability_score").head(50).to_csv("supplement/S-8/diagnostics/top_50_unstable.csv", index=False)
print("Wrote supplement/S-8/diagnostics/top_50_unstable.csv")
