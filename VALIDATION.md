# Validation record

Verified locally on Windows x64 / Python 3.11, 2026-09-10.

## Completed checks

| Check | Result |
| --- | --- |
| `python -m pytest -q` | **51 passed** |
| `python -m compileall -q gesture_control scripts tests main.py` | Passed |
| All application modules imported recursively | Passed in test suite |
| `python -m pip check` | No broken requirements |
| `python main.py --help` | CLI options match README |
| `python main.py --check` | MediaPipe Tasks instantiated; blank-image VIDEO inference passed |
| Model checksum | `fbc2a30080c3c557093b5ddfc334698132eb341044ccee322ccf8bcf3607cde1` verified |
| Installed API compatibility | MediaPipe 1.0.1 / OpenCV 5.0.0.93 / NumPy 2.4.6 / pynput 1.8.2 imported successfully |
| Dry-run isolation | Injected backend raises on output; tests pass. Full app test prohibits output-controller construction. |
| Camera probe | No usable cameras found at indices 0–4 |
| Real startup with unavailable camera | DirectShow/Media Foundation attempts, two reconnects, clear error, exit code 1, cleanup completed |

The installed environment is captured in `requirements-lock.txt`. MediaPipe's native initialization prints informational warnings; blank-image inference still succeeds.

## Test coverage

Geometry tests use synthetic landmark coordinates: Euclidean and normalized distance, scale invariance, finger extension/folding and rotation invariance, pinch extraction, horizontal swipe validation, signed angular movement and ±π wraparound. Synthetic trajectories verify clockwise/counter-clockwise volume steps and rejection of lines, tiny circles and stationary points.

State-machine tests verify timed confirmation, cooldown, hysteresis, click on release, no click before drag, one double-click per hold, right-click separation, cursor clamping, scroll ownership and stationary stopping, two-hand zoom, tab direction and cancellation, media holds/swipes, optional disabled mappings, tracking loss and long processing gaps, disable/resume rearming and two-palms preemption.

Failure tests inject keyboard-press and release exceptions, verify all cleanup attempts and retry release, simulate stale/absent camera frames, exercise the watchdog and Esc callback, check calibration persistence and configuration rejection, render the overlay on an artificial blank frame, import all modules, and verify full-app cleanup with a synthetic camera. Tests never send real mouse or keyboard events.

## Physical acceptance still required

No accessible webcam is available in this environment. These tests **do not prove live recognition accuracy, physical handedness labeling, real OS input behavior or 25–30 webcam FPS**. No real OS control was enabled during development.

After connecting a webcam, run calibration and the following dry-run checklist. Then repeat in a harmless browser/test window with real control enabled. Keep the physical keyboard available.

| User acceptance scenario | Automated evidence | Live status |
| --- | --- | --- |
| 1 Pointer covers the screen smoothly | Mapping/clamping and smoothing implementation | Pending hardware |
| 2 One pinch yields one click | Timed release test | Pending hardware |
| 3 Pinch hold drags and release drops | Drag start/end and no-click tests | Pending hardware |
| 4 Two-finger scrolling without pointer motion | Scroll arbitration/rate tests | Pending hardware |
| 5 Incremental application zoom | Two-hand zoom test | Pending hardware |
| 6 One tab switch in either direction | Left/right release tests and loss cancellation | Pending hardware |
| 7 Clockwise/counter-clockwise volume | Signed synthetic circle tests | Pending hardware |
| 8 Stationary hands do not repeat actions | One-shot holds, stationary scroll/circle tests | Pending hardware |
| 9 Lost hand releases drag | Tracking-loss test | Pending hardware |
| 10 Esc stops and releases | Direct safety callback test | Pending hardware |
| 11 Resume cleanly | Generation reset and unpinched rearm test | Pending hardware |
| 12 Dry-run changes no OS state | Backend isolation and app lifecycle tests | Verified by software tests; live gesture input pending |

Also unplug the camera during a dry-run drag and verify `DRAG_END`, paused status and bounded recovery. Test the resume shortcut with preview unfocused, both-palms emergency stop, dominant left-hand calibration, and the actual monitor resolution. Measure the displayed FPS for at least 30 seconds under representative lighting. Do not label live acceptance complete until these physical checks pass.
