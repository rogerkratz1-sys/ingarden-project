#!/usr/bin/env bash
set -euo pipefail

EMB="C:/Users/ctint/Desktop/Scripts/embeddings_5000_dim8.csv"
SCRIPT="motif_discovery_test.py"
OUTROOT="C:/Users/ctint/Desktop/Scripts/motif_results_robustness"
DBSCAN_EPS=0.5
DBSCAN_MIN=5
NULL_METHOD="radial_preserve"
B=1000
ALPHA=0.05
SEED=42

for PCT in 85 90 95; do
  OUTDIR="${OUTROOT}/peripheral_${PCT}"
  mkdir -p "${OUTDIR}"
  echo "Running peripheral_pct=${PCT} -> ${OUTDIR}"
  python "${SCRIPT}" \
    --embeddings "${EMB}" \
    --outdir "${OUTDIR}" \
    --peripheral_pct "${PCT}" \
    --dbscan_eps "${DBSCAN_EPS}" \
    --dbscan_min_samples "${DBSCAN_MIN}" \
    --null_method "${NULL_METHOD}" \
    --B "${B}" \
    --alpha "${ALPHA}" \
    --seed "${SEED}" \
    > "${OUTDIR}/run.log" 2>&1
done

echo "All runs complete. Results in ${OUTROOT}"