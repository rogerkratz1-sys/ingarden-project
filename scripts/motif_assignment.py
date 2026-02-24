#!/usr/bin/env python3
"""
motif_assignment.py

Implements a conservative motif_assignment(pi, p_canon, TH) interface
based on the classification rules used in compute_stability.py.

Expected inputs:
- pi: permutation string (e.g., "1 4 3 2") or list of ints
- p_canon: canonical cover order (not used here; kept for API compatibility)
- TH: thresholds dict or value (not used here; kept for API compatibility)

Returns a dict with keys:
- multilabel_flags: list of additional labels (empty here)
- primary_label: one of GlobalDistortion, FrontEndMove, BlockReorderExtreme,
                 DualClusterOutlier, AnchorPreservingDisorder, Other
- features: small dict with computed features (violated_covers, n_violations)
- adjudication_flag: boolean (False by default)
"""
from typing import List, Dict, Any, Union

# canonical covers used by mapping rules (same as compute_stability.py)
COVERS = [
    (1, 3), (1, 4), (1, 5),
    (3, 8), (4, 8), (5, 6), (6, 7), (7, 8), (8, 9),
    (9, 10), (10, 11), (11, 12)
]

def parse_perm_field(p: Union[str, List[int], None]) -> List[int]:
    if p is None:
        return []
    if isinstance(p, list):
        return [int(x) for x in p]
    s = str(p).strip()
    if not s:
        return []
    tokens = s.split()
    return [int(t) for t in tokens if t.isdigit()]

def compute_violated_covers_from_perm(perm: List[int]) -> set:
    pos = {v: i for i, v in enumerate(perm)}
    violated = []
    for a, b in COVERS:
        if a in pos and b in pos and pos[a] > pos[b]:
            violated.append((a, b))
    return set(violated)

def classify_first_violated(violated_set: set, cover_check_order: List[tuple]) -> str:
    if len(violated_set) >= 4:
        return "GlobalDistortion"
    front = {(1, 3), (1, 4), (1, 5)}
    for cov in cover_check_order:
        if cov in violated_set and cov in front:
            return "FrontEndMove"
    bre_set = {(3, 8), (4, 8), (5, 6), (6, 7), (7, 8), (8, 9)}
    for cov in cover_check_order:
        if cov in violated_set and cov in bre_set:
            return "BlockReorderExtreme"
    early = front
    late = {(9, 10), (10, 11), (11, 12)}
    if any(c in violated_set for c in early) and any(c in violated_set for c in late):
        for cov in cover_check_order:
            if cov in violated_set and (cov in early or cov in late):
                return "DualClusterOutlier"
    if len(violated_set) > 0 and not any(c in violated_set for c in front):
        return "AnchorPreservingDisorder"
    return "Other"

def motif_assignment(pi: Union[str, List[int], None], p_canon: List[tuple] = COVERS, TH: Any = None) -> Dict[str, Any]:
    """
    Minimal motif_assignment implementation.

    - pi: permutation string or list
    - p_canon: canonical cover order (list of tuples). If None, uses default COVERS.
    - TH: thresholds (not used here)

    Returns a dict with the expected keys for downstream code.
    """
    perm = parse_perm_field(pi)
    violated = compute_violated_covers_from_perm(perm)
    cover_order = list(p_canon) if p_canon else list(COVERS)
    primary_label = classify_first_violated(violated, cover_order)

    features = {
        "violated_covers": sorted(list(violated)),
        "n_violations": len(violated),
        "perm_length": len(perm)
    }

    return {
        "multilabel_flags": [],
        "primary_label": primary_label,
        "features": features,
        "adjudication_flag": False
    }

if __name__ == "__main__":
    # quick smoke test
    example = "1 4 3 2 5 6 7 8 9 10 11 12"
    print(motif_assignment(example))
