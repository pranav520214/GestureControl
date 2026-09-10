import numpy as np
from collections import deque
import json


class Calibration:
    """Guided local calibration. No frames are saved; only bounded numeric samples."""
    STAGES = ['open', 'pinch', 'top_left', 'bottom_right', 'tune']

    def __init__(self, config, path):
        self.c, self.path = config, path
        self.stage = 0
        self.samples = deque(maxlen=24)
        self.done = False
        self.error = ''

    def update(self, hands, key):
        hand = max(hands, key=lambda h: h.confidence) if hands else None
        stage = self.STAGES[self.stage]
        if hand and hand.confidence >= self.c.confidence_threshold:
            if not self.samples or self.samples[-1][0] == hand.label:
                self.samples.append((hand.label, hand.size, hand.pinch, hand.index.copy()))
            else: self.samples.clear()
        else: self.samples.clear()
        if hand and key == ord(' ') and len(self.samples) >= 12:
            size = float(np.median([s[1] for s in self.samples]))
            pinch = float(np.median([s[2] for s in self.samples]))
            index = np.median([s[3] for s in self.samples],axis=0)
            old_stage = self.stage
            if stage == 'open' and hand.pose == 'open':
                self.c.dominant_hand = hand.label
                self.c.hand_size = size
                self.stage += 1
            elif stage == 'pinch':
                if pinch > 0.65:
                    self.error = 'Bring thumb and index together, then Space.'
                else:
                    self.c.pinch_threshold = float(np.clip(pinch*1.3, .16, .42))
                    self.c.pinch_release = self.c.pinch_threshold + .14
                    self.stage += 1
            elif stage == 'top_left':
                self.corner = np.clip(index, .02, .95)
                self.corner[1] = max(self.corner[1], self.c.tab_zone_y+.02)
                self.stage += 1
            elif stage == 'bottom_right':
                if np.any(index-self.corner < .25):
                    self.error = 'Region too small: move down and right.'
                else:
                    self.c.interaction_region = [*map(float,self.corner), *map(float,np.clip(index,.02,.98))]
                    self.stage += 1
            if self.stage != old_stage:
                self.samples.clear()
                self.error = ''
        if stage == 'tune':
            if key == ord('+') or key == ord('='): self.c.cursor_sensitivity = min(2., self.c.cursor_sensitivity+.1)
            if key == ord('-'): self.c.cursor_sensitivity = max(.5, self.c.cursor_sensitivity-.1)
            if key == ord(']'): self.c.cursor_smoothing = min(.4, self.c.cursor_smoothing+.02)
            if key == ord('['): self.c.cursor_smoothing = max(.02, self.c.cursor_smoothing-.02)
            if key == 13:
                self.c.validate()
                fields = ('dominant_hand','hand_size','pinch_threshold','pinch_release',
                          'interaction_region','cursor_sensitivity','cursor_smoothing')
                temporary = self.path.with_suffix('.tmp')
                temporary.write_text(json.dumps({k:getattr(self.c,k) for k in fields},indent=2)+'\n')
                temporary.replace(self.path)
                self.done = True

    def message(self):
        prompts = ['Show dominant OPEN palm. Space captures size and hand.',
                   'Touch thumb to index. Space captures pinch threshold.',
                   'Point at comfortable TOP LEFT reach. Press Space.',
                   'Point at comfortable BOTTOM RIGHT reach. Press Space.',
                   'Tune +/- sensitivity, [ ] smoothing. Enter saves.']
        return ['CALIBRATION - OS control disabled', prompts[self.stage],
                f'Sensitivity {self.c.cursor_sensitivity:.1f} smoothing {self.c.cursor_smoothing:.2f}s | samples {len(self.samples)}/24', self.error]
