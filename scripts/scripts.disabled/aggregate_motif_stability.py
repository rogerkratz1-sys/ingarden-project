#!/usr/bin/env python3
"""
aggregate_motif_stability.py

Aggregate K-W perturbation outputs into consensus motifs and stability summaries.

Usage:
  python aggregate_motif_stability.py --kw-folder .\robustness_results\kw_runs_embeddings_parseA_20260126_194527_20260126_195511

Options:
  --kw-folder PATH         : path to a kw_runs_* folder (required)
  --jaccard-threshold F    : threshold to connect clusters into consensus groups (default 0.5)
  --consensus-fraction F   : fraction of member clusters a permutation must appear in to be in consensus (default 0.5)
  --outdir PATH            : output directory (default: same kw-folder)
  --write-debug            : write debug CSV of all cluster-pair Jaccards
"""
import argparse
import csv
import glob
import json
import math
from collections import defaultdict
from pathlib import Path

def load_cluster_members(kw_folder):
    # returns list of (run_id, cluster_id, set_of_perm_indices, perm_strings_if_available)
    files = sorted(Path(kw_folder).glob("cluster_members_run_*.csv"))
    if not files:
        raise SystemExit(f"No cluster_members_run_*.csv files found in {kw_folder}")
    clusters = []
    for f in files:
        # run index from filename
        stem = f.stem
        # parse run id
        try:
            run_id = int(stem.split("_")[-1])
        except Exception:
            run_id = stem
        # read rows
        with f.open(newline='', encoding='utf8') as fh:
            reader = csv.reader(fh)
            header = next(reader, None)
            # expect header: cluster_id,perm_index,perm
            for row in reader:
                if not row:
                    continue
                cluster_id = int(row[0])
                perm_index = int(row[1])
                perm_str = row[2] if len(row) > 2 else None
                clusters.append((run_id, cluster_id, perm_index, perm_str))
    # group by (run_id, cluster_id)
    grouped = {}
    for run_id, cluster_id, perm_index, perm_str in clusters:
        key = (run_id, cluster_id)
        if key not in grouped:
            grouped[key] = {"perms": set(), "perm_strs": []}
        grouped[key]["perms"].add(int(perm_index))
        if perm_str is not None:
            grouped[key]["perm_strs"].append((int(perm_index), perm_str))
    # convert to list
    cluster_list = []
    for (run_id, cluster_id), info in sorted(grouped.items()):
        cluster_list.append({
            "run_id": run_id,
            "cluster_id": cluster_id,
            "perm_indices": info["perms"],
            "perm_strs": dict(info["perm_strs"])  # map index->string if available
        })
    return cluster_list

def jaccard(a, b):
    if not a and not b:
        return 1.0
    inter = len(a & b)
    uni = len(a | b)
    return inter / uni if uni > 0 else 0.0

def build_pairwise_jaccard(cluster_list):
    n = len(cluster_list)
    pairs = []
    for i in range(n):
        for j in range(i+1, n):
            a = cluster_list[i]["perm_indices"]
            b = cluster_list[j]["perm_indices"]
            val = jaccard(a, b)
            pairs.append((i, j, val))
    return pairs

def build_graph_components(n_nodes, pairs, threshold):
    # adjacency list
    adj = [[] for _ in range(n_nodes)]
    for i, j, val in pairs:
        if val >= threshold:
            adj[i].append(j)
            adj[j].append(i)
    # connected components via DFS
    visited = [False]*n_nodes
    components = []
    for i in range(n_nodes):
        if visited[i]:
            continue
        stack = [i]
        comp = []
        visited[i] = True
        while stack:
            v = stack.pop()
            comp.append(v)
            for w in adj[v]:
                if not visited[w]:
                    visited[w] = True
                    stack.append(w)
        components.append(sorted(comp))
    return components

def compute_consensus_for_component(component_indices, cluster_list, consensus_fraction):
    # gather member clusters
    member_clusters = [cluster_list[i] for i in component_indices]
    m = len(member_clusters)
    # count permutation occurrences across member clusters
    perm_counts = defaultdict(int)
    for c in member_clusters:
        for p in c["perm_indices"]:
            perm_counts[p] += 1
    # consensus perms: those with count >= ceil(consensus_fraction * m)
    threshold = math.ceil(consensus_fraction * m)
    consensus_perms = sorted([p for p, cnt in perm_counts.items() if cnt >= threshold])
    # fragmentation: number of distinct runs represented
    runs = sorted({c["run_id"] for c in member_clusters})
    # mean pairwise jaccard among member clusters
    # compute all pairwise jaccards
    jvals = []
    for i in range(len(member_clusters)):
        for j in range(i+1, len(member_clusters)):
            jvals.append(jaccard(member_clusters[i]["perm_indices"], member_clusters[j]["perm_indices"]))
    mean_jaccard = sum(jvals)/len(jvals) if jvals else 1.0
    return {
        "member_clusters": [(c["run_id"], c["cluster_id"]) for c in member_clusters],
        "n_member_clusters": m,
        "runs_represented": runs,
        "fragmentation": len(runs),
        "mean_pairwise_jaccard": mean_jaccard,
        "consensus_perms": consensus_perms,
        "perm_counts": perm_counts
    }

def load_permutation_strings_from_any(cluster_list):
    # try to recover perm strings mapping from cluster_list entries that have perm_strs
    mapping = {}
    for c in cluster_list:
        for idx, s in c.get("perm_strs", {}).items():
            mapping[int(idx)] = s
    return mapping

def compute_event_position_stats(consensus_perms, perm_index_to_string):
    # perm strings are like "1;2;3;..." ; compute for each event id mean normalized position across consensus perms
    if not consensus_perms:
        return {}
    # build list of permutations as lists
    perms = []
    for pidx in consensus_perms:
        s = perm_index_to_string.get(pidx)
        if s is None:
            # cannot compute positions without perm strings
            return {}
        arr = [int(x) for x in s.split(";") if x != ""]
        perms.append(arr)
    # determine node set
    nodes = sorted({v for perm in perms for v in perm})
    n = len(nodes)
    pos_stats = {}
    for node in nodes:
        positions = []
        for perm in perms:
            if node in perm:
                positions.append(perm.index(node) / max(1, len(perm)-1))
        pos_stats[node] = sum(positions)/len(positions) if positions else None
    return pos_stats

def write_csv_consensus(outdir, consensus_groups):
    path = Path(outdir) / "consensus_motifs.csv"
    with path.open("w", newline='', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(["consensus_id","n_member_clusters","fragmentation","mean_pairwise_jaccard","n_consensus_perms","member_clusters","consensus_perms"])
        for cid, g in enumerate(consensus_groups):
            writer.writerow([
                cid,
                g["n_member_clusters"],
                g["fragmentation"],
                f"{g['mean_pairwise_jaccard']:.6g}",
                len(g["consensus_perms"]),
                ";".join([f"{r}-{c}" for r,c in g["member_clusters"]]),
                ";".join(str(x) for x in g["consensus_perms"])
            ])
    return path

def write_csv_summary(outdir, consensus_groups):
    path = Path(outdir) / "motif_stability_summary.csv"
    with path.open("w", newline='', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(["consensus_id","n_member_clusters","fragmentation","mean_pairwise_jaccard","n_consensus_perms"])
        for cid, g in enumerate(consensus_groups):
            writer.writerow([cid, g["n_member_clusters"], g["fragmentation"], f"{g['mean_pairwise_jaccard']:.6g}", len(g["consensus_perms"])])
    return path

def write_event_positions(outdir, consensus_groups, perm_index_to_string):
    path = Path(outdir) / "consensus_event_positions.csv"
    with path.open("w", newline='', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(["consensus_id","event_id","mean_normalized_position"])
        for cid, g in enumerate(consensus_groups):
            pos_stats = compute_event_position_stats(g["consensus_perms"], perm_index_to_string)
            if not pos_stats:
                continue
            for node, meanpos in sorted(pos_stats.items()):
                writer.writerow([cid, node, "" if meanpos is None else f"{meanpos:.6g}"])
    return path

def write_debug_pairs(outdir, pairs, cluster_list):
    path = Path(outdir) / "debug_cluster_pairs.csv"
    with path.open("w", newline='', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerow(["i","j","run_i","cluster_i","run_j","cluster_j","jaccard"])
        for i, j, val in pairs:
            ci = cluster_list[i]
            cj = cluster_list[j]
            writer.writerow([i, j, ci["run_id"], ci["cluster_id"], cj["run_id"], cj["cluster_id"], f"{val:.6g}"])
    return path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--kw-folder", required=True, help="Path to kw_runs_* folder")
    parser.add_argument("--jaccard-threshold", type=float, default=0.5, help="Jaccard threshold to connect clusters into consensus groups")
    parser.add_argument("--consensus-fraction", type=float, default=0.5, help="Fraction of member clusters a permutation must appear in to be in consensus")
    parser.add_argument("--outdir", type=str, default=None, help="Output directory (default: same as kw-folder)")
    parser.add_argument("--write-debug", action="store_true", help="Write debug CSV of all cluster-pair jaccards")
    args = parser.parse_args()

    kw_folder = Path(args.kw_folder)
    if not kw_folder.exists():
        raise SystemExit(f"kw-folder not found: {kw_folder}")

    outdir = Path(args.outdir) if args.outdir else kw_folder
    outdir.mkdir(parents=True, exist_ok=True)

    print("Loading cluster members...")
    cluster_list = load_cluster_members(kw_folder)
    print(f"Loaded {len(cluster_list)} clusters from runs")

    print("Computing pairwise Jaccard...")
    pairs = build_pairwise_jaccard(cluster_list)
    if args.write_debug:
        write_debug_pairs(outdir, pairs, cluster_list)
        print("Wrote debug_cluster_pairs.csv")

    print("Building consensus groups with Jaccard threshold", args.jaccard_threshold)
    components = build_graph_components(len(cluster_list), pairs, args.jaccard_threshold)
    print(f"Found {len(components)} consensus groups")

    consensus_groups = []
    for comp in components:
        g = compute_consensus_for_component(comp, cluster_list, args.consensus_fraction)
        consensus_groups.append(g)

    # try to recover perm strings for event position stats
    perm_index_to_string = load_permutation_strings_from_any(cluster_list)

    # write outputs
    write_csv_consensus(outdir, consensus_groups)
    write_csv_summary(outdir, consensus_groups)
    write_event_positions(outdir, consensus_groups, perm_index_to_string)
    print("Wrote consensus_motifs.csv, motif_stability_summary.csv, consensus_event_positions.csv to", outdir)

if __name__ == "__main__":
    main()
