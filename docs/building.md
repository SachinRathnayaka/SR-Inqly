# Build and verification guide

## Environment

Use Windows 10/11 and Python 3.13. Tested runtime: PySide6 6.11.2. Tested packaging tools: PyInstaller 6.22.3 and Inno Setup 6.7.3. Runtime and Python build dependencies are pinned in `requirements.txt` and `requirements-dev.txt`. Inno Setup is installed separately.

```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe run.py
```

Run these commands from the repository root. Source resources resolve from `assets/`; frozen resources resolve from the bundled resource directory.

## Checks

```powershell
.\.venv\Scripts\python.exe scripts/run_checks.py --headless
.\.venv\Scripts\python.exe scripts/run_checks.py --all
```

The six headless checks cover the document, command/raster caches, memory accounting, cache eviction, stale text and temporal pen effects. Native checks include a passive Desktop neon drag over an underlying test window; they use desktop focus and may change the clipboard. Do not run native checks alongside screenshot capture or another GUI test. Output screenshots and test fixtures go under the ignored `build/test-artifacts/` directory.

The package check requires `dist/SR Inqly/SR Inqly.exe`. It checks normal startup, desktop input release, toolbar reachability, Esc and process exit. It is included in the release script.

## Release

```powershell
powershell -ExecutionPolicy Bypass -File scripts/build_release.ps1 `
  -Python ".\.venv\Scripts\python.exe" `
  -CompilerPath "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
```

`-CompilerPath` is optional when the compiler is in a detected location. The script builds `packaging/windows.spec` and `packaging/installer.iss`. It generates:

- `dist/SR Inqly/SR Inqly.exe` and its `_internal` runtime folder.
- `dist/SR.Inqly.Setup.2.1.0.exe` (the packaging script copies the Inno filename to this release asset name).
- `dist/SR-Inqly-2.1.0-Windows-Portable.zip`.
- `dist/SR-Inqly-2.1.0-Source.zip`.
- `dist/SHA256SUMS-2.1.0.txt`.

Version 2.1.0 remains the application version because the repository preparation does not add a new software feature. Future version changes must update `src/branding.py`, the toolbar caption in `src/application.py`, `packaging/windows_version.txt`, `packaging/installer.iss`, the changelog and release documentation together.

The PyInstaller spec deliberately excludes incompatible unversioned ICU DLLs that can otherwise cause QtCore import failures. Preserve that exclusion.

## Diagnostic measurements

```powershell
& ".\dist\SR Inqly\SR Inqly.exe" --performance-check "build\performance-local.json" 120
```

This records packaged renderer timings and a bounded synthetic stress test. It uses the Windows desktop, then offscreen rendering. Historical measurements in `docs/benchmarks/` are evidence from previous local runs, not promises for other hardware. Physical display hotplug/high-refresh checks and a 30–60 minute soak remain separate release gates.

## Documentation screenshots

```powershell
.\.venv\Scripts\python.exe scripts/capture_screenshots.py
```

This renders real application controls over a generated demonstration canvas rather than collecting private desktop content. Inspect updated images before committing them.

## Signing

These builds are unsigned. Signing requires a suitable certificate/signing service and a separate signing workflow. Keep certificate material and credentials outside the repository. Signing changes the binary hashes, so regenerate checksums after signing. The installer should embed the final signed application if a signed release is produced.
