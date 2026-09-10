from dataclasses import dataclass
import math
import numpy as np
from .geometry import distance, joint_angle, normalized_distance


@dataclass
class Hand:
    label: str
    confidence: float
    points: np.ndarray
    metric: np.ndarray
    extended: tuple[bool, ...]
    size: float
    palm: np.ndarray
    pinch: float
    middle_pinch: float
    openness: float
    orientation: np.ndarray
    rotation: float
    movement: np.ndarray
    velocity: np.ndarray
    direction: str

    @property
    def index(self):
        return self.points[8, :2]

    @property
    def pose(self) -> str:
        thumb, index, middle, ring, pinky = self.extended
        if all(self.extended): return 'open'
        if not any(self.extended): return 'fist'
        if index and not any((middle, ring, pinky)): return 'point'
        if index and middle and not ring and not pinky: return 'scroll'
        if index and middle and ring and not pinky: return 'three'
        if index and middle and ring and pinky and not thumb: return 'four'
        return 'neutral'


def finger_states(p: np.ndarray, angle: float = 155) -> tuple[bool, ...]:
    result = []
    for base, joint, tip in ((1, 3, 4), (5, 6, 8), (9, 10, 12), (13, 14, 16), (17, 18, 20)):
        straight = joint_angle(p[base], p[joint], p[tip]) > angle
        outward = distance(p[tip], p[0]) > distance(p[joint], p[0]) * 1.08
        result.append(bool(straight and outward))
    return tuple(result)


class FeatureExtractor:
    def __init__(self, config):
        self.config = config
        self.previous = {}

    def extract(self, landmarks, label: str, confidence: float, aspect: float, now: float) -> Hand:
        p = np.asarray(landmarks, dtype=float)
        # MediaPipe z has x scale; correct y for nonsquare images before geometry.
        metric = p * np.array([1, 1 / aspect, 1])
        size = max(distance(metric[0], metric[9]), distance(metric[5], metric[17]), 1e-6)
        palm = p[[0, 5, 9, 13, 17], :2].mean(axis=0)
        old_time, old_palm = self.previous.get(label, (now, palm))
        dt = now - old_time
        movement = palm - old_palm if 0 < dt < 0.3 else np.zeros(2)
        velocity = movement / max(dt, 1e-6)
        self.previous[label] = (now, palm)
        normal = np.cross(metric[5] - metric[0], metric[17] - metric[0])
        normal /= max(np.linalg.norm(normal), 1e-9)
        extended = finger_states(metric, self.config.finger_angle)
        axis = int(np.argmax(np.abs(velocity)))
        direction = ('right' if velocity[0] > 0 else 'left') if axis == 0 else ('down' if velocity[1] > 0 else 'up')
        if np.linalg.norm(velocity) < 0.03: direction = 'stationary'
        return Hand(label.lower(), confidence, p, metric, extended, size, palm,
                    normalized_distance(metric[4], metric[8], size),
                    normalized_distance(metric[4], metric[12], size), sum(extended) / 5,
                    normal, math.atan2(metric[9, 1] - metric[0, 1], metric[9, 0] - metric[0, 0]),
                    movement, velocity, direction)
