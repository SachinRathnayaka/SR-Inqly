# SR Inqly 2.0.1 implementation report

## Update 2.0.4 — stale text after editing/moving

QPicture reported an empty bounding rectangle for QTextDocument glyph runs. The raster cache therefore failed to clear old text when it was hidden for inline editing or moved. Text command bounds now come from QTextDocument layout. Text state changes rebuild the scene layer to also avoid clipped antialiasing seams; unchanged repaints and non-text local edits retain their caches. This correctness fix may cost more for moving committed text in a dense scene. Regression reproduces the old failure with actual non-empty text and now verifies exact pixels after repeated hide/edit/move operations. Text editing, native drag cleanup, cache bounds/budgets and tool toggle checks passed.

## Update 2.0.3 — tool toggle and desktop indication

Clicking the active tool now releases desktop input. Esc and all other desktop-mode transitions clear full and compact tool highlights while retaining the last tool/settings for resuming. Selecting a different tool activates it directly. The compact shapes control releases input when a shape tool is active; its next click opens the shapes menu. Native full/compact click, repeat-click, Escape, re-entry, GitHub-release and Windows hit-testing checks passed. Prior optimization measurements below are historical; rendering code was not changed in this UI update.

## Application and build

- Product, visible captions, menus, notifications, settings namespace, singleton identifier, screenshot folder/name and EXE metadata now identify **SR Inqly**.
- Main module renamed to `application.py`; production entry point is `launcher.py`; build specification is `SR Inqly.spec`.
- `branding.py` centralizes name, version, developer, official GitHub URL, copyright, source model and resource paths.
- `version_info.txt` supplies Windows file/product metadata and developer attribution.
- Historical release archives are not the active product; old binaries are not included in the new portable package.

## Branding, splash and developer information

- Supplied SR ribbon/pen identity was isolated with the image-editing tool and retained as `assets/sr-inqly-logo.png` with alpha transparency.
- Multi-resolution ICO includes 16/24/32/48/64/128/256 sizes; individual PNG icons and preliminary Store-size assets are included. Logo is used by the application icon, toolbar, splash and About panel.
- `branding_ui.py` implements a compact dark gradient splash with the requested title/tagline/attribution/source/copyright. Progress advances after actual module/resources, settings, tools/Fetcher and workspace initialization. No artificial sleep or fake progress timer. A 160 ms closing fade runs while the main UI is available.
- Footer GitHub button opens the central official HTTPS profile once per click using QDesktopServices. Hover text gives developer/license information without taking focus. About is in the Theme menu.
- `LICENSE` contains the requested restricted source-available model, with an explicit third-party-rights carve-out. It is not labeled an unrestricted open-source license. Third-party notices/license texts are included; public-distribution compliance is not certified.

## Drawing and settings

- Pen and highlighter now keep independent color/width/opacity; marker defaults are wider, semi-transparent, square-ended, with natural intensity increase across separate passes.
- `preferences.py` validates numeric/color values, restores defaults on malformed values and persists tool profiles, scale and toolbar location. Theme is persisted separately.
- Existing drawing, selection, text, opacity, theme, compact/full UI, screenshot, clipboard and emergency controls remain.

## Fetcher architecture and interaction

- `image_capture.py` owns image storage, rendering/transforms, crop UI, capture composition, selection handles and floating context controls.
- `Mark` stores immutable asset ID plus anchor, size, rotation, flip flags and normalized crop. Original pixels are not overwritten by edits; duplicate shares the original image while owning independent transformation state.
- Capture asynchronously waits for DWM after hiding UI, composites screen intersections at source DPR, creates/selects one image and returns to smart move/select mode.
- Corner resize preserves aspect by default; Shift permits free resize. Rotation handle supports free rotation; contextual actions cover ±90°, 180°, reset orientation, both flips, crop/full restore, duplicate, Windows image copy, all four layer actions and delete.
- Re-crop uses the original image and editable edges/corners. Crop, transforms, image creation/deletion and layers use document history. Drag gestures create one undo entry.
- Ctrl+C, Ctrl+D, Delete, Ctrl+Z, Ctrl+Y and Esc are supported. Context controls are not exported into screenshots or clipboard images.

## Performance, memory and monitor handling

- `render_cache.py`: compiled freehand paths / picture commands with bounds culling and 16 MiB accounted cache budget. Dirty updates cover drawing and image move/resize/rotation changes.
- `document_model.py`: immutable deduplicated history records, 100-state and 32 MiB limits. Image data is held separately, not serialized into each transform snapshot.
- Original image store has a 128 MiB cap and collects images no longer used by current state, clipboard or retained history. Old undo entries can be evicted to make capture room; captures cannot silently exceed the budget.
- 240 synthetic image create/delete cycles reached a stable 50 retained images for undo; all assets released after history clear. This is a short allocation test, not a long leak certification.
- Geometry/DPI changes are debounced, refresh bounds/cache and release input. Negative desktop origins are handled in region capture and screenshot export.
- Emergency exit uses an independent blocking Windows hotkey loop, with polling only as a fallback if registration is unavailable.
- Startup exceptions and unhandled UI failures have local diagnostic logging; capture/clipboard failures produce meaningful messages.

## Tests

- Existing document/render, area selection/group movement, inline text/caret/drag cleanup, opacity separation, theme/compact UI, quick screenshot, native input and packaged launch/close checks.
- Fetcher create/cancel, resize, aspect ratio, transforms, crop restoration, independent duplicates, clipboard bitmap availability, layer ordering, keyboard duplicate and undo/redo.
- Native desktop red/blue reference region captured at effective Qt scaling 100/125/150/175/200%, producing the expected 200/250/300/350/400-pixel output widths for a 200-logical-pixel selection.
- Staged splash/fade, official URL targets, single-click dispatch, malformed settings fallback and preference persistence.
- Cached/uncached pixel equality and history/cache budgets.
- Packaged 1,000-stroke × 100-point renderer and repeated clear/delete/undo/redo diagnostics. Exact timings and process-memory samples are in `performance-release.json`; normal startup/idle is in `performance-startup-idle.json`.

## Limitations / release status

- Windows portable, windowed PyInstaller build. Installer is unsigned; not an MSIX submission or Store-certified product; no GitHub publication was performed.
- Effective-scale testing used one physical display. Physical mixed-DPI multi-monitor hotplug, 4K dual monitors, sleep/wake, 120/144 Hz, exclusive fullscreen apps and pressure stylus input remain unverified. Pressure-aware rendering is not implemented.
- No 30–60 minute soak was completed. Short stable memory samples do not prove absence of every leak. Full dense-canvas repaint can exceed a 60 Hz frame budget; region microbenchmarks are not end-to-end FPS.
- Capture/copy is limited to 32 million pixels. Undo can discard older entries under its memory limits. Quick screenshot PNG encoding remains synchronous.
- Source-available license language is supplied as requested, not legal advice or a certification that every store's terms are compatible.

## File groups

Modified: `application.py` (renamed main), `document_model.py`, `selection_tools.py`, `text_editor.py`, `icons.py`, `appearance.py`, build spec, README and verification scripts.

Added: `branding.py`, `branding_ui.py`, `launcher.py`, `preferences.py`, `image_capture.py`, `render_cache.py`, `version_info.txt`, `LICENSE`, third-party notices/texts, `build_release.ps1`, branding assets, performance diagnostics/review and Fetcher/branding/display/performance verification scripts.

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

## 2.0.1 corrections and distribution

About explicitly sets foreground and background together for light, dark and custom themes. Native snapshots inspected for readable text. Footer developer name is a non-clickable QLabel with informational tooltip; only GitHub opens the profile. Installer uses per-user installation, a stable upgrade ID, Start menu entry, optional desktop shortcut and Windows uninstall registration. No autorun or administrator requirement. User screenshots/preferences are retained by uninstall. `github upload` contains source, assets, tests, build definitions, documentation and third-party license texts, excluding generated binaries/build folders.

2.0.1 verification: light/dark/custom About snapshots inspected; name-label click dispatches no URL; GitHub click dispatches exactly one URL. Actual installer installed to a separate test directory, registered version 2.0.1, launched successfully with toolbar/input/Escape/close checks, and uninstalled application files and its registration. Test install was removed.

Cursor/navigation fix: GitHub footer switches the overlay to desktop click-through before opening the browser, preventing the drawing surface from blocking browser input after focus changes. Drawing tools now use cached high-contrast tool badges with a precise crosshair hotspot; text, smart selection, move and desktop use native cursors. Toolbar retains the normal arrow. verify_cursor.py covers every tool, native Windows hit testing before browser dispatch, drawing re-entry, selection modes and Escape. verify_windows.py and verify_branding.py passed.

Cursor customization replaces tool badges: Theme > Cursor opens a preview with cursor color, line thickness (1-6 px), size (12-40 px), Restore Defaults, OK and Cancel. Preferences persist separately from ink color/width and UI theme. All drawing tools share the same centered + cursor, with native text/selection cursors retained. GitHub click-through fix is unchanged. verify_cursor_preferences.py, verify_cursor.py, verify_appearance.py and verify_windows.py passed.

Cursor numeric controls: replaced the small embedded spin arrows with separate 38x34 minus/plus buttons, explicit arrow cursors and accessible names. Regression checks hover hit targets, pointer shape, both click directions, maximum bounds, save/cancel and GitHub input release. Both cursor verification scripts passed.

Fetcher toolbar redesign: 14 buttons reduced to five (Crop, Transform menu, Copy menu, Layers menu, Delete). All 14 actions remain available. Action dispatch, transforms, crop, duplicate, clipboard, layers, undo/redo and deletion passed verify_fetcher.py with offscreen and Windows Qt backends. verify_cursor.py passed. The separate real-desktop capture color probe failed its expected-red assertion in this session; real screen pixel capture is not revalidated by the mocked capture tests. Original logo assets remain unchanged; installer shortcuts explicitly reference the packaged .ico. The desktop shortcut overlay badge has not been verified as removed.

Revised direct-action Fetcher toolbar: eight buttons, no menus. Rotate advances 90 degrees each click (Shift reverses, Ctrl resets orientation); horizontal/vertical flips toggle; Copy uses Shift for duplicate; layer up/down move one step (Shift moves to the boundary). Crop and Delete remain direct. Windows Qt mouse-click tests passed repeated rotation through 360, modifier actions, flip toggles, duplication, layers, clipboard, crop and undo/redo.
