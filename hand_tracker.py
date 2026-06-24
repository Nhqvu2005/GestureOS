"""
GestureOS — MediaPipe hand tracking wrapper (new task API).
"""
import cv2
import mediapipe as mp
from mediapipe.tasks.python import vision
from mediapipe.tasks.python.core.base_options import BaseOptions
from mediapipe.tasks.python.vision.core.image import Image, ImageFormat
from mediapipe.tasks.python.vision.core.vision_task_running_mode import VisionTaskRunningMode

import config
import os


# Path to the downloaded model
MODEL_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "hand_landmarker.task")

# Pre-build all hand connections list for drawing
_HAND_CONNS = (
    vision.HandLandmarksConnections.HAND_PALM_CONNECTIONS
    + vision.HandLandmarksConnections.HAND_THUMB_CONNECTIONS
    + vision.HandLandmarksConnections.HAND_INDEX_FINGER_CONNECTIONS
    + vision.HandLandmarksConnections.HAND_MIDDLE_FINGER_CONNECTIONS
    + vision.HandLandmarksConnections.HAND_RING_FINGER_CONNECTIONS
    + vision.HandLandmarksConnections.HAND_PINKY_FINGER_CONNECTIONS
)
# Convert Connection objects to (start, end) tuples for OpenCV drawing
HAND_CONNECTIONS = [(c.start, c.end) for c in _HAND_CONNS]


class HandTracker:
    """Wraps MediaPipe HandLandmarker for landmark detection."""

    def __init__(self):
        if not os.path.exists(MODEL_PATH):
            raise RuntimeError(
                f"Hand landmarker model not found at {MODEL_PATH}. "
                "Download it from: "
                "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
            )

        options = vision.HandLandmarkerOptions(
            base_options=BaseOptions(model_asset_path=MODEL_PATH),
            running_mode=VisionTaskRunningMode.IMAGE,
            num_hands=config.MAX_HANDS,
            min_hand_detection_confidence=config.DETECTION_CONFIDENCE,
            min_hand_presence_confidence=config.DETECTION_CONFIDENCE,
            min_tracking_confidence=config.TRACKING_CONFIDENCE,
        )
        self.detector = vision.HandLandmarker.create_from_options(options)

    def process(self, frame):
        """Detect hands and return (annotated_frame, hands_data).

        hands_data is a list of hand dicts, each containing:
          - 'landmarks': list of 21 (x, y, z) normalized tuples
          - 'handedness': 'Left' or 'Right'
          - 'score': confidence score

        Returns (frame, None) if no hands detected.
        """
        # Convert BGR → RGB for MediaPipe
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        mp_image = Image(image_format=ImageFormat.SRGB, data=rgb)

        result = self.detector.detect(mp_image)

        if result.hand_landmarks and config.SHOW_DEBUG:
            annotated = frame.copy()
        else:
            annotated = frame

        hands_data = None

        if result.hand_landmarks:
            hands_data = []
            for i, hand_landmarks in enumerate(result.hand_landmarks):
                # Convert NormalizedLandmark objects to tuples
                landmarks = []
                for lm in hand_landmarks:
                    landmarks.append((lm.x, lm.y, lm.z if lm.z else 0.0))

                # Get handedness
                handedness = "Unknown"
                score = 0.0
                if result.handedness and i < len(result.handedness):
                    cat = result.handedness[i][0]
                    handedness = cat.category_name
                    score = cat.score

                hands_data.append({
                    'landmarks': landmarks,
                    'handedness': handedness,
                    'score': score,
                })

                # Draw landmarks manually using OpenCV
                self._draw_landmarks(annotated, hand_landmarks, result.handedness[i][0].category_name)

        return annotated, hands_data

    def _draw_landmarks(self, image, landmark_list, handedness):
        """Draw hand landmarks and connections on the image."""
        h, w, _ = image.shape

        # Draw connections
        for start_idx, end_idx in HAND_CONNECTIONS:
            if start_idx < len(landmark_list) and end_idx < len(landmark_list):
                x1 = int(landmark_list[start_idx].x * w)
                y1 = int(landmark_list[start_idx].y * h)
                x2 = int(landmark_list[end_idx].x * w)
                y2 = int(landmark_list[end_idx].y * h)
                cv2.line(image, (x1, y1), (x2, y2), (255, 255, 255), 1)

        # Draw landmarks as circles
        radius = max(1, int(min(h, w) * 0.004))
        for i, lm in enumerate(landmark_list):
            cx = int(lm.x * w)
            cy = int(lm.y * h)
            # Only draw fingertips and key joints
            if i in (4, 8, 12, 16, 20):  # Fingertips
                color = (0, 255, 255)  # Yellow
                cv2.circle(image, (cx, cy), radius + 1, color, -1)
            elif i in (0, 5, 9, 13, 17):  # Wrist + MCP joints
                color = (200, 100, 255)  # Light purple
                cv2.circle(image, (cx, cy), radius, color, -1)

        # Draw handedness label
        if landmark_list:
            cx = int(landmark_list[0].x * w) - 30
            cy = int(landmark_list[0].y * h) - 15
            cv2.putText(image, handedness, (cx, cy),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 255), 1)

    def release(self):
        self.detector.close()
