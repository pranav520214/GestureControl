from dataclasses import dataclass
from collections import deque
import logging
import threading
import time


@dataclass(frozen=True)
class Event:
    name: str
    args: tuple = ()


class EventSink:
    """One synchronized gateway owns all OS input, including emergency release."""
    def __init__(self, backend=None, dry_run=False):
        self.backend = backend
        self.dry_run = dry_run
        self.enabled = False
        self.generation = 0
        self.lock = threading.RLock()
        self.history = deque(maxlen=128)
        self.last_event = ('', 0.0)
        self.dragging = False

    def enable(self):
        with self.lock:
            self.generation += 1
            self.enabled = True

    def disable(self):
        with self.lock:
            self.enabled = False
            self.generation += 1
            self.release()

    def release(self):
        with self.lock:
            try:
                if self.dragging:
                    self._send(Event('DRAG_END'))
            finally:
                if self.backend is not None and not self.dry_run:
                    self.backend.release_all()
                self.dragging = False

    def emit(self, event):
        with self.lock:
            if not self.enabled: return
            self._send(event)

    def _send(self, event):
        self.history.append(event)
        self.last_event = (event.name, time.monotonic())
        if event.name == 'DRAG_START': self.dragging = True
        if self.dry_run:
            print(event.name, *event.args, flush=True)
        elif self.backend is not None:
            self.backend.execute(event)
        if event.name == 'DRAG_END': self.dragging = False
        if event.name != 'MOUSE_MOVE':
            logging.getLogger(__name__).debug('OS event %s %s', event.name, event.args)
