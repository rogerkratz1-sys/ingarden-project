#!/usr/bin/env python3
"""
Map parse cluster IDs to canonical motif names by majority vote, then recompute
Adjusted Rand Index and Cohen's kappa. Prints per-motif preservation and writes
a summary CSV to the outputs folder.
"""
import os
import sys
import pandas as pd
import numpy as np
from sklearn.metrics import adjusted_rand_score, cohen_kappa_score

ROOT = os.getcwd()
CANON = os.path.join(ROOT, "motif_stability_per_permutation.csv")
PARSEA = os.path.join(ROOT, "ParseA", "outputs", "cluster_labels_parseA.csv")
PARSEB = os.path.join(ROOT, "ParseB", "outputs", "cluster_labels_parseB.csv")
OUTDIR = os.path.join(ROOT, "outputs")
os.makedirs(OUTDIR, exist_ok=True)
OUT_SUM = os.path.join(OUTDIR, "segmentation_agreement_mapped.csv")

def load_csv(path):
    if not os.path.exists(path):
        print("Missing:", path)
        return None
    try:
        return pd.read_csv(path)
    except Exception as e:
        print(f"Failed to read {path}: {e}")
        return None

df_can = load_csv(CANON)
df_a = load_csv(PARSEA)
df_b = load_csv(PARSEB)
if df_can is None:
    sys.exit("Canonical file not found. Place motif_stability_per_permutation.csv in the working folder.")

# find index column
def find_index_col(df):
    for c in df.columns:
        if c.lower() in ('index','perm_index','perm','id'):
            return c
    return None

# detect canonical label column
def find_label_col(df):
    for c in df.columns:
        if any(k in c.lower() for k in ['orig_motif','primary_label','modal_label','motif','label','cluster']):
            return c
    return None

# normalize canonical dataframe
idx_can = find_index_col(df_can)
if idx_can is None:
    sys.exit("Cannot find index column in canonical file.")
df_can = df_can.rename(columns={idx_can: 'index'})

can_label = find_label_col(df_can)
if can_label is None:
    sys.exit("Cannot detect canonical label column.")
df_can = df_can.rename(columns={can_label: 'primary_label_canonical'})

# prepare parse files: rename index and cluster columns
def prepare_parse(df):
    if df is None:
        return None
    idx = find_index_col(df)
    if idx:
        df = df.rename(columns={idx: 'index'})
    # find cluster-like column
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

print("ParseA mapping sample (cluster -> canonical):")
for k,v in list(map_a.items())[:20]:
    print(k, "->", v)
print("ParseB mapping sample (cluster -> canonical):")
for k,v in list(map_b.items())[:20]:
    print(k, "->", v)

# Apply mapping to create relabeled parse columns
def apply_map(series, mapping):
    if series is None:
        return None
    return series.map(mapping)

if map_a:
    df['parseA_mapped'] = apply_map(df['cluster_parseA'], map_a)
if map_b:
    df['parseB_mapped'] = apply_map(df['cluster_parseB'], map_b)

# Compute median stability_fraction if present
stab_col = None
for c in df.columns:
    if 'stability' in c.lower():
        stab_col = c
        break
median_stab = df[stab_col].median() if stab_col in df.columns else np.nan
iqr_stab = (df[stab_col].quantile(0.75) - df[stab_col].quantile(0.25)) if stab_col in df.columns else np.nan

results = {'median_stability_fraction': median_stab, 'iqr_stability_fraction': iqr_stab}

# Agreement computations on mapped labels
def compute_agreement(col_parse):
    sub = df.dropna(subset=['primary_label_canonical', col_parse])
    if sub.empty:
        return 'NA','NA'
    ari = adjusted_rand_score(sub['primary_label_canonical'], sub[col_parse])
    uniq = sorted(list(set(sub['primary_label_canonical']).union(set(sub[col_parse]))))
    mapping = {v:i for i,v in enumerate(uniq)}
    kappa = cohen_kappa_score(sub['primary_label_canonical'].map(mapping), sub[col_parse].map(mapping))
    return ari, kappa

if 'parseA_mapped' in df.columns:
    ari_pa, kappa_pa = compute_agreement('parseA_mapped')
    results.update({'ari_canonical_parseA': ari_pa, 'kappa_canonical_parseA': kappa_pa})
else:
    results.update({'ari_canonical_parseA': 'NA', 'kappa_canonical_parseA': 'NA'})

if 'parseB_mapped' in df.columns:
    ari_pb, kappa_pb = compute_agreement('parseB_mapped')
    results.update({'ari_canonical_parseB': ari_pb, 'kappa_canonical_parseB': kappa_pb})
else:
    results.update({'ari_canonical_parseB': 'NA', 'kappa_canonical_parseB': 'NA'})

# Per-motif preservation after mapping
def per_motif_preservation(col_parse):
    motifs = sorted(df['primary_label_canonical'].dropna().unique())
    rows = []
    for motif in motifs:
        subset = df[df['primary_label_canonical'] == motif]
        denom = len(subset)
        if denom == 0:
            frac = np.nan
        else:
            if col_parse in df.columns:
                frac = (subset[col_parse] == motif).sum() / denom
            else:
                frac = np.nan
        rows.append({'motif': motif, 'count_in_canonical': denom, 'fraction_preserved': frac})
    return pd.DataFrame(rows)

preserve_pa = per_motif_preservation('parseA_mapped') if 'parseA_mapped' in df.columns else None
preserve_pb = per_motif_preservation('parseB_mapped') if 'parseB_mapped' in df.columns else None

# Save results and print
pd.Series(results).to_csv(OUT_SUM)
print("\n=== Results ===")
for k,v in results.items():
    print(f"{k}: {v}")

if preserve_pa is not None:
    print("\nPer-motif preservation (Canonical -> ParseA mapped):")
    print(preserve_pa.to_string(index=False))
if preserve_pb is not None:
    print("\nPer-motif preservation (Canonical -> ParseB mapped):")
    print(preserve_pb.to_string(index=False))

print("\nSummary CSV written to:", OUT_SUM)