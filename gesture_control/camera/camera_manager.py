"""Isolate potentially blocking camera drivers in a terminable child process."""
import multiprocessing as mp
import queue
import sys
import time


def _capture(index, width, height, output, stop):
    import cv2
    camera = cv2.VideoCapture(index, cv2.CAP_DSHOW if sys.platform == 'win32' else cv2.CAP_ANY)
    try:
        if not camera.isOpened() and sys.platform == 'win32':
            camera.release()
            camera = cv2.VideoCapture(index, cv2.CAP_MSMF)
        if not camera.isOpened():
            output.put(('error', f'Camera {index} cannot open. Close Teams/Zoom and check Windows camera permissions.'))
            return
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        camera.set(cv2.CAP_PROP_FPS, 30)
        while not stop.is_set():
            ok, frame = camera.read()
            item = ('frame', (time.monotonic(), frame)) if ok else ('error', 'Camera stopped delivering frames')
            try: output.put_nowait(item)
            except queue.Full: pass
            if not ok: return
    finally:
        camera.release()


class CameraManager:
    def __init__(self, config):
        self.c = config
        self.process = None
        self.output = None
        self.first = True

    def open(self):
        ctx = mp.get_context('spawn')
        self.output, self.stop = ctx.Queue(maxsize=1), ctx.Event()
        self.process = ctx.Process(target=_capture, args=(self.c.camera_index, self.c.camera_width,
                                  self.c.camera_height, self.output, self.stop), daemon=True)
        self.process.start()
        self.first = True

    def read(self):
        try: kind, value = self.output.get(timeout=8 if self.first else self.c.camera_timeout)
        except queue.Empty as exc: raise RuntimeError('Camera timed out or its driver stalled.') from exc
        self.first = False
        if kind == 'error': raise RuntimeError(value)
        captured, frame = value
        if time.monotonic()-captured > self.c.camera_timeout:
            raise RuntimeError('Camera frames are stale.')
        return frame

    def close(self):
        if self.process:
            self.stop.set()
            self.process.join(timeout=0.3)
            if self.process.is_alive():
                self.process.terminate()
                self.process.join(timeout=1)
            self.process.close()
            self.process = None
        if self.output:
            self.output.cancel_join_thread()
            self.output.close()
            self.output = None


def probe_cameras(config):
    from dataclasses import replace
    found = []
    for index in range(5):
        camera = CameraManager(replace(config, camera_index=index))
        try:
            camera.open()
            camera.read()
            found.append(index)
        except RuntimeError: pass
        finally: camera.close()
    return found
