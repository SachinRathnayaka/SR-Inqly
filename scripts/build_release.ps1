param([string]$CompilerPath = '', [string]$Python = 'python', [string]$CertificateThumbprint = '', [string]$SignToolPath = 'signtool.exe')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
& $Python scripts\run_checks.py --headless
if ($LASTEXITCODE -ne 0) { throw 'Renderer checks failed.' }
& $Python -m PyInstaller --noconfirm packaging\windows.spec
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
function Sign-ReleaseFile([string]$Path) {
    if (-not $CertificateThumbprint) { return }
    if ($CertificateThumbprint -notmatch '^[A-Fa-f0-9]{40}$') { throw 'Provide a certificate thumbprint, never certificate material or passwords.' }
    & $SignToolPath sign /sha1 $CertificateThumbprint /fd SHA256 /tr https://timestamp.digicert.com /td SHA256 $Path
    if ($LASTEXITCODE -ne 0) { throw 'Authenticode signing failed.' }
    & $SignToolPath verify /pa $Path
    if ($LASTEXITCODE -ne 0) { throw 'Authenticode verification failed.' }
}
Sign-ReleaseFile 'dist\SR Inqly\SR Inqly.exe'
& $Python tests\check_package.py
if ($LASTEXITCODE -ne 0) { throw 'Packaged EXE verification failed.' }
foreach ($document in @('README.md','LICENSE','THIRD_PARTY_NOTICES.md','CHANGELOG.md','CONTRIBUTING.md','SECURITY.md')) {
    Copy-Item -LiteralPath $document -Destination 'dist\SR Inqly' -Force
}
Copy-Item -LiteralPath 'licenses' -Destination 'dist\SR Inqly' -Recurse -Force
Copy-Item -LiteralPath 'docs' -Destination 'dist\SR Inqly' -Recurse -Force
if (-not $CompilerPath) {
    $candidates = @("${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe", "$env:LOCALAPPDATA\SRInqlyBuildTools\InnoSetup\ISCC.exe")
    $CompilerPath = $candidates | Where-Object { Test-Path -LiteralPath $_ } | Select-Object -First 1
}
if (-not $CompilerPath) { throw 'Install Inno Setup 6 or pass -CompilerPath pointing to ISCC.exe.' }
& $CompilerPath /Q packaging\installer.iss
if ($LASTEXITCODE -ne 0) { throw 'Installer build failed.' }
$version = ((Get-Content 'packaging\installer.iss' -First 1) -split '"')[1]
Sign-ReleaseFile "dist\SR Inqly Setup $version.exe"
& $Python scripts\package_release.py
if ($LASTEXITCODE -ne 0) { throw 'Archive verification failed.' }
