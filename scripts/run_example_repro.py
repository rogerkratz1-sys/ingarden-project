#!/usr/bin/env python3
"""
Wrapper entrypoint for CI: runs generate_artifacts.py and reports clear errors.
"""
import argparse
import os
import subprocess
import sys
import traceback

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--input", required=True)
    p.add_argument("--outdir", required=True)
    args = p.parse_args()

    os.makedirs(args.outdir, exist_ok=True)

    cmd = [sys.executable, "scripts/generate_artifacts.py", "--input", args.input, "--outdir", args.outdir]
    print("Running:", " ".join(cmd))
    try:
        res = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print("STDOUT:\\n", res.stdout)
        print("STDERR:\\n", res.stderr)
        print("generate_artifacts.py completed successfully.")
    except subprocess.CalledProcessError as e:
        print("generate_artifacts.py failed with return code", e.returncode)
        print("STDOUT:\\n", e.stdout)
        print("STDERR:\\n", e.stderr)
        print("Traceback (wrapper):")
        traceback.print_exc()
        sys.exit(e.returncode)
    except Exception:
        print("Unexpected error in wrapper:")
        traceback.print_exc()
        sys.exit(2)

if __name__ == "__main__":
    main()
