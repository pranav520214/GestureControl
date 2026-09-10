import math
import numpy as np


def distance(a, b) -> float:
    return float(np.linalg.norm(np.asarray(a) - np.asarray(b)))


def normalized_distance(a, b, hand_size: float) -> float:
    return distance(a, b) / max(hand_size, 1e-6)


def joint_angle(a, b, c) -> float:
    u, v = np.asarray(a) - b, np.asarray(c) - b
    cosine = np.dot(u, v) / max(np.linalg.norm(u) * np.linalg.norm(v), 1e-9)
    return math.degrees(math.acos(float(np.clip(cosine, -1, 1))))


def angle_delta(previous: float, current: float) -> float:
    return (current - previous + math.pi) % (2 * math.pi) - math.pi


def swipe(start, end, minimum: float, vertical: float) -> int:
    dx, dy = np.asarray(end)[:2] - np.asarray(start)[:2]
    return (1 if dx > 0 else -1) if abs(dx) >= minimum and abs(dy) <= vertical else 0
