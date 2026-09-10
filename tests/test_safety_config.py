import json
import queue
import threading
import time
from dataclasses import replace
from types import SimpleNamespace
import pytest
from gesture_control.config import Config, load_config
from gesture_control.controllers.events import EventSink, Event
from gesture_control.controllers.windows import WindowsBackend
from gesture_control.camera.camera_manager import CameraManager
from gesture_control.controllers.safety import SafetyMonitor
from gesture_control.ui.calibration import Calibration
from test_engine import hand


@pytest.mark.parametrize('changes',[{'pinch_release':.1},{'drag_hold_ms':10},{'zoom_threshold':0},
                                  {'dominant_hand':'invalid'},{'cursor_sensitivity':float('nan')},
                                  {'camera_width':0},{'show_preview':'false'},{'camera_index':1.5},
                                  {'interaction_region':[.5,.5,.2,.2]},{'tab_zone_y':.4}])
def test_config_rejects_invalid(changes):
    with pytest.raises(ValueError): replace(Config(),**changes).validate()


def test_calibration_saves_only_calibration_fields(tmp_path):
    path = tmp_path/'calibration.json'
    cal = Calibration(Config(),path)
    for pose in ('open','point'):
        for _ in range(24): cal.update([hand(pose,pinch=.2)],-1)
        cal.update([hand(pose,pinch=.2)],32)
    for x,y in ((.15,.3),(.85,.85)):
        for _ in range(24): cal.update([hand(x=x,y=y)],-1)
        cal.update([hand(x=x,y=y)],32)
    assert cal.stage == 4
    cal.update([],13)
    assert cal.done
    data = json.loads(path.read_text())
    assert 'camera_index' not in data
    c = load_config(tmp_path/'settings.json',path)
    assert c.dominant_hand == 'right' and c.pinch_threshold < c.pinch_release


def test_release_retry_even_when_drag_end_raises():
    class Backend:
        released = False
        def execute(self,event): raise RuntimeError('injected failure')
        def release_all(self): self.released = True
    b = Backend()
    sink = EventSink(b)
    sink.dragging = True
    with pytest.raises(RuntimeError): sink.disable()
    assert b.released and not sink.enabled and not sink.dragging


def test_modifier_cleanup_when_press_fails():
    backend = WindowsBackend.__new__(WindowsBackend)
    released = []
    def fail(key): raise RuntimeError('injected press failure')
    backend.keyboard = SimpleNamespace(press=fail,release=released.append)
    backend.held_keys = set()
    with pytest.raises(RuntimeError): backend.chord('ctrl','tab')
    assert released == ['ctrl'] and not backend.held_keys


def test_all_releases_attempted_after_failure():
    backend = WindowsBackend.__new__(WindowsBackend)
    attempts = []
    def fail(button):
        attempts.append(button)
        raise RuntimeError('injected release failure')
    backend.mouse = SimpleNamespace(release=fail)
    backend.keyboard = SimpleNamespace(release=attempts.append)
    backend.held_buttons = {'left','right'}
    backend.held_keys = {'ctrl'}
    with pytest.raises(RuntimeError): backend.release_all()
    assert set(attempts) == {'left','right','ctrl'}


def test_camera_timeout_and_stale_frame():
    camera = CameraManager(Config(camera_timeout=.01))
    camera.first = False
    camera.output = queue.Queue()
    with pytest.raises(RuntimeError,match='timed out'): camera.read()
    camera.output.put(('frame',(time.monotonic()-10,None)))
    with pytest.raises(RuntimeError,match='stale'): camera.read()


def test_watchdog_disables_stalled_processing():
    monitor = SafetyMonitor.__new__(SafetyMonitor)
    monitor.sink = EventSink(dry_run=True)
    monitor.sink.enable()
    monitor.sink.emit(Event('DRAG_START'))
    monitor.timeout = .01
    monitor.beat = time.monotonic()-10
    monitor.stop_event = threading.Event()
    worker = threading.Thread(target=monitor.watch)
    worker.start()
    time.sleep(.12)
    monitor.stop_event.set()
    worker.join(timeout=1)
    assert not monitor.sink.enabled and not monitor.sink.dragging


def test_escape_callback_disables_immediately():
    from pynput.keyboard import Key
    monitor = SafetyMonitor.__new__(SafetyMonitor)
    monitor.sink = EventSink(dry_run=True)
    monitor.sink.enable()
    monitor.sink.emit(Event('DRAG_START'))
    monitor.listener = SimpleNamespace(canonical=lambda k:k)
    monitor.hotkey = SimpleNamespace(press=lambda k:None)
    monitor.press(Key.esc)
    assert not monitor.sink.enabled and not monitor.sink.dragging
