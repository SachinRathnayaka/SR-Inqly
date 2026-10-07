# Repository preparation verification

Prepared on **October 7, 2026** from the existing SR Inqly **2.0.4** source. No GitHub repository or release was created by the preparation process.

## Source migration

Application modules were moved into `src/` and renamed by responsibility. Imports and mock targets were migrated together. Source resource paths resolve from the repository root; bundled resources continue to resolve from PyInstaller's resource directory. Tests moved to `tests/check_*.py`; build/installer definitions moved to `packaging/`.

The existing text-cache, GitHub input-release, cursor, eight-button Fetcher and tool-toggle fixes were preserved. Source comparison and local tests verify the migration rather than relying only on historical reports.

## Local checks

- Five headless document/renderer checks passed, including populated-text movement, cache eviction and exact cache/direct pixels.
- Twenty source checks passed from the new layout, covering Windows interaction, native region capture/clipboard, cursor settings, themes, inline text, selection, Fetcher, screenshots, opacity and tool toggles.
- Actual app controls were captured over a generated demonstration canvas for the README. Banner, full/compact/light layouts, inline text, Fetcher and splash images were inspected locally.

The organized source built successfully with PyInstaller. The packaged EXE passed icon DLL loading, desktop startup, toolbar reachability, Escape and clean exit checks. Inno Setup compiled the Windows installer successfully; portable/source ZIP integrity checks passed and SHA-256 checksums were generated. Installation/uninstallation was not repeated during this repository preparation.

Historical benchmark files were copied as evidence and are labeled as historical; a new long performance soak was not run for this documentation migration.

## Workflow

Renderer CI is supplied for Windows-hosted GitHub runners using the current documented [checkout](https://github.com/actions/checkout) and [setup-python](https://github.com/actions/setup-python) usage. No remote workflow execution is claimed before publication.

## Limits

Repository preparation is not Store certification, code signing or a complete third-party licensing audit. The original custom Source Available license remains in effect. Physical monitor/high-refresh cases and long soak coverage remain as documented in the README.
