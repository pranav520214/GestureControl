"""Windows-specific input implementation. Never imported by the dry-run backend."""
import ctypes
import sys


def screen_size():
    if sys.platform != 'win32': return (1920, 1080)
    try: ctypes.windll.shcore.SetProcessDpiAwareness(2)
    except (OSError, AttributeError): ctypes.windll.user32.SetProcessDPIAware()
    return (ctypes.windll.user32.GetSystemMetrics(0), ctypes.windll.user32.GetSystemMetrics(1))


class WindowsBackend:
    def __init__(self):
        if sys.platform != 'win32': raise RuntimeError('Real control currently supports Windows only.')
        from pynput import keyboard, mouse
        self.key = keyboard.Key
        self.button = mouse.Button
        self.keyboard, self.mouse = keyboard.Controller(), mouse.Controller()
        self.held_keys = set()
        self.held_buttons = set()

    def chord(self, *keys):
        try:
            for key in keys:
                self.held_keys.add(key)
                self.keyboard.press(key)
        finally:
            self.release_keys()

    def release_keys(self):
        errors = []
        for key in tuple(self.held_keys):
            try:
                self.keyboard.release(key)
                self.held_keys.discard(key)
            except Exception as exc: errors.append(exc)
        if errors: raise errors[0]

    def release_all(self):
        errors = []
        try:
            for button in tuple(self.held_buttons):
                try:
                    self.mouse.release(button)
                    self.held_buttons.discard(button)
                except Exception as exc: errors.append(exc)
        finally:
            self.release_keys()
        if errors: raise errors[0]

    def execute(self, event):
        name, args, k = event.name, event.args, self.key
        if name == 'MOUSE_MOVE': self.mouse.position = tuple(map(int, args))
        elif name in ('LEFT_CLICK', 'RIGHT_CLICK', 'DOUBLE_CLICK'):
            button = self.button.right if name == 'RIGHT_CLICK' else self.button.left
            for _ in range(2 if name == 'DOUBLE_CLICK' else 1):
                self.held_buttons.add(button)
                try: self.mouse.press(button)
                finally:
                    self.mouse.release(button)
                    self.held_buttons.discard(button)
        elif name == 'DRAG_START':
            self.held_buttons.add(self.button.left)
            self.mouse.press(self.button.left)
        elif name == 'DRAG_END': self.release_all()
        elif name == 'SCROLL': self.mouse.scroll(0, int(args[0]))
        elif name == 'DIRECT_TAB': self.chord(k.ctrl, str(args[0]))
        else:
            chords = {
                'ZOOM_IN': (k.ctrl, '+'), 'ZOOM_OUT': (k.ctrl, '-'), 'RESET_ZOOM': (k.ctrl, '0'),
                'TAB_NEXT': (k.ctrl, k.tab), 'TAB_PREVIOUS': (k.ctrl, k.shift, k.tab),
                'VOLUME_UP': (k.media_volume_up,), 'VOLUME_DOWN': (k.media_volume_down,),
                'PLAY_PAUSE': (k.media_play_pause,), 'MUTE': (k.media_volume_mute,),
                'NEXT_TRACK': (k.media_next,), 'PREVIOUS_TRACK': (k.media_previous,),
                'APP_NEXT': (k.alt, k.tab), 'APP_PREVIOUS': (k.alt, k.shift, k.tab),
                'DESKTOP': (k.cmd, 'd'), 'TASK_VIEW': (k.cmd, k.tab)}
            self.chord(*chords[name])
