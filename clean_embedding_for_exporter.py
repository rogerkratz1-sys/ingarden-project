import pandas as pd
import numpy as np
from pathlib import Path

p = Path('data/embeddings_5000_dim8.csv')
out_csv = Path('data/embeddings_5000_dim8.cleaned.csv')
out_npy = Path('data/embedding.npy')

# Read with header row, drop non-numeric index column if present
df = pd.read_csv(p, header=0, dtype=str)

# If a leading index column exists named 'perm_pos' or similar, drop it
for idx_name in ['perm_pos', 'id', 'index', 'perm']:
    if idx_name in df.columns:
        df = df.drop(columns=[idx_name])
        break

# Coerce to numeric, drop any fully-empty columns/rows
df = df.apply(pd.to_numeric, errors='coerce').dropna(axis=1, how='all').dropna(axis=0, how='all')

# Save cleaned CSV (no header) and numpy array
df.to_csv(out_csv, index=False, header=False, float_format='%.12g')
np.save(out_npy, df.values.astype(float))

print('Wrote cleaned CSV:', out_csv)
print('Wrote numpy file:', out_npy)
print('Cleaned shape:', df.shape)
