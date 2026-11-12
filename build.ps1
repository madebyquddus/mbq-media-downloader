param(
    [string]$Python = 'py'
)

$ErrorActionPreference = 'Stop'
Set-Location $PSScriptRoot

$appName = 'MBQ Media Downloader'
$specFile = 'MBQ.spec'
$distPath = Join-Path 'dist' $appName

Write-Host ''
Write-Host '========================================='
Write-Host ' MBQ Media Downloader - Windows Build'
Write-Host '========================================='
Write-Host ''

# --------------------------------------------------
# 1. Check Python
# --------------------------------------------------

Write-Host '[1/7] Checking Python...'

& $Python --version

if ($LASTEXITCODE -ne 0) {
    throw 'Python was not found. Make sure Python and the py launcher are installed.'
}

# --------------------------------------------------
# 2. Check PyInstaller
# --------------------------------------------------

Write-Host ''
Write-Host '[2/7] Checking PyInstaller...'

& $Python -m PyInstaller --version

if ($LASTEXITCODE -ne 0) {
    Write-Host 'PyInstaller is not installed. Installing it now...'
    & $Python -m pip install pyinstaller

    if ($LASTEXITCODE -ne 0) {
        throw 'PyInstaller installation failed.'
    }
}

# --------------------------------------------------
# 3. Check required project files
# --------------------------------------------------

Write-Host ''
Write-Host '[3/7] Checking project files...'

$requiredFiles = @(
    'main.py',
    $specFile,
    'assets\icons\mbq.ico',
    'assets\windows-version.txt',
    'LICENSE',
    'THIRD_PARTY_NOTICES.md'
)

foreach ($file in $requiredFiles) {
    if (-not (Test-Path -LiteralPath $file)) {
        throw "Required file is missing: $file"
    }
}

# --------------------------------------------------
# 4. Remove previous build
# --------------------------------------------------

Write-Host ''
Write-Host '[4/7] Cleaning previous build...'

if (Test-Path -LiteralPath 'build') {
    Remove-Item -LiteralPath 'build' -Recurse -Force
}

if (Test-Path -LiteralPath 'dist') {
    Remove-Item -LiteralPath 'dist' -Recurse -Force
}

# --------------------------------------------------
# 5. Build application
# --------------------------------------------------

Write-Host ''
Write-Host '[5/7] Building MBQ Media Downloader...'
Write-Host ''

& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    $specFile

if ($LASTEXITCODE -ne 0) {
    throw 'PyInstaller build failed.'
}

if (-not (Test-Path -LiteralPath $distPath)) {
    throw "Build completed but expected output folder was not found: $distPath"
}

# --------------------------------------------------
# 6. Copy external tools and supporting files
# --------------------------------------------------

Write-Host ''
Write-Host '[6/7] Copying external tools and documentation...'

# yt-dlp, FFmpeg and Node remain external so they
# can be updated/replaced without rebuilding the app.
if (Test-Path -LiteralPath 'tools') {
    Copy-Item `
        -LiteralPath 'tools' `
        -Destination $distPath `
        -Recurse `
        -Force
}

# Third-party licenses
if (Test-Path -LiteralPath 'licenses') {
    Copy-Item `
        -LiteralPath 'licenses' `
        -Destination $distPath `
        -Recurse `
        -Force
}

# Documentation
$documents = @(
    'LICENSE',
    'README.md',
    'THIRD_PARTY_NOTICES.md',
    'VERIFICATION.md',
    'CHANGELOG.md'
)

foreach ($document in $documents) {
    if (Test-Path -LiteralPath $document) {
        Copy-Item `
            -LiteralPath $document `
            -Destination $distPath `
            -Force
    }
}

# --------------------------------------------------
# 7. Verify final EXE
# --------------------------------------------------

Write-Host ''
Write-Host '[7/7] Verifying final build...'

$exePath = Join-Path $distPath "$appName.exe"

if (-not (Test-Path -LiteralPath $exePath)) {
    throw "The final executable was not found: $exePath"
}

Write-Host ''
Write-Host '========================================='
Write-Host ' BUILD COMPLETED SUCCESSFULLY'
Write-Host '========================================='
Write-Host ''
Write-Host "Application:"
Write-Host $exePath
Write-Host ''
Write-Host "Distribution folder:"
Write-Host $distPath
Write-Host ''
Write-Host 'You can now open the EXE and test the packaged application.'
Write-Host ''