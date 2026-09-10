# GestureControl

A local Windows 10/11 webcam hand controller built with Python 3.11, OpenCV and the current MediaPipe **Tasks HandLandmarker** API. Inference uses the CPU. No cloud inference, telemetry, frame recording, image uploads, or runtime network requests. Only package installation and the explicit model-download script need internet access.

**Starts paused. Press Ctrl+Alt+G to enable, Esc to pause, F12 to quit.** Controls work globally, even when the preview is unfocused. After enabling, show an unpinched hand briefly before performing a gesture. Always test in dry-run first.

## Installation (Windows PowerShell)

```powershell
cd D:\gai
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python scripts\download_model.py
python main.py --check
python main.py --calibrate
python main.py --dry-run
python main.py
```

If activation is blocked by PowerShell policy, use `.\.venv\Scripts\python.exe` instead of `python` in each command; activation is optional. Runtime-only installations can use `requirements.txt`. Windows x64 and Python 3.11 are verified; other Python versions need compatible package wheels. No administrator rights are required.

The model is already downloaded in this workspace. The script verifies its SHA-256 and downloads the versioned official model only when needed. To install offline, transfer the repository, matching package wheels, and the model file to the target PC. The application never downloads anything automatically.

## Launch commands

On this PC, double-click **GestureControl.bat** on the Desktop. It uses the project's virtual environment and launches real control with default settings when calibration is absent. Click the preview and press **G** to enable. The repository also includes `Start GestureControl.bat` for launching directly from its folder.

```powershell
python main.py --calibrate          # Guided preview, no OS input controllers
python main.py --dry-run            # Print recognized actions; enable with Ctrl+Alt+G
python main.py --debug              # Structured diagnostic logs
python main.py                     # Real control, initially paused
python main.py --use-defaults      # Real control without the first-launch calibration wizard
python main.py --camera 1           # Alternate camera
python main.py --no-preview         # Requires completed calibration
python main.py --list-cameras       # Probe indices 0 through 4
python main.py --check              # Blank-image model inference, no camera or inputs
python main.py --config settings.json --calibration-file calibration.json
```

Close the preview or press F12 to exit. Esc pauses rather than exiting. Ctrl+C in the console also shuts down cleanly. The resume shortcut is configurable as `resume_hotkey` using pynput hotkey syntax. There is no automatic resume after a camera failure or watchdog timeout.

You can also press **G while the preview is focused** to enable control. The preview explicitly labels REAL CONTROL, DRY RUN (no OS actions), or CALIBRATION. `--use-defaults` uses existing configuration and any saved calibration, but allows startup when calibration has not yet been saved.

## Calibration

First launch automatically enters calibration. Stand in good light with the full hand visible; keep the camera stationary.

1. Show your dominant open palm; hold steady until at least 12 samples are present, then Space.
2. Touch thumb and index, hold steady, then Space to measure a comfortable pinch.
3. Point at your comfortable upper-left reach, hold steady, then Space.
4. Point at your comfortable lower-right reach, hold steady, then Space. The interaction rectangle must span at least a quarter of the preview in both directions.
5. Adjust sensitivity with `+`/`-` and smoothing with `[`/`]`; Enter saves and exits. These controls set values for the next dry-run; calibration never moves the real pointer.

Samples are kept in a bounded in-memory buffer; no images are stored. Median hand size, pinch distance, and reach coordinates reduce single-frame noise. The upper-left boundary is kept below the tab strip. `calibration.json` stores only seven calibration fields. Those fields override `settings.json`; edit the calibration file or recalibrate to change them. Other thresholds remain controlled by `settings.json`.

## Gesture cheat sheet

All directions refer to the **mirrored preview**. Right is the default dominant hand; calibration chooses yours. `auto` locks the first confidently detected hand for that session. The other hand is the media hand. Use one hand at a time except for zoom and emergency stop.

| Action | Gesture |
| --- | --- |
| Pointer | Dominant index extended, middle/ring/pinky folded. Move inside the outlined rectangle. |
| Left click | Dominant thumb–index pinch below the tab strip; hold at least 90 ms and release before 550 ms. One click occurs on confirmed release. |
| Drag/drop | Same pinch held at least 550 ms: button goes down, index moves the pointer, release drops. No preceding click. |
| Double click | Dominant index, middle and ring extended, pinky folded. Hold about 1 second. One deliberate double-click per hold. |
| Right click | Dominant thumb–middle pinch with thumb–index unpinched, then release. |
| Scroll | Dominant index and middle extended; ring/pinky folded. Move upward/downward. Pointer remains still. |
| Zoom | Bring both hands into view and pinch thumb–index on both together, before another gesture activates. Move hands apart/together while maintaining pinches. Release either pinch to finish. |
| Reset zoom | Media hand: index/middle/ring extended, pinky folded; hold about 1 second. Sends Ctrl+0. |
| Next/previous tab | Begin a dominant thumb–index pinch **above the purple horizontal line**, hold briefly, slide right/left at least 18% of preview width, then release within 2 seconds. |
| Volume | Media hand: index extended, other fingers mostly folded. Draw clear circles of moderate size. Clockwise increases; counter-clockwise decreases. |
| Play/pause | Media hand open palm, stationary for about 1 second. |
| Next/previous track | Media hand open palm, then swipe right/left **before** the stationary hold fires. One action per pose. |
| Mute/unmute | Media hand closed fist, held about 1 second. |
| Emergency pause | Esc immediately, or both open palms for 1 second. |
| Resume | Ctrl+Alt+G, then an unpinched hand for about 180 ms. |

The dedicated three-finger double-click avoids accidentally interpreting two short pinches as an application double-click. Windows can still interpret two real clicks close together according to its own double-click setting; leave a deliberate gap when two separate clicks are intended.

**Tab grabs and drags are latched by their starting zone.** Dragging into the top zone never switches tabs. Starting in the tab zone never holds a mouse button. For two-hand zoom, present the pinches together; an already-active drag retains ownership until released.

Optional `window_gestures: true` enables media-hand two-finger swipes for Alt+Tab / Alt+Shift+Tab, a stationary two-finger hold for Task View, and a four-finger hold (thumb folded) for Show Desktop. `direct_tabs: true` enables held poses from `direct_tab_mapping` (default four fingers → tab 1, three fingers → tab 2). Direct tabs override the corresponding media hold. These options are disabled by default. Application closing and experimental window resizing are deliberately not implemented.

## Tuning

Restart after editing JSON. Invalid configuration is rejected at startup.

| Setting | Default | Effect |
| --- | --- | --- |
| `pinch_threshold` / `pinch_release` | .28 / .42 hand-size units | Smaller activation threshold is stricter. Release must be larger, providing hysteresis. Calibration overrides these. |
| `click_hold_ms` / `drag_hold_ms` | 90 / 550 | Increase confirmation to reject brief pinches; increase drag hold if clicks become drags. |
| `hold_ms` / `release_ms` | 180 / 65 | Pose confirmation and release debounce. |
| `gesture_cooldown_ms` | 350 | Pause between completed incompatible gestures. |
| `cursor_sensitivity` | 1.0 | Higher values cover the screen with less travel. Calibration overrides it. |
| `cursor_smoothing` | .12 seconds | Higher smooths more; adaptive speed response reduces fast-motion lag. Calibration overrides it. |
| `scroll_deadzone` / `scroll_speed` | .012 / 80 | Minimum accumulated preview displacement; wheel units per full vertical travel. |
| `scroll_smoothing` / `scroll_max_rate` | .07 s / 18 | Smooth scroll movement and cap wheel events per second. |
| `zoom_threshold` | .25 | Change in hand separation divided by current mean hand size per zoom step. |
| `tab_zone_y` / `tab_swipe_distance` | .22 / .18 | Top strip boundary and required horizontal displacement, in preview fractions. |
| `volume_angle_step` | 25 degrees | Angular travel per volume-key press after circular recognition. |
| `volume_min_radius` | .035 | Minimum radius in aspect-corrected image-width units. Increase to ignore small loops. |
| `volume_fit_error` | .20 | Maximum radial standard deviation divided by fitted radius. Lower is stricter. |
| `volume_min_arc` | 100 degrees | Required initial trajectory arc; activation does not replay the initial arc. |
| `tracking_loss_ms` | 200 | Maximum gap before gesture cancellation and input release. |
| `confidence_threshold` | .65 | MediaPipe detection/presence/tracking threshold and handedness confidence filter. |
| `finger_angle` | 155 degrees | Required joint straightness for extended fingers. |
| `camera_width` / `camera_height` | 640 / 480 | Requested camera resolution. Actual camera output may differ. |

Finger/pinch geometry uses hand-relative distances and aspect-corrected coordinates. Movement zones use normalized preview fractions; screen mapping uses physical primary-monitor pixels and clamps to bounds. The model's handedness confidence is not a calibrated gesture probability. The overlay shows that confidence alongside the temporal gesture state.

## Safety and architecture

- A single `EventSink` serializes input and emergency cleanup with a reentrant lock. The vision layer never sends OS input.
- Temporal states are IDLE, POTENTIAL_GESTURE, GESTURE_STARTED, GESTURE_ACTIVE, GESTURE_FINISHED and COOLDOWN. Pose holds, separate activation/release thresholds, release debounce and latched ownership prevent competing actions.
- Emergency candidates preempt all modes; active gestures otherwise retain ownership. New gestures use explicit priority: pinch/click, zoom, scroll, tab, media, pointer. Two simultaneous pinches explicitly select zoom before ownership begins.
- A drag releases on confirmed unpinch, tracking loss, camera error, Esc, both-palms stop, F12, normal shutdown, handled exceptions and signals. A watchdog pauses control if processing stops responding for 2 seconds. Resume invalidates old gesture state.
- Native camera drivers run in a separate process with a one-frame queue. Timeouts reject stale frames; reconnects are limited. A stuck capture process is terminated during cleanup.
- The circular detector uses a fixed 64-point trajectory, least-squares circle fitting, covariance-based line rejection, radius consistency, signed angle unwrapping, direction consistency and stop reset. It emits bounded steps without moving the pointer.
- `--dry-run` constructs no mouse/keyboard **output** controllers. A keyboard **listener** still receives safety hotkeys. Events print as `MOUSE_MOVE x y`, `LEFT_CLICK`, `DRAG_START`, `DRAG_END`, `SCROLL n`, `ZOOM_IN`, `TAB_NEXT`, `VOLUME_UP`, etc. Its diagnostic history is bounded.
- Forced process termination, OS failure or power loss cannot guarantee a final input-release call. Use Esc for normal emergency pause. No software can guarantee cleanup after its process is forcibly killed.

## Repository

```text
GestureControl/                    # This repository is D:\gai
  main.py
  settings.json
  requirements.txt
  requirements-dev.txt
  requirements-lock.txt
  README.md
  VALIDATION.md
  .gitignore
  models/
    hand_landmarker.task           # Downloaded locally; ignored by Git
    hand_landmarker.sha256
  scripts/
    download_model.py
  gesture_control/
    __init__.py
    main.py
    config.py
    camera/camera_manager.py
    vision/geometry.py
    vision/gesture_features.py
    vision/hand_tracker.py
    gestures/gesture_state.py
    gestures/gesture_engine.py
    gestures/circle.py
    controllers/events.py
    controllers/windows.py
    controllers/safety.py
    ui/overlay.py
    ui/calibration.py
    utils/smoothing.py
    utils/logger.py
  tests/
    test_geometry.py
    test_engine.py
    test_safety_config.py
    test_app.py
```

Controller actions are consolidated in a small Windows adapter rather than many forwarding modules. Other platforms can implement the same `execute(Event)` / `release_all()` interface. Dry-run geometry and state logic are independent of that adapter. Package subdirectories also contain `__init__.py` files.

## Tests and verification

```powershell
python -m pytest -q
python -m compileall -q gesture_control scripts tests main.py
python -m pip check
python main.py --check
```

`requirements-lock.txt` records the full tested Windows/Python 3.11 environment; use `python -m pip install -r requirements-lock.txt` to reproduce it. Runtime requirements intentionally install only `opencv-contrib-python`, which MediaPipe requires; do not also install `opencv-python` or headless OpenCV into this environment because they share the `cv2` namespace.

See [VALIDATION.md](VALIDATION.md) for completed automated checks and the physical acceptance checklist. Live accuracy and 25–30 FPS remain dependent on camera, lighting, CPU and calibration; they have not been verified without an accessible webcam.

## Troubleshooting and limitations

- **No camera:** close Teams/Zoom/browser camera tabs; check Windows Settings → Privacy & security → Camera → desktop-app access. Try `--list-cameras`, `--camera 1`, another USB port, and 640×480. The application tries DirectShow and then Media Foundation. Probing is limited to five indices and may take several seconds per device.
- **Model missing/checksum failure:** rerun `python scripts/download_model.py`. The model comes from Google's official model bucket. If a firewall blocks it, download the versioned URL in that script manually and verify against the supplied checksum. There is no runtime download fallback.
- **Preview but no control:** it starts paused. Press the resume shortcut, briefly unpinch, then pose. Verify the hand label during calibration. Keep both hands apart; occlusion and handedness flips may cancel gestures.
- **Click instead of drag:** hold longer; drag uses the original pinch onset. **Drag instead of click:** release before `drag_hold_ms`. Keep click pinches below the tab line.
- **Unexpected scrolling/zoom:** fully fold ring/pinky for scrolling. Zoom requires both thumb–index pinches and has exclusive ownership. Release and wait for cooldown before changing modes.
- **Volume doesn't activate:** use the non-dominant hand, draw a sustained clear circle larger than the minimum radius, and keep your finger visible. The first arc is intentionally silent. After stopping, begin a fresh circle.
- **High CPU/low FPS:** use 640×480, improve lighting, close camera consumers, or disable preview after calibration. CPU-only performance varies. `--debug` and especially printing every dry-run pointer event can reduce FPS.
- **Hotkeys fail in an elevated application:** Windows privilege boundaries may block normal-process input. Test in a normal browser window. Full-screen games, secure desktops, login prompts and applications that reject synthetic input are not supported.
- **Multiple monitors:** physical resolution mapping currently targets the primary monitor, not the full virtual desktop. Mixed-DPI extended desktop control is not implemented.
- **Gesture ambiguity:** hand landmarks are a heuristic interface, not intent recognition. Distinct hand roles, activation zones and holds reduce but cannot eliminate false positives. Media shortcuts act on Windows' current media session; browser/window shortcuts act on the focused application.
- **Zoom depth:** two-hand zoom normalizes separation by live hand size, but large depth changes can still affect it. Keep hands approximately in the same plane.
- **Calibration tuning preview:** sensitivity and smoothing can be changed during calibration, but real cursor feel must be assessed afterward in dry-run/controlled use. Calibration never generates inputs.
- Native MediaPipe can print initialization warnings even in normal mode; these are not frame recording or network activity.

## Verified API sources

Implementation checked against the [official MediaPipe Python Hand Landmarker guide](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker/python), [official model overview](https://developers.google.com/edge/mediapipe/solutions/vision/hand_landmarker), and [pynput keyboard documentation](https://pynput.readthedocs.io/en/latest/keyboard.html). Installed APIs were also exercised locally: MediaPipe 1.0.1, OpenCV 5.0.0.93, NumPy 2.4.6 and pynput 1.8.2. No deprecated `mp.solutions.hands` calls are used.
