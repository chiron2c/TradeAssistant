# --- build_all_previews.ps1 ---
param()

$root   = "C:\Dev\TradeAssistant"
$py     = Join-Path $root "env\Scripts\python.exe"
$outdir = Join-Path $root "output"

# Ensure plan has forex/oil pip values and indices silenced
& $py "$root\src\tools\patch_pip_values.py" --apply plan --disable-indices

# ===== CMC =====
& $py "$root\src\tools\set_broker.py" --broker cmc --write-copy
& $py "$root\src\jobs\run.py" --broker cmc --symbol-debug WTI
Copy-Item "$outdir\plan_preview.csv" "$outdir\plan_wti_cmc.csv" -Force

# ===== Pepperstone =====
& $py "$root\src\tools\set_broker.py" --broker pepperstone --write-copy
& $py "$root\src\jobs\run.py" --broker pepperstone --symbol-debug WTI
Copy-Item "$outdir\plan_preview.csv" "$outdir\plan_wti_pepperstone.csv" -Force

Write-Host "[DONE] Built: plan_wti_cmc.csv and plan_wti_pepperstone.csv"
