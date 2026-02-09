#!/usr/bin/env python3
import argparse, json, csv
import pandas as pd

def load_perms(path):
    df = pd.read_csv(path)
    perm_cols = [c for c in df.columns if c.startswith("pos_")]
    return df[perm_cols].values.tolist()

def load_segmentation(path):
    # use utf-8-sig to accept files with or without a BOM
    with open(path, 'r', encoding='utf-8-sig') as f:
        return json.load(f)

def kendall_distance(p, q):
    n = len(p); pos = {v:i for i,v in enumerate(p)}; qpos = [pos[v] for v in q]
    inv = 0
    for i in range(n):
        for j in range(i+1, n):
            if qpos[i] > qpos[j]:
                inv += 1
    max_inv = n*(n-1)//2
    return inv / max_inv if max_inv > 0 else 0.0

def disp_kappa(perm, canon, kappa):
    return sum(abs(perm.index(canon[i]) - i)**kappa for i in range(len(canon)))

def adjacency_violations(perm, covers):
    pos = {v:i for i,v in enumerate(perm)}; violations = 0
    for a,b in covers:
        if pos[a] >= pos[b]:
            violations += 1
    return violations

def main():
    p = argparse.ArgumentParser()
    p.add_argument('--perms-file', required=True)
    p.add_argument('--segmentation-file', required=True)
    p.add_argument('--kappa', type=float, default=1.2)
    p.add_argument('--alpha', type=float, default=0.0001)
    p.add_argument('--lambda', dest='lam', type=float, default=0.1)
    p.add_argument('--out', required=True)
    args = p.parse_args()

    perms = load_perms(args.perms_file)
    seg = load_segmentation(args.segmentation_file)
    nodes = list(range(1, len(seg) + 1)); canon = nodes
    rows = []

    # load covers from poset file if present next to segmentation file
    try:
        covers = []
        with open(args.segmentation_file.replace('segmentation_vector.json','poset_covers.csv'), 'r', encoding='utf-8-sig') as f:
            r = csv.reader(f)
            for row in r:
                if not row: continue
                a = row[0].strip(); b = row[1].strip()
                covers.append((int(a), int(b)))
    except Exception:
        covers = [(i, i+1) for i in range(1, len(seg))]

    for idx, perm in enumerate(perms):
        dK = kendall_distance(canon, perm)
        disp = disp_kappa(perm, canon, args.kappa)
        disp_scaled = disp * (1 + args.alpha * (disp**2))
        adj_viol = adjacency_violations(perm, covers)
        single_move = max(abs(perm.index(i+1) - i) for i in range(len(seg)))
        max_block = 1
        n = len(seg)
        for i in range(n):
            for j in range(i+1, n+1):
                block = canon[i:j]
                for k in range(n - (j - i) + 1):
                    if perm[k:k+(j-i)] == block:
                        max_block = max(max_block, j - i)
        rev = list(reversed(canon)); dual_prox = kendall_distance(rev, perm)
        score_dir = 1.0 - (0.6 * dK + 0.4 * (disp_scaled / (1 + disp_scaled)))
        rows.append({
            'perm_index': idx,
            'dK': dK,
            'disp_kappa_scaled': disp_scaled,
            'adjacency_violations': adj_viol,
            'single_move': single_move,
            'max_block_move': max_block,
            'order_dual_proximity': dual_prox,
            'score_dir': score_dir,
            'connective_density_per_100': 0.0,
            'pos_weighted_connectives': 0.0,
            'sent_connective_sd': 0.0,
            'max_sent_connectives': 0.0
        })

    df = pd.DataFrame(rows)
    df.to_csv(args.out, index=False)
    print("Wrote", args.out)

if __name__ == '__main__':
    main()
