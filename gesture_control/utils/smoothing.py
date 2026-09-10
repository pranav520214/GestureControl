import numpy as np


class AdaptiveSmoother:
    def __init__(self, seconds: float):
        self.seconds = seconds
        self.value = None
        self.time = None

    def reset(self):
        self.value = self.time = None

    def update(self, value, now):
        value = np.asarray(value, dtype=float)
        if self.value is None:
            self.value, self.time = value.copy(), now
        dt = max(now - self.time, 0.001)
        speed = np.linalg.norm(value - self.value) / dt
        tau = self.seconds / (1 + 3 * speed)
        self.value += (1 - np.exp(-dt / tau)) * (value - self.value)
        self.time = now
        return self.value.copy()
