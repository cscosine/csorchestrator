# Owned by the project template (cs-project-template): change it there.
# Creates .venv, installs the project with its dev tools, installs the pre-commit hooks.
# Usage: .\setup.ps1 [-Python <interpreter>]
param(
    [string]$Python = "python"
)
$ErrorActionPreference = "Stop"

function Invoke-Checked {
    & $args[0] $args[1..($args.Count - 1)]
    if ($LASTEXITCODE -ne 0) { throw "Failed: $args" }
}

Write-Host "Using Python: $Python"

& $Python -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"
if ($LASTEXITCODE -ne 0) {
    Write-Host "Error: Python 3.11 or newer is required."
    Write-Host "Found:"
    & $Python --version
    exit 1
}

Invoke-Checked $Python -m venv .venv

.\.venv\Scripts\Activate.ps1

Invoke-Checked python -m pip install --upgrade pip setuptools wheel
Invoke-Checked python -m pip install -e ".[dev]"

Invoke-Checked pre-commit install

Write-Host "Setup complete."
Write-Host ""
Write-Host "Next:"
Write-Host "  .\.venv\Scripts\Activate.ps1"
Write-Host "  code ."
Write-Host ""
Write-Host "Or:"
Write-Host "  .\open-code.ps1"
