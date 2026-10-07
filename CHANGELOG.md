# Changelog

This source repository starts from the verified 2.0.4 application. Preparing the repository reorganizes filenames, imports, resource paths and build scripts; it does not introduce a new product version.

## 2.0.4

- Fix stale characters remaining after an existing text box was edited or moved.
- Use text layout bounds for cached text and rebuild the scene when text records change.
- Add a regression that uses populated text through repeated hide/edit/move cycles.

## 2.0.3

- Clicking the active tool returns to desktop mode.
- Esc and desktop-mode transitions clear tool highlights in full and compact layouts.
- Clicking a tool resumes drawing with its saved settings.

## 2.0.2

- Check retained object bounds before recompiling commands for local edits.
- Restrict Fetcher rectangle-drag repaints to changed areas.
- Bound icon variants to 256 cached entries.
- Audit the preserved rendering/history optimizations and record packaged measurements.

## 2.0.1

- Correct light/dark About text contrast.
- Keep the developer footer name informational; use the separate GitHub button for navigation.
- Release desktop input before opening the browser.
- Add a customizable crosshair with separate color, thickness, size, preview and saved preferences.
- Simplify Fetcher to eight direct actions with repeated-click and modifier behavior.
- Add a per-user Windows installer and explicit shortcut icon paths.

## 2.0.0

- Introduce SR Inqly branding, startup splash and centralized developer information.
- Add non-destructive Fetcher image objects, transforms, crop restoration and layer controls.
- Keep independent marker settings and persistent preferences.
- Introduce bounded rendering, history and image caches.
