# move_helper.ps1
# Move the module-level helper block so it appears after any module docstring
# and after all from __future__ imports, then run a quick smoke test (B=20).
# Save this file as UTF-8 and run from the repo folder.

Set-StrictMode -Version Latest

$repo = Split-Path -Path $MyInvocation.MyCommand.Path -Parent
if (-not $repo) { $repo = Get-Location }
Set-Location $repo

$src = ".\motif_discovery_test.py"
if (-not (Test-Path $src)) {
  Write-Error "$src not found in current folder. Run this from the repo folder."
  exit 1
}

# backup
$bak = ".\motif_discovery_test.py.move_helper_script.bak"
Copy-Item $src $bak -Force
Write-Host "Backup written to $bak"

# read file
$text = Get-Content $src -Raw -Encoding utf8

$start = "# --- begin helper: write labels and candidate membership (module-level) ---"
$end   = "# --- end helper ---"

if ($text -notmatch [regex]::Escape($start) -or $text -notmatch [regex]::Escape($end)) {
  Write-Host "Helper markers not found; no changes made."
  exit 0
}

# extract helper and remove it
$parts = $text -split [regex]::Escape($start),2
$before = $parts[0]; $rest = $parts[1]
$parts2 = $rest -split [regex]::Escape($end),2
$helperBody = $parts2[0]; $after = $parts2[1]
$helperBlock = $start + $helperBody + $end

$base = $before + $after

# split into lines and find insertion point: after last from __future__ import or after docstring
$lines = $base -split "`n"
$lastFutureIdx = -1
for ($i=0; $i -lt $lines.Length; $i++) {
  if ($lines[$i] -match '^\s*from\s+__future__\s+import\b') { $lastFutureIdx = $i }
}

# find end of module docstring if present using simple string checks (avoid complex quoting)
$insertIdx = 0
if ($lines.Length -gt 0) {
  $first = $lines[0].Trim()
  if ($first.StartsWith('"""') -or $first.StartsWith("'''")) {
    for ($j=1; $j -lt $lines.Length; $j++) {
      $lnj = $lines[$j]
      if ($lnj.Contains('"""') -or $lnj.Contains("'''")) { $insertIdx = $j + 1; break }
    }
  }
}

# prefer inserting after last future import if present
if ($lastFutureIdx -ge 0) {
  $insertIdx = [Math]::Max($insertIdx, $lastFutureIdx + 1)
} else {
  for ($k=$insertIdx; $k -lt $lines.Length; $k++) {
    $ln = $lines[$k].Trim()
    if ($ln -eq "" -or $ln -match '^\s*#') { $insertIdx = $k + 1; continue }
    break
  }
}

# build new file with helper inserted at insertIdx
if ($insertIdx -gt 0) { $head = $lines[0..($insertIdx-1)] -join "`n" } else { $head = "" }
if ($insertIdx -lt $lines.Length) { $tail = $lines[$insertIdx..($lines.Length-1)] -join "`n" } else { $tail = "" }
$newText = $head + "`n" + $helperBlock + "`n" + $tail

# write file (UTF-8)
Set-Content -Path $src -Value $newText -Encoding utf8
Write-Host "Moved helper after module docstring/from __future__ imports and wrote $src"

# Quick smoke test (B=20) and save log
$log = ".\debug_run.log"
$env:PYTHONUNBUFFERED="1"
$env:OMP_NUM_THREADS="1"
$env:OPENBLAS_NUM_THREADS="1"
$env:MKL_NUM_THREADS="1"
$env:NUMEXPR_NUM_THREADS="1"

$pythonCmd = @(
  "python", ".\motif_discovery_test.py",
  "--embeddings", "C:\Users\ctint\Desktop\Scripts\embeddings_5000_dim8.csv",
  "--outdir", "C:\Users\ctint\Desktop\Scripts\motif_results_robustness\peripheral_90_debug",
  "--peripheral_pct", "90",
  "--null_method", "radial_preserve",
  "--B", "20",
  "--alpha", "0.05",
  "--seed", "42"
) -join " "

Write-Host "Running smoke test (B=20). Output will be saved to $log"
Invoke-Expression "$pythonCmd 2>&1 | Tee-Object -FilePath $log"

Write-Host "Smoke test finished. If there was an error, inspect $log with: Get-Content $log -Tail 120"