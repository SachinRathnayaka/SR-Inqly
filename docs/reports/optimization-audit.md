# SR Inqly 2.0.2 optimization audit

## Findings

The changes reported from the other chat are present. The previous performance work was not removed: incremental freehand paths, dirty repaint regions, a 16 MiB accounted command cache, a 64 MiB raster layer, deduplicated 32 MiB/100-state undo history, a 128 MiB original-image budget, cached theme application and the blocking emergency-hotkey thread remain active. Cursor customization uses a bounded 32-entry cursor cache, not per-mouse-move image generation.

The GitHub input-release fix, plain drawing crosshair, saved cursor preferences with separate +/- buttons, eight direct Fetcher actions, modifier shortcuts and explicit shortcut icon are retained.

## Improvements

- Dirty scene repaint now checks retained object bounds before looking up or rebuilding compiled commands. Previously a small edit could scan/recompile commands for distant objects when the cache had evicted them. An eviction regression verifies identical pixels and only 3 command lookups for a local edit in a 189-object scene.
- Fetcher region-selection movement repaints the union of old/new rectangle bounds instead of requesting the full overlay.
- Icon variants are bounded to 256 cached entries; repeatedly choosing custom theme colors can no longer grow that cache without a limit.

## Capture investigation

The original native red/blue test failed once and passed on the next run without changing production capture code, confirming an intermittent result rather than proving a deterministic capture regression. The test previously relied on an ordinary desktop window being visible after a fixed delay. The fixture now stays above unrelated windows, waits for exposure and verifies its actual desktop pixels before the app captures them. Final output pixels and Windows clipboard availability are still checked exactly. A test-fixture correction is not a claim that every display/capture case is certified.

## Verification

Source checks cover exact cached/direct pixels, eviction behavior, history budgets, Fetcher actions/undo, cursor settings, GitHub input release, text drag/caret cleanup, native toolbar/Escape behavior, themes, About, display-change handling, opacity and quick screenshot saving. Packaged before/after measurements are stored separately as `performance-audit-before.json` and `performance-audit-after.json`.

Repaint measurements are offscreen microbenchmarks, not end-to-end input latency or display FPS. Hardware-specific multi-monitor/high-refresh cases and a 30–60 minute soak remain unverified. Version 2.0.2 distinguishes this audited build from the several earlier 2.0.1 builds.

## Packaged results

Same laptop, 1,000 strokes with 100 points each, antialiasing enabled, 1920x1080 image. Baseline recorded September 27; final run September 28, 2026. Runs were not simultaneous or controlled for all background load.

| Measurement | Existing 2.0.1 | Audited 2.0.2 |
| --- | ---: | ---: |
| Cold full paint | 99.04 ms | 94.92 ms |
| Unchanged small region median | 0.07145 ms | 0.07105 ms |
| Unchanged full paint median | 0.4524 ms | 0.4314 ms |
| History checkpoint median | 8.46 ms | 8.21 ms |
| Diagnostic idle, one-core CPU | 0.13% | 0.13% |
| Destructive stress duration / cycles | 30.18 s / 148 | 120.22 s / 435 |

These close repaint timings confirm the prior raster optimization remains active; they do not establish a large overall speedup. Destructive stress throughput was lower in the later run (3.62 versus 4.90 cycles/second), so no universal performance improvement is claimed. That workload replaces most objects and cannot benefit much from local-edit culling. The bounded-cache/local-edit regression separately demonstrates the targeted improvement without changing rendered pixels.

Final private bytes were 189,460,480 (about 180.7 MiB), with samples near 189 million throughout the last minute. Command accounting remained 16,776,640 bytes and history accounting 3,049,602 bytes. Normal packaged startup measured 3.99 seconds; its separate 12-second idle sample measured 0.52% of one core. The native packaged input/close check passed.

Tested main EXE SHA256: `b95ae8adfb1fa4ee751b26db940576207f58a2e387cc8a228faf3190424fbc97`.
