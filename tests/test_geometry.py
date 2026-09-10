import math
import numpy as np
import pytest
from gesture_control.config import Config
from gesture_control.vision.geometry import distance, normalized_distance, angle_delta, swipe
from gesture_control.vision.gesture_features import finger_states, FeatureExtractor
from gesture_control.gestures.circle import CircleDetector


def landmarks():
    p = np.zeros((21,3))
    p[0] = [.5,.9,0]
    for ids, x in zip(((1,2,3,4),(5,6,7,8),(9,10,11,12),(13,14,15,16),(17,18,19,20)),(.2,.35,.5,.65,.8)):
        for i,y in zip(ids,(.65,.45,.3,.15)): p[i] = [x,y,0]
    return p


def test_euclidean_and_normalized():
    assert distance([0,0],[3,4]) == 5
    assert normalized_distance([0,0],[3,4],2) == 2.5
    assert normalized_distance([0,0],[6,8],4) == 2.5


def test_finger_states_rotation_invariant():
    p = landmarks()
    assert all(finger_states(p))
    rotation = np.array([[0,-1,0],[1,0,0],[0,0,1]])
    assert all(finger_states(p@rotation))
    p[8] = [.35,.75,0]
    assert not finger_states(p)[1]


def test_pinch_features_and_scale():
    p = landmarks()
    p[4] = p[8]+[.01,0,0]
    extractor = FeatureExtractor(Config())
    a = extractor.extract(p,'Right',.95,4/3,1.)
    b = extractor.extract(p*.5,'Right',.95,4/3,1.1)
    assert a.pinch < Config().pinch_threshold
    assert a.pinch == pytest.approx(b.pinch)
    assert np.isfinite(a.orientation).all()


def test_swipes():
    assert swipe([.2,.4],[.6,.41],.18,.12) == 1
    assert swipe([.6,.4],[.2,.41],.18,.12) == -1
    assert swipe([.2,.4],[.6,.7],.18,.12) == 0
    assert swipe([.2,.4],[.21,.41],.18,.12) == 0


def test_angle_wrap():
    assert angle_delta(math.radians(179), math.radians(-179)) == pytest.approx(math.radians(2))
    assert angle_delta(math.radians(-179), math.radians(179)) == pytest.approx(math.radians(-2))


@pytest.mark.parametrize('sign',[1,-1])
def test_circle_direction(sign):
    detector = CircleDetector(Config())
    events = [detector.update([.5+.1*math.cos(sign*t),.5+.1*math.sin(sign*t)],i/30)
              for i,t in enumerate(np.linspace(0,4*math.pi,120))]
    assert sum(events)*sign >= 5
    assert all(e in (0,sign) for e in events)
    detector.update(detector.points[-1],10.)
    assert not detector.active


def test_linear_small_and_stationary_rejected():
    for points in ([([.1+i*.005,.4]) for i in range(100)],
                   [[.5+.005*math.cos(i),.5+.005*math.sin(i)] for i in range(100)],
                   [[.5,.5]]*100):
        detector = CircleDetector(Config())
        assert not any(detector.update(p,i/30) for i,p in enumerate(points))
