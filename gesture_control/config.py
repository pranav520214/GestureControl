from dataclasses import asdict, dataclass, field
import json
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


@dataclass
class Config:
    camera_index: int = 0
    camera_width: int = 640
    camera_height: int = 480
    camera_timeout: float = 1.5
    reconnect_attempts: int = 2
    cursor_sensitivity: float = 1.0
    cursor_smoothing: float = 0.12
    interaction_region: list[float] = field(default_factory=lambda: [0.12, 0.28, 0.88, 0.90])
    pinch_threshold: float = 0.28
    pinch_release: float = 0.42
    click_hold_ms: int = 90
    drag_hold_ms: int = 550
    hold_ms: int = 180
    release_ms: int = 65
    scroll_deadzone: float = 0.012
    scroll_speed: float = 80.0
    scroll_max_rate: float = 18.0
    scroll_smoothing: float = 0.07
    zoom_step_seconds: float = 0.15
    zoom_threshold: float = 0.25
    gesture_cooldown_ms: int = 350
    tab_swipe_distance: float = 0.18
    tab_zone_y: float = 0.22
    swipe_vertical_tolerance: float = 0.12
    swipe_timeout: float = 2.0
    volume_angle_step: float = 25.0
    volume_min_radius: float = 0.035
    volume_fit_error: float = 0.20
    volume_min_arc: float = 100.0
    volume_stop_seconds: float = 0.4
    volume_step_seconds: float = 0.09
    media_stationary_distance: float = 0.06
    media_hold_ms: int = 850
    emergency_hold_ms: int = 1000
    tracking_loss_ms: int = 200
    confidence_threshold: float = 0.65
    finger_angle: float = 155.0
    dominant_hand: str = 'right'
    show_preview: bool = True
    debug_mode: bool = False
    hand_size: float = 0.15
    resume_hotkey: str = '<ctrl>+<alt>+g'
    window_gestures: bool = False
    direct_tabs: bool = False
    media_mapping: dict[str, str] = field(default_factory=lambda: {
        'open': 'PLAY_PAUSE', 'fist': 'MUTE', 'swipe_right': 'NEXT_TRACK',
        'swipe_left': 'PREVIOUS_TRACK', 'three': 'RESET_ZOOM'})
    direct_tab_mapping: dict[str, int] = field(default_factory=lambda: {'four': 1, 'three': 2})

    def validate(self) -> None:
        defaults = asdict(Config())
        for name, value in asdict(self).items():
            expected = type(defaults[name])
            if expected in (int, bool, str, list, dict) and type(value) is not expected:
                raise ValueError(f'{name} must be {expected.__name__}')
            if expected is float and (type(value) not in (float, int)):
                raise ValueError(f'{name} must be numeric')
        for name, value in asdict(self).items():
            if isinstance(value, (int, float)) and not isinstance(value, bool):
                if not math.isfinite(value) or value < 0:
                    raise ValueError(f'{name} must be finite and nonnegative')
        if self.dominant_hand not in ('right', 'left', 'auto'):
            raise ValueError('dominant_hand must be right, left or auto')
        if not 0 < self.pinch_threshold < self.pinch_release:
            raise ValueError('pinch_release must exceed pinch_threshold > 0')
        if not 0 < self.click_hold_ms < self.drag_hold_ms:
            raise ValueError('drag_hold_ms must exceed click_hold_ms > 0')
        if len(self.interaction_region) != 4:
            raise ValueError('interaction_region must contain four coordinates')
        x1, y1, x2, y2 = self.interaction_region
        if not (0 <= x1 < x2 <= 1 and 0 <= y1 < y2 <= 1):
            raise ValueError('invalid interaction_region')
        for name in ('cursor_sensitivity', 'cursor_smoothing', 'zoom_threshold',
                     'volume_angle_step', 'camera_timeout', 'scroll_max_rate', 'hand_size'):
            if getattr(self, name) <= 0:
                raise ValueError(f'{name} must be positive')
        if self.camera_width < 160 or self.camera_height < 120:
            raise ValueError('camera resolution is too small')
        if not 0 < self.confidence_threshold <= 1:
            raise ValueError('confidence_threshold must be in (0, 1]')
        if self.reconnect_attempts > 10 or self.camera_width > 3840 or self.camera_height > 2160:
            raise ValueError('Camera retry/resolution limit exceeded')
        if not 0 < self.finger_angle < 180 or not 0 <= self.tab_zone_y < 1:
            raise ValueError('Invalid finger_angle or tab_zone_y')
        if self.tab_zone_y >= y1:
            raise ValueError('tab_zone_y must be above the cursor interaction region')
        allowed = {'PLAY_PAUSE', 'MUTE', 'NEXT_TRACK', 'PREVIOUS_TRACK', 'RESET_ZOOM'}
        if not set(self.media_mapping.values()) <= allowed:
            raise ValueError('unsupported media action')
        if any(type(v) is not int or not 1 <= v <= 9 for v in self.direct_tab_mapping.values()):
            raise ValueError('tab numbers must be integers 1..9')


def load_config(path: Path, calibration: Path | None = None) -> Config:
    data = json.loads(path.read_text()) if path.exists() else {}
    if calibration and calibration.exists():
        data.update(json.loads(calibration.read_text()))
    config = Config(**data)
    config.validate()
    return config


def save_config(config: Config, path: Path) -> None:
    config.validate()
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(asdict(config), indent=2) + '\n')
    temporary.replace(path)
