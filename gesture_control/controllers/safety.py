import threading
import time


class SafetyMonitor:
    def __init__(self, sink, hotkey, timeout=2.0):
        from pynput import keyboard
        self.sink = sink
        self.timeout = timeout
        self.beat = time.monotonic()
        self.stop_event = threading.Event()
        self.quit_event = threading.Event()
        self.hotkey = keyboard.HotKey(keyboard.HotKey.parse(hotkey), sink.enable)
        self.listener = keyboard.Listener(on_press=self.press, on_release=self.release)
        self.worker = threading.Thread(target=self.watch, daemon=True)

    def press(self, key):
        from pynput.keyboard import Key
        if key == Key.esc: self.sink.disable()
        if key == Key.f12:
            self.sink.disable()
            self.quit_event.set()
        self.hotkey.press(self.listener.canonical(key))

    def release(self, key):
        self.hotkey.release(self.listener.canonical(key))

    def start(self):
        self.listener.start()
        self.listener.wait()
        self.worker.start()

    def heartbeat(self):
        self.beat = time.monotonic()
        if not self.listener.is_alive():
            self.sink.disable()
            raise RuntimeError('Keyboard safety listener stopped; control disabled.')

    def watch(self):
        while not self.stop_event.wait(0.05):
            if self.sink.enabled and time.monotonic()-self.beat > self.timeout:
                self.sink.disable()

    def close(self):
        self.sink.disable()
        self.stop_event.set()
        self.listener.stop()
        if self.worker.is_alive(): self.worker.join(timeout=1)
