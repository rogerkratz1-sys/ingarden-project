# Ingarden Project — Reproducibility Package (repo_candidate)

This repository contains the complete set of artifacts referenced by the paper, abstracts, and supplements. It is organized to make it straightforward for readers to reproduce the example analyses and to obtain the larger data assets used for full reproduction.

## Repository layout (canonical)
- **scripts/** — analysis and helper scripts (Python).  
- **data/** — CSV tables and small supporting data used by examples and supplements.  
- **outputs/figures/** — final figures (PNG/SVG) used in the supplements.  
- **outputs/embeddings/** — binary embedding files (.npy) used by analyses.  
- **docs/** — short documentation and notes.  
- **metadata/** — project metadata and manifest.  
- **MANIFEST.csv** — authoritative list of all artifacts, checksums, sizes, and recommendations.

## Quickstart — run the minimal example
1. **Create and activate a virtual environment**

- **Windows (PowerShell)**
  `powershell
  python -m venv .venv
  .\.venv\Scripts\Activate.ps1
  python -m pip install --upgrade pip
  python -m pip install -r requirements.txt


