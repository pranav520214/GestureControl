from collections import deque
import math
import numpy as np
from ..vision.geometry import angle_delta, distance


class CircleDetector:
    """Fit a center, reject lines/noisy radii, then integrate signed screen angles."""
    def __init__(self, config):
        self.c = config
        self.points = deque(maxlen=64)
        self.last_move = 0.0
        self.last_emit = -math.inf
        self.active = False
        self.accumulated = 0.0
        self.center = None

    def reset(self):
        self.points.clear()
        self.active = False
        self.accumulated = 0.0
        self.center = None

    def update(self, point, now) -> int:
        point = np.asarray(point, dtype=float)
        if self.points and distance(point, self.points[-1]) < 0.003:
            if now - self.last_move > self.c.volume_stop_seconds: self.reset()
            return 0
        self.last_move = now
        self.points.append(point.copy())
        if len(self.points) < 12: return 0
        p = np.array(self.points)
        eigen = np.linalg.eigvalsh(np.cov(p.T))
        if eigen[0] < eigen[1] * 0.12:
            self.active = False
            self.accumulated = 0
            return 0
        solution, *_ = np.linalg.lstsq(np.column_stack((2*p[:, 0], 2*p[:, 1], np.ones(len(p)))),
                                     (p*p).sum(axis=1), rcond=None)
        center = solution[:2]
        radii = np.linalg.norm(p - center, axis=1)
        radius = float(radii.mean())
        angles = np.unwrap(np.arctan2(p[:, 1] - center[1], p[:, 0] - center[0]))
        arc = angles[-1] - angles[0]
        travel = np.abs(np.diff(angles)).sum()
        valid = (radius >= self.c.volume_min_radius and radius < 0.4
                 and radii.std() / radius < self.c.volume_fit_error
                 and abs(arc) > math.radians(self.c.volume_min_arc)
                 and abs(arc) / max(travel, 1e-6) > 0.8)
        if not valid:
            self.active = False
            self.accumulated = 0
            return 0
        self.center = center
        if not self.active:
            self.active = True
            self.accumulated = 0
            return 0
        # Recompute both endpoint angles around the SAME fitted center each frame.
        before = math.atan2(p[-2, 1]-center[1], p[-2, 0]-center[0])
        after = math.atan2(p[-1, 1]-center[1], p[-1, 0]-center[0])
        self.accumulated += angle_delta(before, after)
        step = math.radians(self.c.volume_angle_step)
        if abs(self.accumulated) >= step and now - self.last_emit >= self.c.volume_step_seconds:
            sign = 1 if self.accumulated > 0 else -1
            self.accumulated -= sign * step
            self.last_emit = now
            return sign  # Screen y points down, so positive angles are clockwise.
        return 0
