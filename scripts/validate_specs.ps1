<# 
  validate_specs.ps1
  Validates spec JSONs under .\brokers\<broker>\specs\**\*.json
  Exits with non-zero code if any file fails validation.
#>

$ErrorActionPreference = "Stop"

# --- helpers ---
function Fail([string]$msg) { Write-Host " $msg" -ForegroundColor Red }

function Must-HaveKeys($obj, $path, [string[]]$keys) {
  foreach ($k in $keys) {
    if (-not ($obj.PSObject.Properties.Name -contains $k)) {
      throw "Missing key '$k' at $path"
    }
  }
}

function Must-BeNumeric($val, $path) {
  if ($null -eq $val) { throw "Null numeric at $path" }
  [double]$tmp | Out-Null  # implicit cast check
  try { [void][double]$val } catch { throw "Non-numeric value at $path (value='$val')" }
}

# --- paths ---
$repoRoot = Get-Location
$brokers  = Join-Path $repoRoot "brokers"
if (-not (Test-Path $brokers)) { throw "Folder not found: $brokers" }

$files = Get-ChildItem -Path $brokers -Recurse -Filter *.json -File
if (-not $files) { throw "No spec JSONs under $brokers" }

$errors = @()

foreach ($f in $files) {
  try {
    $json = Get-Content -Raw -Encoding UTF8 -LiteralPath $f.FullName | ConvertFrom-Json -ErrorAction Stop

    # --- top-level required ---
    Must-HaveKeys $json $f.FullName @('market_code','broker','symbol','price','volume','spread')
    if ([string]::IsNullOrWhiteSpace($json.market_code)) { throw "market_code empty at $($f.FullName)" }
    if ([string]::IsNullOrWhiteSpace($json.broker))      { throw "broker empty at $($f.FullName)" }
    if ([string]::IsNullOrWhiteSpace($json.symbol))      { throw "symbol empty at $($f.FullName)" }

    # broker whitelist (extend if you add more)
    $allowedBrokers = @('cmc','pepperstone')
    if ($allowedBrokers -notcontains $json.broker) {
      throw "broker '$($json.broker)' not in allowed set: $($allowedBrokers -join ', ') at $($f.FullName)"
    }

    # --- price ---
    Must-HaveKeys $json.price "$($f.FullName):price" @('digits','tick_size','tick_value_per_1lot','contract_size')
    if ($json.price.digits -isnot [int] -and $json.price.digits -isnot [long]) {
      throw "price.digits must be integer at $($f.FullName)"
    }
    Must-BeNumeric $json.price.tick_size            "$($f.FullName):price.tick_size"
    Must-BeNumeric $json.price.tick_value_per_1lot  "$($f.FullName):price.tick_value_per_1lot"
    Must-BeNumeric $json.price.contract_size        "$($f.FullName):price.contract_size"

    # --- volume ---
    Must-HaveKeys $json.volume "$($f.FullName):volume" @('min_lot','lot_step','max_lot')
    Must-BeNumeric $json.volume.min_lot  "$($f.FullName):volume.min_lot"
    Must-BeNumeric $json.volume.lot_step "$($f.FullName):volume.lot_step"
    Must-BeNumeric $json.volume.max_lot  "$($f.FullName):volume.max_lot"

    # --- spread ---
    Must-HaveKeys $json.spread "$($f.FullName):spread" @('type')
    if ([string]::IsNullOrWhiteSpace($json.spread.type)) {
      throw "spread.type empty at $($f.FullName)"
    }

    # --- swaps (optional) ---
    if ($json.PSObject.Properties.Name -contains 'swaps') {
      Must-HaveKeys $json.swaps "$($f.FullName):swaps" @('type','long','short')
      if ([string]::IsNullOrWhiteSpace($json.swaps.type)) {
        throw "swaps.type empty at $($f.FullName)"
      }
      Must-BeNumeric $json.swaps.long  "$($f.FullName):swaps.long"
      Must-BeNumeric $json.swaps.short "$($f.FullName):swaps.short"
      # triple_day optional but nice to have
    }

    # --- hint checks (optional, no fail) ---
    if ($json.price.digits -lt 0) { Fail "Non-sensical digits (<0) at $($f.FullName)" }
    # Ensure category folder aligns with file path (indices/commodities/fx)
    $fp = $f.FullName
    if ($json.market_code -and $fp -match '\\specs\\(indices|commodities|fx)\\') { } else {
      # No-op; just informational
    }

    Write-Host " OK: $($f.FullName)" -ForegroundColor Green
  }
  catch {
    $msg = "File: $($f.FullName)`n  Error: $($_.Exception.Message)"
    $errors += $msg
    Fail $msg
  }
}

if ($errors.Count -gt 0) {
  Write-Host "`n---- SUMMARY (FAIL) ----" -ForegroundColor Red
  $errors | ForEach-Object { Write-Host $_ -ForegroundColor Red }
  exit 1
} else {
  Write-Host "`nAll spec files valid " -ForegroundColor Green
  exit 0
}
