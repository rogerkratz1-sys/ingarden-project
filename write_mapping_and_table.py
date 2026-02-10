#!/usr/bin/env python3
"""
Write cluster->motif mappings and the full per-permutation table to CSV files.
Run this script from the folder containing motif_stability_per_permutation.csv,
ParseA/outputs/cluster_labels_parseA.csv, and ParseB/outputs/cluster_labels_parseB.csv.
"""
import os
import pandas as pd

ROOT = os.getcwd()
CANON = os.path.join(ROOT, "motif_stability_per_permutation.csv")
PARSEA = os.path.join(ROOT, "ParseA", "outputs", "cluster_labels_parseA.csv")
PARSEB = os.path.join(ROOT, "ParseB", "outputs", "cluster_labels_parseB.csv")
OUTDIR = os.path.join(ROOT, "outputs")
os.makedirs(OUTDIR, exist_ok=True)

def load_csv(path):
    if not os.path.exists(path):
        raise FileNotFoundError(f"Missing file: {path}")
    return pd.read_csv(path)

# Load files
df_can = load_csv(CANON)
df_a = load_csv(PARSEA)
df_b = load_csv(PARSEB)

# Normalize index column name to 'index'
def find_index_col(df):
    for c in df.columns:
        if c.lower() in ('index','perm_index','perm','id'):
            return c
    return None

idx_can = find_index_col(df_can)
if idx_can is None:
    raise SystemExit("Cannot find index column in canonical file.")
df_can = df_can.rename(columns={idx_can: 'index'})

# detect canonical label column and rename to 'primary_label_canonical'
can_label = None
for c in df_can.columns:
    if any(k in c.lower() for k in ['orig_motif','primary_label','modal_label','motif','label','cluster']):
        can_label = c
        break
if can_label is None:
    raise SystemExit("Cannot detect canonical label column.")
df_can = df_can.rename(columns={can_label: 'primary_label_canonical'})

# prepare parse files: rename index and cluster columns
def prepare_parse(df):
    idx = find_index_col(df)
    if idx:
        df = df.rename(columns={idx: 'index'})
    cluster_col = None
    for c in df.columns:
        if any(k in c.lower() for k in ['cluster','label','primary_label','motif']) and c.lower() != 'index':
            cluster_col = c
            break
    if cluster_col:
        df = df.rename(columns={cluster_col: 'cluster'})
    return df

df_a = prepare_parse(df_a)
df_b = prepare_parse(df_b)

# Merge canonical with parse labels
df = df_can.copy()
if df_a is not None:
    df = df.merge(df_a[['index','cluster']].drop_duplicates(), on='index', how='left').rename(columns={'cluster':'cluster_parseA'})
if df_b is not None:
    df = df.merge(df_b[['index','cluster']].drop_duplicates(), on='index', how='left').rename(columns={'cluster':'cluster_parseB'})

# Build majority-vote mapping cluster -> canonical motif
def build_mapping(df, cluster_col):
    if cluster_col not in df.columns:
        return {}
    mapping = {}
    groups = df.dropna(subset=[cluster_col, 'primary_label_canonical']).groupby(cluster_col)
    for cluster_val, g in groups:
        top = g['primary_label_canonical'].value_counts().idxmax()
        mapping[cluster_val] = top
    return mapping

map_a = build_mapping(df, 'cluster_parseA')
map_b = build_mapping(df, 'cluster_parseB')

# Apply mapping to create relabeled parse columns
df['parseA_mapped'] = df['cluster_parseA'].map(map_a)
df['parseB_mapped'] = df['cluster_parseB'].map(map_b)

# Select and write mapping CSVs
map_a_df = pd.DataFrame(sorted(map_a.items()), columns=['cluster_parseA','mapped_motif'])
map_b_df = pd.DataFrame(sorted(map_b.items()), columns=['cluster_parseB','mapped_motif'])
map_a_df.to_csv(os.path.join(OUTDIR, "cluster_to_motif_mapping_parseA.csv"), index=False)
map_b_df.to_csv(os.path.join(OUTDIR, "cluster_to_motif_mapping_parseB.csv"), index=False)

# Prepare full per-permutation table and write
cols_out = ['index','primary_label_canonical','cluster_parseA','parseA_mapped','cluster_parseB','parseB_mapped']
# include stability fraction if present
stab_col = None
for c in df.columns:
    if 'stability' in c.lower():
        stab_col = c
        break
if stab_col:
    cols_out.append(stab_col)
permutation_table = df[cols_out]
permutation_table.to_csv(os.path.join(OUTDIR, "permutation_label_table.csv"), index=False)

print("Wrote:")
print(" -", os.path.join(OUTDIR, "cluster_to_motif_mapping_parseA.csv"))
print(" -", os.path.join(OUTDIR, "cluster_to_motif_mapping_parseB.csv"))
print(" -", os.path.join(OUTDIR, "permutation_label_table.csv"))