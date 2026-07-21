# Compatibility wrapper: keep root invocation stable while the real script
# lives in build/build_release.ps1.

$ErrorActionPreference = "Stop"
$delegate = Join-Path $PSScriptRoot "build\build_release.ps1"

if (-not (Test-Path $delegate)) {
    throw "Delegate build script not found: $delegate"
}

& $delegate @args
