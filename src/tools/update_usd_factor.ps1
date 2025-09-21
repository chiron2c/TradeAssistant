param(
  [Parameter(Mandatory=$true)]
  [double]$AudUsd
)

$root   = "C:\Dev\TradeAssistant"
$config = Join-Path $root "config\account.json"

if (!(Test-Path $config)) {
  Write-Error "Config not found: $config"
  exit 1
}

# Read & compute factor
$json   = Get-Content $config -Raw | ConvertFrom-Json
$factor = [Math]::Round(1.0 / $AudUsd, 6)

# Ensure structure
if (-not $json.default_fx_usd_to_account) { $json | Add-Member -NotePropertyName default_fx_usd_to_account -NotePropertyValue $factor -Force }
else { $json.default_fx_usd_to_account = $factor }

if (-not $json.brokers) { $json | Add-Member -NotePropertyName brokers -NotePropertyValue (@{}) -Force }
foreach ($b in @('cmc','pepperstone')) {
  if (-not $json.brokers.$b) { $json.brokers | Add-Member -NotePropertyName $b -NotePropertyValue (@{}) -Force }
  $json.brokers.$b.fx_usd_to_account = $factor
}

if (-not $json.fx_map_quote_to_account) { $json | Add-Member -NotePropertyName fx_map_quote_to_account -NotePropertyValue (@{}) -Force }
$json.fx_map_quote_to_account.USD = $factor

# Write back
($json | ConvertTo-Json -Depth 8) | Set-Content $config -Encoding UTF8
Write-Host "[DONE] Set USD→AUD factor to $factor (from AUDUSD=$AudUsd)"
