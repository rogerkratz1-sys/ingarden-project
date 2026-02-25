#!/usr/bin/env python3
import csv, json, os, argparse

parser = argparse.ArgumentParser()
parser.add_argument("--labels", default="outputs/labels_per_perm.csv")
parser.add_argument("--out", default="outputs/adjudication_template.csv")
args = parser.parse_args()

os.makedirs(os.path.dirname(args.out), exist_ok=True)
with open(args.labels, newline='') as inf, open(args.out, "w", newline='') as outf:
    reader = csv.DictReader(inf)
    fieldnames = reader.fieldnames + ["adjudicator_note","final_label"]
    writer = csv.DictWriter(outf, fieldnames=fieldnames)
    writer.writeheader()
    for r in reader:
        r["adjudicator_note"] = ""
        r["final_label"] = ""
        writer.writerow(r)
print("Wrote:", args.out)