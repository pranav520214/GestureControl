from types import SimpleNamespace
import importlib
import json
import pkgutil
import threading
import numpy as np
import gesture_control
from gesture_control.config import Config
from gesture_control.controllers.events import EventSink
from gesture_control.gestures.gesture_engine import GestureEngine
from gesture_control.ui.overlay import draw


def test_all_package_imports():
    for item in pkgutil.walk_packages(gesture_control.__path__,gesture_control.__name__+'.'):
        importlib.import_module(item.name)


def test_overlay_on_synthetic_frame():
    engine = GestureEngine(Config(),EventSink(dry_run=True))
    frame = np.zeros((480,640,3),dtype=np.uint8)
    result = draw(frame,[],engine,30.,1.,['Calibration'])
    assert result.shape == frame.shape and result.any()


def test_app_dry_run_never_constructs_output_backend(monkeypatch,tmp_path):
    import gesture_control.controllers.windows as windows
    import gesture_control.controllers.safety as safety
    import gesture_control.camera.camera_manager as camera
    import gesture_control.vision.hand_tracker as tracker
    import gesture_control.main as app
    closed = []
    def forbidden(): raise AssertionError('Output backend constructed in dry-run')
    monkeypatch.setattr(windows,'WindowsBackend',forbidden)
    class FakeTracker:
        def __init__(self,*args): pass
        def detect(self,*args): return []
        def close(self): closed.append('tracker')
    class FakeCamera:
        def __init__(self,*args): self.count = 0
        def open(self): pass
        def read(self):
            self.count += 1
            if self.count > 2: raise KeyboardInterrupt()
            return np.zeros((480,640,3),dtype=np.uint8)
        def close(self): closed.append('camera')
    class FakeSafety:
        def __init__(self,*args): self.quit_event = threading.Event()
        def start(self): pass
        def heartbeat(self): pass
        def close(self): closed.append('safety')
    monkeypatch.setattr(tracker,'HandTracker',FakeTracker)
    monkeypatch.setattr(camera,'CameraManager',FakeCamera)
    monkeypatch.setattr(safety,'SafetyMonitor',FakeSafety)
    calibration = tmp_path/'calibration.json'
    calibration.write_text('{}')
    assert app.main(['--dry-run','--no-preview','--calibration-file',str(calibration)]) == 1
    assert set(closed) == {'tracker','camera','safety'}
