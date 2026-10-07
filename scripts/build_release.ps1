param([string]$CompilerPath = '', [string]$Python = 'python')
$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot
& $Python scripts\run_checks.py --headless
if ($LASTEXITCODE -ne 0) { throw 'Renderer checks failed.' }
& $Python -m PyInstaller --noconfirm packaging\windows.spec
if ($LASTEXITCODE -ne 0) { throw 'EXE build failed.' }
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
& $Python scripts\package_release.py
if ($LASTEXITCODE -ne 0) { throw 'Archive verification failed.' }
