# Pen effects

## Neon pen

Select **Pen**, then tick **Neon** below the opacity slider. The selected ink color gets a soft glow and bright center. Permanent neon strokes support selection, movement, Undo/Redo and PNG export. The highlighter retains its separate settings.

## Temporary pen

Tick **Fade** and choose a hold time from **1 to 15 seconds** (default 3). Each sampled part of the stroke stays visible for that time, then fades smoothly over 0.9 seconds. The beginning disappears before the later parts; a long ongoing stroke can start fading while you are still drawing.

These are temporary presentation trails, not document objects. They cannot be selected or restored with Redo. Undo removes the newest visible temporary trail before normal document history; Clear removes all trails. Switching effects changes new strokes only. A screenshot includes trails that are still visible when captured.

## Desktop neon

Tick **Desktop neon** to enter click-through desktop mode and draw neon trails while holding the left mouse button over ordinary Windows apps. **Underlying clicks and drags still execute**: clicking a button activates it and dragging text can select it. Use ordinary Pen mode when you want to annotate without interacting with the application underneath.

Desktop trails always fade. Turn this option off to stop observing desktop mouse input; turn Neon off to disable it too. Clicking Pen enters ordinary drawing mode and pauses desktop observation until desktop mode resumes. Desktop neon is off after every restart. Secure Windows desktops/UAC and exclusive fullscreen applications are not covered by the overlay.

Windows Raw Input is registered only when explicitly enabled. It does not install a mouse hook, suppress events, record keyboard input, send input data over the network or save the mouse trail to disk. Registration is removed when disabled or the toolbar closes. Errors stop the observer without consuming the original event.

## Rendering and resource limits

Permanent annotations retain the existing raster/command caches. Temporary trails repaint only their affected rectangles. The animation timer runs while visible parts fade and stops when there is no pending trail work. During the hold interval it waits for the next fade deadline instead of continuously repainting.

Temporary data is capped at 64 trails and 16,384 points; oldest trail data is discarded under pressure. Neon rendering uses layered paths rather than a full-screen blur. Mixed-DPI, multiple-monitor and high-refresh physical testing still applies; no fixed FPS guarantee is made.
