$ErrorActionPreference = "Stop"
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot
try {
    python -m teateret_brief.cli --mode demo
    exit $LASTEXITCODE
}
finally {
    Pop-Location
}

