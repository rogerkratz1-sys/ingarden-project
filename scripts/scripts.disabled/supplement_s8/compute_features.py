# compute_features.py
import argparse, json, pandas as pd
from math import fabs

def parse_perm(s):
    return [int(x) for x in s.strip().split()]

def kendall_distance(p, canon):
    n = len(p)
    pos = {v:i for i,v in enumerate(p)}
    discord = 0
    total = n*(n-1)/2
    for i in range(n):
        for j in range(i+1,n):
            a = canon[i]; b = canon[j]
            if pos[a] > pos[b]:
                discord += 1
    return discord / total

def disp_kappa_scaled(p, canon, kappa=1.2, alpha=0.0001):
    pos = {v:i for i,v in enumerate(p)}
    canon_pos = {v:i for i,v in enumerate(canon)}
    disp = sum(abs(pos[v]-canon_pos[v])**kappa for v in canon_pos)
    return disp * (1 + alpha * (disp**2))

def violated_covers(p, covers):
    pos = {v:i for i,v in enumerate(p)}
    violated = []
    for a,b in covers:
        if pos.get(a,1e9) > pos.get(b,-1e9):
            violated.append((a,b))
    return violated

def anchor_preservation(p, anchors, r=1):
    pos = {v:i for i,v in enumerate(p)}
    canon_pos = {v:i for i,v in enumerate(sorted(p))}
    preserved = 0
    for a in anchors:
        if abs(pos.get(a,1e9) - canon_pos.get(a,1e9)) <= r:
            preserved += 1
    return preserved / max(1,len(anchors))

def max_block_move(p):
    n = len(p)
    pos = {v:i for i,v in enumerate(p)}
    max_block = 1
    for start in range(1,n+1):
        length = 1
        cur = start
        while cur+1 <= n and pos.get(cur+1, -999) > pos.get(cur, -999):
            length += 1
            cur += 1
        if length > max_block:
            max_block = length
    return max_block

def single_element_move(p, canon):
    pos = {v:i for i,v in enumerate(p)}
    canon_pos = {v:i for i,v in enumerate(canon)}
    return max(abs(pos[v]-canon_pos[v]) for v in canon_pos)

def order_dual_proximity(p, canon):
    rev = list(reversed(canon))
    return kendall_distance(p, rev)

def score_dir_placeholder(p, canon):
    return 1.0 - kendall_distance(p, canon)

def main(args):
    df = pd.read_csv(args.input)
    if 'perm_str' not in df.columns:
        df = df.rename(columns={df.columns[1]:'perm_str'})
    cfg = json.load(open(args.covers))
    covers = [tuple(x) for x in cfg['covers']]
    anchors = cfg.get('anchors', [])
    first_perm = parse_perm(df.iloc[0]['perm_str'])
    n = len(first_perm)
    canon = list(range(1,n+1))
    rows = []
    for idx, row in df.iterrows():
        perm = parse_perm(row['perm_str'])
        dK = kendall_distance(perm, canon)
        disp = disp_kappa_scaled(perm, canon, kappa=args.kappa, alpha=args.alpha)
        violated = violated_covers(perm, covers)
        anchor_pres = anchor_preservation(perm, anchors, r=args.anchor_radius)
        max_block = max_block_move(perm)
        single_move = single_element_move(perm, canon)
        dual_prox = order_dual_proximity(perm, canon)
        score = score_dir_placeholder(perm, canon)
        rows.append({
            'index': row.get('index', idx),
            'perm_str': row['perm_str'],
            'dK': dK,
            'disp_kappa_scaled': disp,
            'violated_covers': str(violated),
            'anchor_preservation': anchor_pres,
            'max_block_move': max_block,
            'single_element_move': single_move,
            'dual_proximity': dual_prox,
            'score_dir': score
        })
    pd.DataFrame(rows).to_csv(args.out, index=False)
    print('Wrote', args.out)

if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('--input', required=True)
    p.add_argument('--covers', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--kappa', type=float, default=1.2)
    p.add_argument('--alpha', type=float, default=0.0001)
    p.add_argument('--anchor_radius', type=int, default=1)
    args = p.parse_args()
    main(args)
