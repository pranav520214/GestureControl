import logging
import numpy as np
from .gesture_state import State, TemporalGate
from .circle import CircleDetector
from ..controllers.events import Event
from ..utils.smoothing import AdaptiveSmoother
from ..vision.geometry import distance, swipe


class GestureArbiter:
    """Latched ownership prevents an active gesture from becoming another gesture."""
    PRIORITY = {'STOP': 0, 'PINCH': 1, 'RIGHT': 2, 'DOUBLE': 2, 'ZOOM': 3,
                'SCROLL': 4, 'TAB': 5, 'MEDIA': 6, 'POINT': 7}

    @classmethod
    def choose(cls, candidates):
        return min(candidates, key=lambda item: cls.PRIORITY[item]) if candidates else None


class GestureEngine:
    def __init__(self, config, sink, screen=(1920, 1080)):
        self.c, self.sink, self.screen = config, sink, screen
        self.smoother = AdaptiveSmoother(config.cursor_smoothing)
        self.scroll_smoother = AdaptiveSmoother(config.scroll_smoothing)
        self.circle = CircleDetector(config)
        self.gate, self.stop_gate = TemporalGate(), TemporalGate()
        self.dominant = None if config.dominant_hand == 'auto' else config.dominant_hand
        self.generation = sink.generation
        self.mode = None
        self.owner = None
        self.state = State.IDLE
        self.confidence = 0.0
        self.start = self.last = None
        self.since = self.last_seen = 0.0
        self.release_since = None
        self.cooldown_until = 0.0
        self.armed = False
        self.neutral_since = None
        self.scroll_accum = 0.0
        self.last_step = 0.0
        self.target = None

    def cancel(self, reason='cancelled'):
        if self.mode: logging.getLogger(__name__).debug('cancel %s: %s', self.mode, reason)
        self.sink.release()
        self.mode = self.owner = None
        self.state = State.IDLE
        self.gate.reset()
        self.circle.reset()
        self.smoother.reset()
        self.scroll_smoother.reset()
        self.release_since = None
        self.armed = False
        self.neutral_since = None

    def _emit(self, name, *args):
        self.sink.emit(Event(name, args))

    def _finish(self, now):
        self.sink.release()
        self.mode = self.owner = None
        self.state = State.GESTURE_FINISHED
        self.cooldown_until = now + self.c.gesture_cooldown_ms / 1000
        self.gate.reset()
        self.circle.reset()
        self.release_since = None
        # A residual pinch after zoom must not turn into a new single-hand drag.
        self.armed = False
        self.neutral_since = None

    def _move(self, hand, now):
        x1, y1, x2, y2 = self.c.interaction_region
        position = (hand.index - [x1, y1]) / [x2-x1, y2-y1]
        position = np.clip((position-0.5)*self.c.cursor_sensitivity+0.5, 0, 1)
        position = self.smoother.update(position, now)
        self.target = tuple(np.clip(position * (np.array(self.screen)-1), 0, np.array(self.screen)-1).astype(int))
        self._emit('MOUSE_MOVE', *map(int, self.target))

    def _released(self, condition, now):
        if not condition:
            self.release_since = None
            return False
        if self.release_since is None: self.release_since = now
        return now - self.release_since >= self.c.release_ms / 1000

    def update(self, hands, now):
        # Emergency listener also uses this lock. Generation invalidates stale state on resume.
        with self.sink.lock:
            self._update(hands, now)

    def _update(self, hands, now):
        if self.generation != self.sink.generation:
            self.cancel('enable state changed')
            self.generation = self.sink.generation
        hands = [h for h in hands if h.confidence >= self.c.confidence_threshold]
        if self.stop_gate.update('STOP' if len(hands) == 2 and all(h.pose == 'open' for h in hands) else None,
                                 now, self.c.emergency_hold_ms / 1000):
            self.sink.disable()
            self.cancel('two open palms')
            return
        if not self.sink.enabled: return
        if len(hands) == 2 and all(h.pose == 'open' for h in hands):
            self.cancel('emergency stop candidate')
            return
        if self.dominant is None and hands:
            self.dominant = max(hands, key=lambda h: h.confidence).label
        dominant = next((h for h in hands if h.label == self.dominant), None)
        other = next((h for h in hands if h.label != self.dominant), None)
        owner = next((h for h in hands if h.label == self.owner), None)
        if self.mode and now-self.last_seen > self.c.tracking_loss_ms/1000:
            self.cancel('tracking gap')
            return
        if self.mode and (owner is None or (self.mode == 'ZOOM' and len(hands) != 2)):
            if now-self.last_seen >= self.c.tracking_loss_ms/1000:
                self.cancel('tracking loss')
            return
        if self.mode: self.last_seen = now
        if not hands:
            self.armed = False
            self.neutral_since = None
            self.gate.reset()
            return
        # Require observed unpinched input after startup, disable, or tracking loss.
        if not self.armed:
            if all(h.pinch > self.c.pinch_release for h in hands):
                if self.neutral_since is None: self.neutral_since = now
                self.armed = now-self.neutral_since >= self.c.hold_ms/1000
            else: self.neutral_since = None
            return
        if self.mode:
            self._active(owner, hands, now)
            return
        if now < self.cooldown_until:
            self.state = State.COOLDOWN
            return
        candidates = {}
        if dominant:
            if dominant.pinch < self.c.pinch_threshold:
                candidates['TAB' if dominant.index[1] < self.c.tab_zone_y else 'PINCH'] = dominant
            elif dominant.middle_pinch < self.c.pinch_threshold: candidates['RIGHT'] = dominant
            elif dominant.pose == 'three': candidates['DOUBLE'] = dominant
            elif dominant.pose == 'scroll': candidates['SCROLL'] = dominant
            elif dominant.pose == 'point': candidates['POINT'] = dominant
        # Two pinch hands reserved for zoom only when no drag already owns input.
        if len(hands) == 2 and all(h.pinch < self.c.pinch_threshold for h in hands):
            candidates = {'ZOOM': dominant or hands[0]}
        elif other and other.pose != 'neutral': candidates['MEDIA'] = other
        choice = GestureArbiter.choose(candidates)
        hand = candidates.get(choice)
        name = (choice, hand.label) if hand else None
        hold = self.c.click_hold_ms / 1000 if choice in ('PINCH', 'TAB', 'RIGHT') else self.c.hold_ms/1000
        started = self.gate.update(name, now, hold)
        self.state = self.gate.state
        self.confidence = hand.confidence if hand else 0.0
        if not started: return
        self.mode, self.owner = choice, hand.label
        self.state = State.GESTURE_STARTED
        self.since, self.last_seen = now, now
        self.start = hand.index.copy()
        self.last = hand.index.copy()
        self.scroll_accum = 0.0
        self.scroll_smoother.reset()
        self.last_step = now
        self.release_since = None
        if choice == 'ZOOM': self.last = distance(hands[0].palm, hands[1].palm) / np.mean([h.size for h in hands])
        if choice == 'DOUBLE': self.double_fired = False
        if choice == 'MEDIA':
            self.media_pose = hand.pose
            self.media_fired = False
            self.start = hand.palm.copy()
        if choice == 'PINCH': self.since = self.gate.since

    def _active(self, hand, hands, now):
        self.state = State.GESTURE_ACTIVE
        elapsed = now - self.since
        if self.mode in ('PINCH', 'TAB'):
            if self._released(hand.pinch > self.c.pinch_release, now):
                if self.mode == 'TAB':
                    direction = swipe(self.start, hand.index, self.c.tab_swipe_distance, self.c.swipe_vertical_tolerance)
                    if direction and elapsed <= self.c.swipe_timeout:
                        self._emit('TAB_NEXT' if direction > 0 else 'TAB_PREVIOUS')
                elif not self.sink.dragging:
                    self._emit('LEFT_CLICK')
                self._finish(now)
            elif self.mode == 'PINCH' and self.release_since is None:
                if elapsed >= self.c.drag_hold_ms/1000 and not self.sink.dragging:
                    self._emit('DRAG_START')
                if self.sink.dragging: self._move(hand, now)
        elif self.mode == 'RIGHT':
            if self._released(hand.middle_pinch > self.c.pinch_release, now):
                self._emit('RIGHT_CLICK')
                self._finish(now)
        elif self.mode == 'DOUBLE':
            if self._released(hand.pose != 'three', now): self._finish(now)
            elif elapsed >= self.c.media_hold_ms/1000:
                if not getattr(self, 'double_fired', False) and hand.pose == 'three':
                    self._emit('DOUBLE_CLICK')
                    self.double_fired = True
        elif self.mode == 'POINT':
            if hand.pose != 'point' or hand.pinch < self.c.pinch_threshold or hand.middle_pinch < self.c.pinch_threshold:
                self.mode = self.owner = None
                self.gate.reset()
            else: self._move(hand, now)
        elif self.mode == 'SCROLL':
            if hand.pose != 'scroll' or hand.pinch < self.c.pinch_threshold:
                if self._released(True,now): self._finish(now)
                return
            self.release_since = None
            position = self.scroll_smoother.update(hand.index,now)
            dy = float(self.last[1] - position[1])
            if abs(dy) >= self.c.scroll_deadzone:
                self.scroll_accum += dy*self.c.scroll_speed
                self.last = position
            if abs(self.scroll_accum) >= 1 and now-self.last_step >= 1/self.c.scroll_max_rate:
                step = 1 if self.scroll_accum > 0 else -1
                self._emit('SCROLL', step)
                self.scroll_accum = float(np.clip(self.scroll_accum-step, -3, 3))
                self.last_step = now
        elif self.mode == 'ZOOM':
            if self._released(any(h.pinch > self.c.pinch_release for h in hands), now):
                self._finish(now)
                return
            current = distance(hands[0].palm, hands[1].palm)/np.mean([h.size for h in hands])
            if abs(current-self.last) >= self.c.zoom_threshold and now-self.last_step >= self.c.zoom_step_seconds:
                self._emit('ZOOM_IN' if current > self.last else 'ZOOM_OUT')
                self.last, self.last_step = current, now
        elif self.mode == 'MEDIA': self._media(hand, elapsed, now)

    def _media(self, hand, elapsed, now):
        if hand.pose != self.media_pose:
            if self._released(True,now): self._finish(now)
            return
        self.release_since = None
        if self.media_pose == 'point':
            # Aspect-corrected coordinates avoid fitting an ellipse on a 4:3 preview.
            direction = self.circle.update(hand.metric[8, :2], now)
            if direction: self._emit('VOLUME_UP' if direction > 0 else 'VOLUME_DOWN')
            return
        if self.media_fired: return
        direction = swipe(self.start, hand.palm, self.c.tab_swipe_distance, self.c.swipe_vertical_tolerance)
        action = None
        if self.media_pose == 'open' and direction and elapsed < self.c.swipe_timeout:
            action = self.c.media_mapping.get('swipe_right' if direction > 0 else 'swipe_left')
        elif elapsed >= self.c.media_hold_ms/1000:
            # Stationary holds and swipes are mutually exclusive.
            if distance(self.start, hand.palm) > self.c.media_stationary_distance: return
            if self.c.direct_tabs and self.media_pose in self.c.direct_tab_mapping:
                self._emit('DIRECT_TAB', self.c.direct_tab_mapping[self.media_pose])
                self.media_fired = True
                return
            action = self.c.media_mapping.get(self.media_pose)
            if self.c.window_gestures:
                action = {'scroll': 'TASK_VIEW', 'four': 'DESKTOP'}.get(self.media_pose, action)
        if self.c.window_gestures and self.media_pose == 'scroll' and direction:
            action = 'APP_NEXT' if direction > 0 else 'APP_PREVIOUS'
        if action:
            self._emit(action)
            self.media_fired = True
