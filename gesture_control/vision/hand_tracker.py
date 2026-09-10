import cv2
import mediapipe as mp
from mediapipe.tasks import python
from mediapipe.tasks.python import vision
from .gesture_features import FeatureExtractor


class HandTracker:
    def __init__(self, config, model_path):
        if not model_path.is_file():
            raise FileNotFoundError('Missing hand model. Run: python scripts/download_model.py')
        options = vision.HandLandmarkerOptions(
            base_options=python.BaseOptions(model_asset_path=str(model_path)),
            running_mode=vision.RunningMode.VIDEO, num_hands=2,
            min_hand_detection_confidence=config.confidence_threshold,
            min_hand_presence_confidence=config.confidence_threshold,
            min_tracking_confidence=config.confidence_threshold)
        self.tracker = vision.HandLandmarker.create_from_options(options)
        self.features = FeatureExtractor(config)
        self.timestamp = -1

    def detect(self, frame, now):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        self.timestamp = max(self.timestamp + 1, int(now * 1000))
        result = self.tracker.detect_for_video(mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb), self.timestamp)
        hands = []
        for points, categories in zip(result.hand_landmarks, result.handedness):
            category = categories[0]
            hands.append(self.features.extract([[p.x, p.y, p.z] for p in points],
                         category.category_name, category.score, frame.shape[1] / frame.shape[0], now))
        return hands

    def close(self):
        self.tracker.close()
