<# 
  generate_spec_index.ps1
  Scans .\brokers\<broker>\specs\<category>\*.json and builds README.md (root),
  plus per-broker READMEs. Safe for Windows PowerShell and PowerShell 7+.
#>

$ErrorActionPreference = 'Stop'

# Paths
$scriptDir = $PSScriptRoot
if (-not $scriptDir) { $scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path }  # fallback
$repoRoot  = Split-Path -Parent $scriptDir
$brokers   = Join-Path $repoRoot 'brokers'

if (-not (Test-Path $brokers)) {
  throw "Brokers folder not found at: $brokers"
}

# Helper: make repo-relative path like .\brokers\cmc\specs\indices\AUS200.json
function Get-RelativePath([string]$fullPath, [string]$root) {
  $normFull = [System.IO.Path]::GetFullPath($fullPath)
  $normRoot = [System.IO.Path]::GetFullPath($root)
  if ($normFull.StartsWith($normRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    return '.' + $normFull.Substring($normRoot.Length)
  }
  return $fullPath
}

# Helper: category from path (indices / commodities / fx / other)
function Get-CategoryFromPath([string]$path) {
  if ($path -match '[\\/]+specs[\\/]+indices[\\/]')        { return 'indices' }
  elseif ($path -match '[\\/]+specs[\\/]+commodities[\\/]') { return 'commodities' }
  elseif ($path -match '[\\/]+specs[\\/]+fx[\\/]')          { return 'fx' }
  else                                                      { return 'other' }
}

# Collect & parse JSON spec files
$files = Get-ChildItem -Path $brokers -Recurse -Filter *.json -File

# Build rows (no multiline pipe!)
$rows = foreach ($f in $files) {
  try {
    $json = Get-Content -Raw -Encoding UTF8 -LiteralPath $f.FullName | ConvertFrom-Json
    [pscustomobject]@{
      MarketCode = $json.market_code
      Broker     = $json.broker
      Symbol     = $json.symbol
      Category   = Get-CategoryFromPath $f.FullName
      RelPath    = Get-RelativePath $f.FullName $repoRoot
    }
  } catch {
    Write-Warning ("Failed to parse JSON: {0} — {1}" -f $f.FullName, $_.Exception.Message)
  }
}

# Filter invalid/incomplete entries
$rows = $rows | Where-Object { $_ -and $_.MarketCode -and $_.Broker -and $_.Symbol }

if (-not $rows) {
  throw "No spec JSONs found under $brokers"
}

# Order of categories in the README
$categories = @('indices','commodities','fx','other')

# ---------- Root README ----------
$sb = New-Object System.Text.StringBuilder
$null = $sb.AppendLine('# 📂 Trade Assistant — Market Specs Index  ')
$null = $sb.AppendLine('')
$null = $sb.AppendLine(("Auto-generated from **brokers/** on {0}.  " -f (Get-Date -Format 'yyyy-MM-dd HH:mm')))
$null = $sb.AppendLine('Each spec includes broker symbol, price/volume, spread, swaps, trading hours, and notes.  ')
$null = $sb.AppendLine('')
$null = $sb.AppendLine('## 📊 Current Coverage  ')
$null = $sb.AppendLine('')

foreach ($cat in $categories) {
  $catRows = $rows | Where-Object { $_.Category -eq $cat } | Sort-Object MarketCode, Broker
  if (-not $catRows) { continue }

  $title = switch ($cat) {
    'indices'     { '### Indices' }
    'commodities' { '### Commodities' }
    'fx'          { '### FX Majors' }
    default       { '### Other' }
  }
  $null = $sb.AppendLine($title)

  foreach ($mkt in ($catRows | Select-Object -ExpandProperty MarketCode -Unique)) {
    $null = $sb.AppendLine((" - **{0}**  " -f $mkt))
    foreach ($r in ($catRows | Where-Object { $_.MarketCode -eq $mkt })) {
      $line = ("   - {0} → ``{1}``  (symbol: ``{2}``)" -f ($r.Broker.ToUpper()), $r.RelPath, $r.Symbol)
      $null = $sb.AppendLine($line)
    }
  }
  $null = $sb.AppendLine('')
}

$null = $sb.AppendLine('---')
$null = $sb.AppendLine('**Tip:** To update this index after adding markets, run:  ')
$null = $sb.AppendLine('```powershell')
$null = $sb.AppendLine('.\scripts\generate_spec_index.ps1')
$null = $sb.AppendLine('```')

# Write root README.md
$readmePath = Join-Path $repoRoot 'README.md'
[System.IO.File]::WriteAllText($readmePath, $sb.ToString(), [System.Text.Encoding]::UTF8)

# ---------- Per-broker READMEs ----------
$byBroker = $rows | Group-Object Broker
foreach ($g in $byBroker) {
  $b    = $g.Name
  $sbB  = New-Object System.Text.StringBuilder
  $null = $sbB.AppendLine(("# {0} — Specs Index  " -f ($b.ToUpper())))
  $null = $sbB.AppendLine(("Auto-generated on {0}.  " -f (Get-Date -Format 'yyyy-MM-dd HH:mm')))
  $null = $sbB.AppendLine('')

  foreach ($cat in $categories) {
    $catRows = $g.Group | Where-Object { $_.Category -eq $cat } | Sort-Object MarketCode
    if (-not $catRows) { continue }

    $title = switch ($cat) {
      'indices'     { '## Indices' }
      'commodities' { '## Commodities' }
      'fx'          { '## FX' }
      default       { '## Other' }
    }
    $null = $sbB.AppendLine($title)

    foreach ($mkt in ($catRows | Select-Object -ExpandProperty MarketCode -Unique)) {
      $null = $sbB.AppendLine((" - **{0}**  " -f $mkt))
      foreach ($r in ($catRows | Where-Object { $_.MarketCode -eq $mkt })) {
        $line = ("   - ``{0}``  (symbol: ``{1}``)" -f $r.RelPath, $r.Symbol)
        $null = $sbB.AppendLine($line)
      }
    }
    $null = $sbB.AppendLine('')
  }

  $brokerFolder = Join-Path $brokers $b
  if (-not (Test-Path $brokerFolder)) { New-Item -ItemType Directory -Path $brokerFolder | Out-Null }
  $readmeBPath  = Join-Path $brokerFolder 'README.md'
  [System.IO.File]::WriteAllText($readmeBPath, $sbB.ToString(), [System.Text.Encoding]::UTF8)
}

Write-Host 'README.md updated. Per-broker READMEs written under brokers\<broker>\README.md'
