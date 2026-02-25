# inspect_cliff_bootstrap.py
import pickle, os, numpy as np
p = r".\\circularity\\heldout_summary.pkl"
with open(p, "rb") as fh:
    obj = pickle.load(fh)
cb = obj.get("cliff_bootstrap", None)
print("cliff_bootstrap type:", type(cb))
if isinstance(cb, dict):
    for k,v in cb.items():
        print("\nKEY:", repr(k))
        print("  TYPE:", type(v))
        try:
            import pandas as pd
            if isinstance(v, pd.Series):
                arr = v.dropna().to_numpy()
                print("  SERIES length:", len(arr), "sample:", arr[:10])
            elif isinstance(v, pd.DataFrame):
                print("  DATAFRAME shape:", v.shape)
                print("  COLUMNS:", list(v.columns))
                print("  SAMPLE (first 5 rows):")
                print(v.head().to_string())
            elif isinstance(v, (list, tuple, np.ndarray)):
                arr = np.asarray(v)
                print("  ARRAY shape:", arr.shape, "dtype:", arr.dtype, "sample:", arr.ravel()[:10])
            else:
                print("  REPR (truncated):", repr(v)[:400])
        except Exception as e:
            print("  (inspect error)", e)
else:
    print("cliff_bootstrap not a dict or missing; repr:", repr(cb)[:400])