# assemble_S8_final.ps1
# Usage: run from C:\Users\ctint\Desktop\Scripts\repo_candidate
# Produces supplement\S-8\ with sensitivity table, histogram captions, and run commands.

$base = "C:\Users\ctint\Desktop\Scripts"
$s8dir = Join-Path $base "supplement\S-8"
New-Item -ItemType Directory -Path $s8dir -Force | Out-Null

# Candidate run folder patterns to search for (handles both _B1000 and plain names)
$patterns = @(
  "motif_results_robustness\peripheral_85*",
  "motif_results_robustness\peripheral_90*",
  "motif_results_robustness\peripheral_95*",
  "motif_results\*"
)

# Discover run folders that contain both S8_null_samples_summary.csv and motif_candidates_test.csv
$runs = @()
foreach ($p in $patterns) {
  $folders = Get-ChildItem (Join-Path $base $p) -Directory -ErrorAction SilentlyContinue
  foreach ($f in $folders) {
    $summary = Join-Path $f.FullName "S8_null_samples_summary.csv"
    $cands = Join-Path $f.FullName "motif_candidates_test.csv"
    if ((Test-Path $summary) -and (Test-Path $cands)) {
      # infer percentile from folder name if possible
      if ($f.Name -match "85") { $pct = 85 } elseif ($f.Name -match "90") { $pct = 90 } elseif ($f.Name -match "95") { $pct = 95 } else { $pct = "" }
      $runs += [PSCustomObject]@{ run_p = $pct; dir = $f.FullName; summary = $summary; cands = $cands }
    }
  }
}

if ($runs.Count -eq 0) {
  Write-Host "No run folders with both S8_null_samples_summary.csv and motif_candidates_test.csv found. Exiting."
  exit 1
}

# Build sensitivity table and histogram captions
$sensitivityRows = @()
$histCaptions = @()

foreach ($r in $runs) {
  $p = $r.run_p
  $dir = $r.dir
  $summary = Import-Csv $r.summary
  $cands = Import-Csv $r.cands

  # Build sensitivity rows from motif_candidates_test.csv (use meta.json B if available)
  $metaPath = Join-Path $dir "meta.json"
  $metaB = ""
  if (Test-Path $metaPath) {
    try { $meta = Get-Content $metaPath -Raw | ConvertFrom-Json; $metaB = $meta.B } catch { $metaB = "" }
  }

  foreach ($cand in $cands) {
    $cid = [int]$cand.label
    $row = [PSCustomObject]@{
      run_p = $p
      B = if ($metaB) { $metaB } else { "" }
      candidate_id = $cid
      n_points = $cand.size
      T_obs = $cand.stat
      raw_p_value = $cand.pval
      BH_selected = if ($cand.selected -eq "True") { "yes" } else { "no" }
    }
    $sensitivityRows += $row
  }

  # Build histogram captions using summary CSV (match by candidate_id)
  foreach ($s in $summary) {
    $cid = $s.candidate_id
    # ensure BH_selected column exists in summary; if not, try to find in candidate table
    $bh = $s.BH_selected
    if (-not $bh) {
      $matchCand = $cands | Where-Object { [int]$_.label -eq [int]$cid }
      if ($matchCand) { $bh = if ($matchCand.selected -eq "True") { "yes" } else { "no" } }
    }
    $caption = @"
Candidate $cid (p=$p)
Observed cluster density T_obs = $([double]$s.T_obs)
Null summary: null_min = $([double]$s.null_min); null_1pct = $([double]$s.null_1pct); null_5pct = $([double]$s.null_5pct); null_median = $([double]$s.null_median); null_95pct = $([double]$s.null_95pct); null_max = $([double]$s.null_max)
Monte Carlo p = $([double]$s.raw_p_value)
BH_selected = $bh
Interpretation: Observed density compared to radial-preserving null for p=$p (B=$([string]$s.B)).
"@
    $histCaptions += $caption
  }
}

# Export sensitivity table
$sensitivityPath = Join-Path $s8dir "sensitivity_table_p85_90_95.csv"
$sensitivityRows | Sort-Object run_p,candidate_id | Export-Csv $sensitivityPath -NoTypeInformation -Force

# Export histogram captions
$histFile = Join-Path $s8dir "S8_null_histograms.txt"
$histCaptions -join "`r`n---`r`n" | Out-File -FilePath $histFile -Encoding UTF8 -Force

# Create run commands and provenance header
# Try to get git commit if repo exists
$gitHash = ""
try {
  $gitHash = (& git -C $base rev-parse --short HEAD) 2>$null
} catch { $gitHash = "<commit-hash-not-found>" }

$prov = "Provenance: assembled_date=$(Get-Date -Format yyyy-MM-dd), git_commit=$gitHash, assembler=assemble_S8_final.ps1"
$runCommands = @(
  $prov,
  "",
  "Run commands used to produce diagnostics (examples):",
  'python motif_discovery_test.py --embeddings <path> --outdir <outdir> --peripheral_pct 95 --dbscan_eps 0.5 --dbscan_min_samples 5 --null_method radial_preserve --B 1000 --alpha 0.05 --seed 42',
  "",
  "Notes: S8_null_samples_summary.csv files were read from each run folder and used to create the captions and sensitivity table."
)
$runCommands -join "`r`n" | Out-File -FilePath (Join-Path $s8dir "S8_run_commands.txt") -Encoding UTF8 -Force

Write-Host "Assembled S-8 files in $s8dir"
Write-Host "Sensitivity table:" $sensitivityPath
Write-Host "Histogram captions:" $histFile
Write-Host "Run commands/provenance:" (Join-Path $s8dir "S8_run_commands.txt")