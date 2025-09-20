<# run_specs_maintenance.ps1
   Validates specs, then generates the README indexes if valid.
#>
$ErrorActionPreference = "Stop"
powershell -ExecutionPolicy Bypass -File .\scripts\validate_specs.ps1
if ($LASTEXITCODE -ne 0) { throw "Spec validation failed. README was not regenerated." }
powershell -ExecutionPolicy Bypass -File .\scripts\generate_spec_index.ps1
