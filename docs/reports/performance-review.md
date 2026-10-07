# SR Inqly 2.0 — performance review

## What the ten recommendations mean for this app

| Item | Assessment | Implementation / evidence |
| --- | --- | --- |
| 1. Reduce drawing latency | Correct. Qt already coalesces `update()` calls, but our old code requested the entire overlay and rebuilt all stroke paths. | Live pen/highlighter requests only the last segment's dirty rectangle. Shapes repaint the union of their old/new extents. Committed strokes use a bounded compiled-path / QPicture cache and bounds culling. Freehand events closer than 0.5 logical pixels are ignored; the release endpoint is retained. No aggressive smoothing that changes handwriting. |
| 2. Use GPU / target 60 FPS | Conditional, not a mandatory fix or a guarantee. QWidget/QPainter here uses raster rendering; GPU support requires an architectural change and additional transparency/input validation. | Kept the working raster overlay and measured it. Warm drawing microbenchmarks are **not** end-to-end FPS or pen latency. No 120/144 Hz certification. |
| 3. Idle CPU | Correct. Timers should do useful work only. | Emergency Ctrl+Alt+Q uses a blocking Windows hotkey message loop on its independent thread. A polling fallback remains only if registration fails. The text caret timer runs only while its editor is visible. There is no animation/render timer for a blank idle overlay. |
| 4. Memory leaks | Correct, but growing active documents or bounded history are not automatically leaks. A short plateau is not proof of leak freedom. | Snapshot and render-cache budgets, integrity tests, and a packaged stress sample. A 30–60 minute soak is still a release gate. |
| 5. Undo/Redo | Correct. The old app did not save screen bitmaps, but it deep-copied the complete Python mark graph. | Immutable serialized stroke records are deduplicated across snapshots. Up to 100 states, additionally capped by an accounted 32 MiB budget. Oldest states may be discarded earlier for very large documents. Deserialization accepts internally generated records only; there is no pickle file import. |
| 6. Overlay / DPI / monitors | Correct. Transparent composition still has a system cost beyond Python drawing time. | Preserve source-composition clearing (prevents old border trails), native toolbar input hole and click-through fail-safe. Monitor geometry/DPI signals trigger debounced geometry/cache refresh and desktop mode. Fixed screenshot annotation offset for negative virtual-desktop origins. Simulated geometry/DPI tests are not physical monitor hotplug tests. |
| 7. Input / UI work | Correct. | Incremental live QPainterPath, small-point filtering, region updates and cached committed commands. Theme CSS is no longer reapplied after every stroke. Screenshot capture still deliberately pauses briefly for DWM; PNG save is synchronous. Tablet pressure is **not implemented or verified**. |
| 8. Startup | Correct; measure before removing required imports. | No network, analytics or update checks in the startup path. Diagnostic code is loaded only with an explicit CLI flag. Required Qt imports remain. Startup measured from process launch until both windows exist. |
| 9. Release build | Correct in principle. “Enable compiler optimizations” is not directly equivalent for this Python/PyInstaller app. | Tested the actual windowed, onedir EXE (`debug=False`), not only source tests. Kept Python assertions; `-O` is not a substitute for fixing algorithms. No Store/MSIX build was tested. |
| 10. Stress / hardware matrix | Correct. | 1,000 strokes × 100 points, repeated delete/undo/redo/clear, cache pixel equality, native drag-trail checks and input safety. Hardware cases below remain unverified. |

## Recorded before/after comparison

Baseline was recorded before the changes; after-measurements use the current implementation. Workload: 1,000 strokes, 100 points each, 15 history snapshots; 1,920 × 1,080 image, 80 × 80 repaint region.

| Measurement | Before | After |
| --- | ---: | ---: |
| History checkpoint median, with tracemalloc enabled | 435.08 ms | 13.35 ms |
| Retained Python allocations for the snapshot test | 17,218,440 bytes | 2,502,528 bytes |
| Small-region painter median | 60.00 ms | 1.016 ms |

The drawing comparison uses a **warm cache** after compiling existing strokes. It excludes display presentation, DWM, input-device sampling and image clearing. Cold-cache timing and normal release timings are recorded separately in the JSON diagnostics. Tracemalloc allocation figures are not total application RAM. These are measurements on this laptop, not promises for every computer.

## Verification artifacts

- `performance-before.json`, `performance-after.json`: comparable source microbenchmarks.
- `performance-startup-idle.json`: normal packaged launch and 12-second idle CPU sample, including its normal emergency-hotkey thread.
- `performance-release.json`: packaged renderer and bounded stress diagnostics; includes display configuration and process memory samples.
- `verify_performance.py`: exact cached/uncached pixels for every mark type, mutation-safe undo/redo, bounded history/cache.
- `verify_text_drag.py`: native desktop old-pixel clearing, caret blinking and contextual toolbar placement.
- `verify_display_changes.py`: simulated virtual desktop / DPI changes.
- Existing document, selection, text, opacity, themes, screenshots, native input and packaged startup/close checks were rerun.

The rendering cache is capped at an accounted 16 MiB (compiled commands plus estimated retained mark objects). This is not a cap on the whole application's RAM. The active document remains user-controlled and can grow.

## Before describing this as a production-ready paid release

Still run a real 30–60 minute soak, physical monitor unplug/replug, sleep/wake, mixed 125–200% DPI, two 4K monitors, 120/144 Hz displays, pen pressure/high-frequency input, and fullscreen/exclusive apps. Check the intended distribution package on clean Windows machines. This review does not certify those cases or claim “100% optimized”.

Qt/PySide distribution also has licensing obligations. A paid app is not automatically forbidden, and payment does not remove LGPL/commercial-license obligations. Choose and review the applicable license/distribution route, including notices and the target store's conditions. This build is not a signed Store release or a licensing compliance certification.

## Primary references

- [Qt QWidget updates and event coalescing](https://doc.qt.io/qt-6/qwidget.html)
- [Qt QPaintEvent automatic region clipping](https://doc.qt.io/qt-6/qpaintevent.html)
- [Qt painting backends](https://doc.qt.io/qt-6/paintsystem-devices.html)
- [PyInstaller bytecode optimization](https://pyinstaller.org/en/stable/feature-notes.html)
- [Qt licensing](https://doc.qt.io/qt-6/licensing.html)
- [Qt LGPL obligations and distribution considerations](https://www.qt.io/development/open-source-lgpl-obligations)

## SR Inqly / Fetcher additions

See IMPLEMENTATION_REPORT.md for branding, startup, developer information and Fetcher functionality. The Fetcher allocation test completed 240 synthetic create/delete cycles. Effective Qt scaling 100/125/150/175/200% was exercised with native known-color capture/clipboard checks on one physical screen; this is not a physical multi-monitor test. Final packaged benchmark enables antialiasing, while the original source microbenchmark uses the default image painter settings.

## Final raster cache verification

Committed drawing also uses a 64 MiB maximum raster layer, updated only for changed object bounds. Unchanged repaints reuse those pixels. Oversized desktops fall back to the bounded command renderer. This is additional to the 16 MiB command cache, 32 MiB accounted history and 128 MiB original image store; these are not a total process RAM limit. `verify_scene_cache.py` checks exact pixels at 100/125/200% for add, move, reorder, delete, active-editor omission, clear and budget fallback. Cold rendering and changed scenes still cost more than unchanged repainting.

## Final packaged measurement — 2026-09-27

Actual frozen EXE, antialiasing enabled, 1,000 strokes × 100 points, 1920×1080 offscreen benchmark surface. Physical display: 1536×960 logical, DPR 1.25, 60 Hz.

- Normal startup: 3.71 s. Normal 12-second idle: 0.00% of one CPU core (measurement resolution applies). Separate diagnostic idle: 1.43%; samples differ and neither promises zero CPU on every machine.
- Cold full paint: 107.23 ms. Unchanged full paint median: 0.568 ms. Unchanged 80×80 region median: 0.071 ms. These exclude presentation and input latency.
- History checkpoint median without tracemalloc: 8.20 ms.
- 120.05 seconds, 584 synthetic edit/delete/undo/redo/clear cycles. Private memory at 10 seconds: 184.6 MiB; at end: 183.2 MiB. Final minute approximately stable; not a long soak or leak-proof claim.
- The raster layer trades extra memory and cold/changed-scene work for cheap unchanged repaints. Full-scene destructive stress is not faster in every case.
- Source regression checks, raster pixel checks including rotated images, native text trail/input checks and packaged startup/close passed.
