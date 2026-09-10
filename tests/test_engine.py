from dataclasses import replace
import numpy as np
import pytest
from gesture_control.config import Config
from gesture_control.controllers.events import Event, EventSink
from gesture_control.gestures.gesture_engine import GestureEngine
from gesture_control.gestures.gesture_state import TemporalGate, State
from gesture_control.vision.gesture_features import Hand

POSES = {'point':(False,True,False,False,False), 'scroll':(False,True,True,False,False),
         'open':(True,)*5, 'fist':(False,)*5, 'neutral':(True,False,True,False,True),
         'three':(False,True,True,True,False)}


def hand(pose='point', x=.5,y=.5,pinch=1.,middle=1.,label='right'):
    p = np.tile([x,y,0.],(21,1))
    return Hand(label,.99,p,p.copy(),POSES[pose],.2,np.array([x,y]),pinch,middle,.5,
                np.array([0,0,1]),0,np.zeros(2),np.zeros(2),'stationary')


class Driver:
    def __init__(self, config=None):
        self.sink = EventSink(dry_run=True)
        self.sink.enable()
        self.engine = GestureEngine(config or Config(),self.sink)
        self.now = 0.
        self.feed([hand('neutral')],.3)

    def feed(self,hands,duration=.1):
        for _ in range(round(duration/.025)):
            self.now += .025
            self.engine.update(hands,self.now)

    def names(self): return [e.name for e in self.sink.history]


def test_temporal_gate_and_cooldown():
    g = TemporalGate()
    assert not g.update('pinch',0,.1,.3)
    assert g.state == State.POTENTIAL_GESTURE
    assert not g.update('pinch',.05,.1,.3)
    assert g.update('pinch',.11,.1,.3)
    assert not g.update('pinch',.2,.1,.3)
    assert g.state == State.COOLDOWN
    assert not g.update('pinch',.5,.1,.3)
    g.update(None,.6,.1)
    assert not g.update('pinch',.7,.1)
    assert g.update('pinch',.81,.1)


def test_one_click_on_release_no_drag():
    d = Driver()
    d.feed([hand(pinch=.1)],.25)
    assert 'LEFT_CLICK' not in d.names()
    d.feed([hand(pinch=.6)],.15)
    assert d.names().count('LEFT_CLICK') == 1
    assert 'DRAG_START' not in d.names()
    d.feed([hand()],1.)
    assert d.names().count('LEFT_CLICK') == 1


def test_short_pinch_and_hysteresis():
    d = Driver()
    d.feed([hand(pinch=.1)],.05)
    d.feed([hand()],.3)
    assert 'LEFT_CLICK' not in d.names()
    d = Driver()
    d.feed([hand(pinch=.1)],.2)
    d.feed([hand(pinch=.35)],.2)
    assert 'LEFT_CLICK' not in d.names()
    d.feed([hand(pinch=.6)],.15)
    assert d.names().count('LEFT_CLICK') == 1


def test_drag_and_release():
    d = Driver()
    d.feed([hand(pinch=.1)],.7)
    assert d.sink.dragging
    d.feed([hand(x=.7,pinch=.1)],.2)
    d.feed([hand(pinch=.6)],.15)
    assert not d.sink.dragging
    assert d.names().count('DRAG_START') == d.names().count('DRAG_END') == 1
    assert 'LEFT_CLICK' not in d.names()


def test_tracking_loss_cancel_no_release_click():
    d = Driver()
    d.feed([hand(pinch=.1)],.7)
    d.feed([],.3)
    assert not d.sink.dragging and d.engine.mode is None
    d.feed([hand(pinch=.1)],1.)
    assert d.names().count('DRAG_START') == 1
    assert 'LEFT_CLICK' not in d.names()


def test_disable_blocks_and_resume_requires_unpinched():
    d = Driver()
    d.feed([hand(pinch=.1)],.7)
    d.sink.disable()
    count = len(d.names())
    d.feed([hand(pinch=.1)],.3)
    assert len(d.names()) == count
    d.sink.enable()
    d.feed([hand(pinch=.1)],1.)
    assert len(d.names()) == count
    d.feed([hand('neutral')],.4)
    d.feed([hand(pinch=.1)],.25)
    d.feed([hand()],.15)
    assert d.names().count('LEFT_CLICK') == 1


def test_right_click_distinct():
    d = Driver()
    d.feed([hand(middle=.1)],.3)
    d.feed([hand()],.15)
    assert 'RIGHT_CLICK' in d.names() and 'LEFT_CLICK' not in d.names()


def test_double_click_hold_once():
    d = Driver()
    d.feed([hand('three')],2.)
    assert d.names().count('DOUBLE_CLICK') == 1


@pytest.mark.parametrize('sign',[1,-1])
def test_tab_release_once(sign):
    d = Driver()
    d.feed([hand(y=.15,pinch=.1)],.25)
    d.feed([hand(x=.5+sign*.25,y=.15,pinch=.1)],.3)
    d.feed([hand(x=.5+sign*.25,y=.15)],.15)
    assert d.names().count('TAB_NEXT' if sign>0 else 'TAB_PREVIOUS') == 1
    assert 'DRAG_START' not in d.names()


def test_scroll_owns_pointer_and_stationary_stops():
    d = Driver()
    d.feed([hand('scroll')],.3)
    for y in np.linspace(.5,.25,20): d.feed([hand('scroll',y=y)],.025)
    assert 'SCROLL' in d.names() and 'MOUSE_MOVE' not in d.names()
    d.feed([hand('scroll',y=.25)],1.)
    count = d.names().count('SCROLL')
    d.feed([hand('scroll',y=.25)],1.)
    assert d.names().count('SCROLL') == count


def test_two_hand_zoom():
    d = Driver()
    d.feed([hand(x=.4,pinch=.1),hand(x=.6,pinch=.1,label='left')],.3)
    d.feed([hand(x=.2,pinch=.1),hand(x=.8,pinch=.1,label='left')],.3)
    assert d.names().count('ZOOM_IN') == 1
    assert 'LEFT_CLICK' not in d.names() and 'DRAG_START' not in d.names()


def test_two_open_palms_preempt_media():
    d = Driver()
    d.feed([hand('open'),hand('open',label='left')],1.2)
    assert not d.sink.enabled
    assert not d.names()


def test_media_hold_once_and_circle_no_pointer():
    d = Driver()
    d.feed([hand('open',label='left')],2.)
    assert d.names().count('PLAY_PAUSE') == 1
    d = Driver()
    for angle in np.linspace(0,4*np.pi,140):
        d.feed([hand(x=.5+.1*np.cos(angle),y=.5+.1*np.sin(angle),label='left')],.025)
    assert 'VOLUME_UP' in d.names() and 'MOUSE_MOVE' not in d.names()


def test_dry_run_never_calls_backend():
    class Forbidden:
        def execute(self,event): raise AssertionError('OS input called')
        def release_all(self): raise AssertionError('OS release called')
    sink = EventSink(Forbidden(),dry_run=True)
    sink.enable()
    for event in ('LEFT_CLICK','DRAG_START','SCROLL','ZOOM_IN','TAB_NEXT','VOLUME_UP'):
        sink.emit(Event(event,(1,) if event=='SCROLL' else ()))
    sink.disable()
    assert not sink.dragging


def test_pointer_clamps():
    d = Driver()
    d.feed([hand(x=1.5,y=-.5)],.4)
    moves = [e for e in d.sink.history if e.name=='MOUSE_MOVE']
    assert moves and all(0<=e.args[0]<1920 and 0<=e.args[1]<1080 for e in moves)


def test_tab_tracking_loss_does_not_commit():
    d = Driver()
    d.feed([hand(y=.15,pinch=.1)],.25)
    d.feed([hand(x=.8,y=.15,pinch=.1)],.2)
    d.feed([],.3)
    d.feed([hand(x=.8,y=.15)],.2)
    assert 'TAB_NEXT' not in d.names()


def test_long_gap_with_returning_hand_cancels_drag():
    d = Driver()
    d.feed([hand(pinch=.1)],.7)
    d.now += 1.
    d.feed([hand(pinch=.1)],.025)
    assert not d.sink.dragging


def test_media_swipe_no_play_pause():
    d = Driver()
    d.feed([hand('open',label='left')],.3)
    d.feed([hand('open',x=.8,label='left')],1.5)
    assert d.names() == ['NEXT_TRACK']


def test_optional_actions_disabled_by_default():
    d = Driver()
    d.feed([hand('scroll',label='left')],1.5)
    assert not d.names()


def test_optional_window_action():
    d = Driver(Config(window_gestures=True))
    d.feed([hand('scroll',label='left')],1.5)
    assert d.names() == ['TASK_VIEW']


def test_direct_tabs_override_media_hold():
    d = Driver(Config(direct_tabs=True))
    d.feed([hand('three',label='left')],1.5)
    assert d.names() == ['DIRECT_TAB']


def test_zoom_release_cannot_turn_remaining_pinch_into_drag():
    d = Driver()
    d.feed([hand(pinch=.1),hand(label='left',pinch=.1)],.3)
    d.feed([hand(pinch=.1),hand(label='left',pinch=.8)],1.5)
    assert 'DRAG_START' not in d.names() and 'LEFT_CLICK' not in d.names()
