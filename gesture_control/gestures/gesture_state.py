from enum import Enum, auto
import logging


class State(Enum):
    IDLE = auto()
    POTENTIAL_GESTURE = auto()
    GESTURE_STARTED = auto()
    GESTURE_ACTIVE = auto()
    GESTURE_FINISHED = auto()
    COOLDOWN = auto()


class TemporalGate:
    def __init__(self):
        self.name = None
        self.since = 0.0
        self.state = State.IDLE
        self.until = 0.0

    def update(self, name, now, hold, cooldown=0.0):
        if now < self.until:
            self.state = State.COOLDOWN
            return False
        if name != self.name:
            logging.getLogger(__name__).debug('pose transition %s -> %s', self.name, name)
            self.name, self.since = name, now
            self.state = State.POTENTIAL_GESTURE if name else State.IDLE
            return False
        if name and self.state == State.POTENTIAL_GESTURE and now - self.since >= hold:
            self.state = State.GESTURE_STARTED
            self.until = now + cooldown
            return True
        if self.state == State.GESTURE_STARTED:
            self.state = State.GESTURE_ACTIVE
        return False

    def reset(self):
        self.__init__()
