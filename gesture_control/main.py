import argparse
import atexit
import logging
from pathlib import Path
import signal
import time
from .config import ROOT, load_config
from .controllers.events import EventSink
from .gestures.gesture_engine import GestureEngine
from .utils.logger import configure


def parser():
    result = argparse.ArgumentParser(description='GestureControl: local webcam hand control. Esc pauses; F12 exits.')
    result.add_argument('--dry-run', action='store_true', help='Print events; never construct OS input controllers')
    result.add_argument('--debug', action='store_true')
    result.add_argument('--calibrate', action='store_true')
    result.add_argument('--use-defaults', action='store_true', help='Use default thresholds without requiring saved calibration')
    result.add_argument('--camera', type=int)
    result.add_argument('--no-preview', action='store_true')
    result.add_argument('--config', type=Path, default=ROOT/'settings.json')
    result.add_argument('--calibration-file', type=Path, default=ROOT/'calibration.json')
    result.add_argument('--model', type=Path, default=ROOT/'models'/'hand_landmarker.task')
    result.add_argument('--list-cameras', action='store_true')
    result.add_argument('--check', action='store_true', help='Verify imports and run local inference on a blank image; no camera or controls')
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    sink = EventSink(dry_run=args.dry_run)
    camera = tracker = safety = None
    configure(args.debug)
    try:
        c = load_config(args.config, args.calibration_file)
        if args.camera is not None: c.camera_index = args.camera
        if args.no_preview: c.show_preview = False
        c.validate()
        configure(args.debug or c.debug_mode)
        import cv2
        from .camera.camera_manager import CameraManager, probe_cameras
        from .vision.hand_tracker import HandTracker
        if args.list_cameras:
            print('Available camera indices:', probe_cameras(c))
            return 0
        tracker = HandTracker(c, args.model)
        if args.check:
            import numpy as np
            hands = tracker.detect(np.zeros((480,640,3),dtype=np.uint8),time.monotonic())
            print(f'Local inference passed: {len(hands)} hands on blank input; no camera or OS events.')
            return 0
        from .controllers.windows import WindowsBackend, screen_size
        from .controllers.safety import SafetyMonitor
        from .ui.calibration import Calibration
        from .ui.overlay import draw
        calibration = Calibration(c, args.calibration_file) if args.calibrate or (not args.use_defaults and not args.calibration_file.exists()) else None
        if calibration and not c.show_preview:
            raise ValueError('First launch requires preview calibration. Run python main.py --calibrate first.')
        # Calibration and dry-run never instantiate mouse or keyboard controllers.
        if not args.dry_run and not calibration: sink.backend = WindowsBackend()
        engine = GestureEngine(c, sink, screen_size())
        safety = SafetyMonitor(sink, c.resume_hotkey)
        safety.start()
        atexit.register(sink.disable)
        def shutdown(signum, frame):
            sink.disable()
            safety.quit_event.set()
        for name in ('SIGINT', 'SIGTERM', 'SIGBREAK'):
            if hasattr(signal, name): signal.signal(getattr(signal,name), shutdown)
        camera = CameraManager(c)
        camera.open()
        print('GestureControl starting. Esc pauses, F12 exits. '+c.resume_hotkey+' enables control.',flush=True)
        if calibration: print('Calibration first: follow the preview. No OS control is enabled.')
        # Start paused. A deliberate hotkey arms real or simulated control.
        failures = 0
        fps, previous = 0., time.monotonic()
        key = -1
        while not safety.quit_event.is_set():
            try: frame = camera.read()
            except RuntimeError as exc:
                sink.disable()
                engine.cancel('camera failure')
                logging.getLogger(__name__).warning('%s', exc)
                camera.close()
                if failures >= c.reconnect_attempts:
                    raise RuntimeError('Camera recovery exhausted. Run python main.py --list-cameras or choose --camera 1.') from exc
                failures += 1
                camera.open()
                continue
            safety.heartbeat()
            now = time.monotonic()
            frame = cv2.flip(frame, 1)
            hands = tracker.detect(frame, now)
            fps = .9*fps+.1/max(time.monotonic()-previous, .001)
            previous = time.monotonic()
            if calibration:
                sink.disable()
                calibration.update(hands, key)
                if calibration.done:
                    print('Calibration saved. Launch python main.py --dry-run to test, or python main.py for real control.')
                    break
            else: engine.update(hands, now)
            if c.show_preview:
                cv2.imshow('GestureControl', draw(frame,hands,engine,fps,now,calibration.message() if calibration else None))
                key = cv2.waitKey(1) & 0xFF
                if key == 27: sink.disable()
                if key in (ord('g'), ord('G')) and calibration is None: sink.enable()
                if cv2.getWindowProperty('GestureControl', cv2.WND_PROP_VISIBLE) < 1: break
        return 0
    except (Exception, KeyboardInterrupt) as exc:
        sink.disable()
        logging.getLogger(__name__).error('%s', exc, exc_info=args.debug)
        return 1
    finally:
        # Each independent cleanup is attempted even if another resource raises.
        for resource, method in ((sink,'disable'),(safety,'close'),(camera,'close'),(tracker,'close')):
            if resource is not None:
                try: getattr(resource,method)()
                except Exception: logging.getLogger(__name__).exception('Cleanup failed: %s', method)
        try:
            import cv2
            cv2.destroyAllWindows()
        except (ImportError, AttributeError): pass
        atexit.unregister(sink.disable)
