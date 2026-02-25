import pandas as pd, json
pid = 3535.0
m = pd.read_csv("supplement/S-8/stability_map.csv", encoding="utf-8-sig")
sub = m[m["perm_id"]==pid].copy()
modal = sub["primary_label"].mode().iloc[0]
non_modal = sub[sub["primary_label"] != modal].sort_values("setting_id")
non_modal["flags"] = non_modal["flags_json"].apply(lambda x: ";".join(sorted([k for k,v in json.loads(x).items() if v])))
non_modal.to_csv(f"supplement/S-8/diagnostics/perm_{int(pid)}_non_modal.csv", index=False)
print("Wrote perm_{0}_non_modal.csv with {1} rows".format(int(pid), len(non_modal)))
