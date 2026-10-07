# Changelog

## 2.1.0

- Add a neon pen glow using the selected color and shared pen opacity.
- Add temporary pen trails with a 1–15 second hold and smooth 0.9 second fade in drawing order.
- Add opt-in Desktop neon: passive Windows raw mouse input draws fading trails while normal desktop clicks continue.
- Expose effects below opacity in the full toolbar and inside the compact color menu.
- Keep temporary trails separate from permanent annotations and redo history; Undo removes the newest visible trail first.
- Stop animation while idle and bound temporary stroke memory. Do not persist Desktop neon across restarts.
- Include native click-through and temporal rendering regressions.

This source repository started from the verified 2.0.4 application.

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
