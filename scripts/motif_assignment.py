#!/usr/bin/env python3
"""
motif_assignment.py

Minimal implementation of motif_assignment(pi, p_canon, TH) using the
classification rules from compute_stability.py.

Returns:
{
  "multilabel_flags": [],
  "primary_label": <str>,
  "features": {"violated_covers": [...], "n_violations": int, "perm_length": int},
  "adjudication_flag": False
}
"""
from typing import List, Dict, Any, Union

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
    print(motif_assignment("1 4 3 2 5 6 7 8 9 10 11 12"))
