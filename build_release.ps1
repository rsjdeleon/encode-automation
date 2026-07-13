# Builds the 3 desktop apps into standalone .exe files and assembles them into
# one shared release folder (dist-release/) so they operate on one shared set
# of databases, matching how they already behave as one Python source tree.
#
# Safe to re-run after code changes: rebuilds the executables but only seeds
# the database/resource files into dist-release/ the first time, so it never
# clobbers live data that has since accumulated there from actual use.

$ErrorActionPreference = "Stop"

$root = $PSScriptRoot
Set-Location $root

$python = Join-Path $root ".venv\Scripts\python.exe"
$releaseDir = Join-Path $root "dist-release"

# selenium.webdriver's __init__.py lazily imports its Chrome/Firefox/etc.
# submodules via __getattr__ + importlib at runtime (Selenium 4.x), which
# PyInstaller's static analysis can't see -- without --collect-submodules
# the frozen build throws ModuleNotFoundError the first time automation
# actually touches webdriver.Chrome/ChromeOptions. Only apps that drive
# Selenium need this (assistance-form-new.py directly, config_manager.py via
# sync_config_from_website.py); social_worker_manager.py doesn't use it.
$seleniumArgs = @("--collect-submodules", "selenium")

$apps = @(
    @{ Script = "assistance-form-new.py"; ContentsDir = "_internal_assistance"; ExtraArgs = $seleniumArgs },
    @{ Script = "config_manager.py";      ContentsDir = "_internal_config";     ExtraArgs = $seleniumArgs },
    @{ Script = "social_worker_manager.py"; ContentsDir = "_internal_social";   ExtraArgs = @() }
)

New-Item -ItemType Directory -Force -Path $releaseDir | Out-Null

foreach ($app in $apps) {
    $name = [System.IO.Path]::GetFileNameWithoutExtension($app.Script)
    Write-Host "==> Building $($app.Script)"

    & $python -m PyInstaller `
        --noconfirm `
        --onedir `
        --windowed `
        --name $name `
        --contents-directory $app.ContentsDir `
        @($app.ExtraArgs) `
        $app.Script

    $builtDir = Join-Path $root "dist\$name"
    if (-not (Test-Path $builtDir)) {
        throw "Build output not found for $name at $builtDir"
    }

    Copy-Item -Path (Join-Path $builtDir "$name.exe") -Destination $releaseDir -Force
    Copy-Item -Path (Join-Path $builtDir $app.ContentsDir) -Destination $releaseDir -Recurse -Force
}

Write-Host "==> Seeding shared data files into dist-release/ (only if not already present)"

$dataFiles = @("config.db", "person-record.db", "worker.db", "data-new.pkl", "default.png", "license.json")
foreach ($file in $dataFiles) {
    $source = Join-Path $root $file
    $dest = Join-Path $releaseDir $file
    if ((Test-Path $source) -and (-not (Test-Path $dest))) {
        Copy-Item -Path $source -Destination $dest
        Write-Host "  copied $file"
    } else {
        Write-Host "  skipped $file (already present in dist-release/ or missing from source)"
    }
}

Write-Host "==> Done. Executables are in $releaseDir"
