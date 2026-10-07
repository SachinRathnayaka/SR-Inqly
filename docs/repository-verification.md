# Repository preparation verification

## 2.1.2 audit repairs — October 7, 2026

- 24 source/native regression checks passed, including actual Windows desktop input, Fetcher capture, text cleanup, tool toggles and the new audit regressions.
- Added headless coverage for curved neon hit/area/erase, capture allocation rejection/failure restoration, responsive DWM wait, cached time-binned fade geometry, source manifests, checksum mismatches and version mismatches.
- The same completed fading neon path rendered in 10.008 / 26.272 / 31.757 ms for 801 / 6318 / 12616 points versus 31.338 / 62.003 / 84.959 ms on 2.1.1. These are warmed offscreen medians, not end-to-end FPS. See `benchmarks/pen-fade-2.1.2.json` for inputs and scope.
- Source packaging now uses tracked/staged public files (or the prepared ZIP manifest), validates paths and known secret patterns, and rejects signing material. This is not a guarantee against every possible sensitive file.
- The public 2.1.1 portable download differed from its checksum; replacement checksum is generated from the actual downloaded artifacts. Installer/source matched.
- The app is free for personal/non-commercial use; commercial use requires developer permission. Original source distribution/rebranding restrictions remain.
- Trusted signing certificate absent; output remains unsigned. Physical mixed-DPI/high-refresh/sleep-wake and a long-duration soak are outstanding.


## 2.1.1 controls and smoothing verification — October 7, 2026

- All 22 source/native checks passed after the fixes, including old text-cache, selection, toolbar, Fetcher and DPI regressions.
- Fade delay minus/plus controls were exercised at 75%, 100% and 150% UI scale.
- Dense stroke half-fade opacity, expiry, bounded trail data and stopped idle timer passed.
- Native Raw Input test verified down/up delivery to an underlying Windows window, neon trail creation, width changes and compact effect toggles.
- The native target window is topmost during this test so another running overlay cannot intercept its injected clicks. Tests must run without simultaneous screenshot capture.
- Screenshots were refreshed using the generated demonstration canvas, including the new compact effect row.

Smoothing is verified in software. Perceived smoothness on different GPUs, 120/144 Hz displays and mixed-DPI monitor setups still requires physical testing; no fixed FPS is claimed.

## 2.1.0 pen effects verification — October 7, 2026

- All 22 source/native checks passed after the feature changes. Six headless checks passed during the release build.
- Temporal pixel tests verified that earlier stroke regions fade before later ones, fade alpha is smooth, and the animation timer stops after trails expire.
- Permanent neon cache pixels, Undo/Redo, glow bounds, highlighter isolation and temporary trail memory limits passed.
- A native Windows test window received left mouse down/up while passive raw mouse input simultaneously generated a neon trail; disabling Desktop neon unregistered the observer.
- Text editing, compact controls, toolbar hit masks and UI scaling passed at 75–150%.
- README screenshots were regenerated on a generated canvas. No private desktop screenshots were added.

The 2.1.0 packaged EXE passed icon DLLs, desktop startup, toolbar reachability, Escape and clean exit. Inno Setup compiled the installer; portable/source archives passed ZIP integrity checks and SHA-256 sums were generated. Installation/uninstallation was not repeated. The sections below describe the original 2.0.4 repository preparation.

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
