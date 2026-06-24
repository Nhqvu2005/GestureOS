"""
GestureOS — Configuration constants.
"""
import cv2

# Camera
CAM_ID = 0
CAM_WIDTH = 640
CAM_HEIGHT = 480
CAM_FPS = 30

# MediaPipe
MAX_HANDS = 1
DETECTION_CONFIDENCE = 0.7
TRACKING_CONFIDENCE = 0.5

# Landmark indices (MediaPipe hand convention)
WRIST = 0
THUMB_CMC = 1
THUMB_IP = 3
THUMB_TIP = 4
INDEX_MCP = 5
INDEX_PIP = 6
INDEX_TIP = 8
MIDDLE_MCP = 9
MIDDLE_PIP = 10
MIDDLE_TIP = 12
RING_MCP = 13
RING_PIP = 14
RING_TIP = 16
PINKY_MCP = 17
PINKY_PIP = 18
PINKY_TIP = 20

# Gesture thresholds
# Pinch: distance(tip, tip) / distance(WRIST, MIDDLE_MCP) — ratio, scale-invariant
PINCH_THRESHOLD = 0.20
PINCH_HYSTERESIS = 0.25  # Higher threshold to release pinch (prevents rapid toggling)

SCROLL_THRESHOLD = 30  # pixels movement for one scroll tick

# Cursor smoothing (EMA alpha, 0-1, lower = smoother)
SMOOTHING_ALPHA = 0.3

# Dead zone (ignore cursor movement smaller than this, in normalized coords)
DEAD_ZONE = 0.005

# Cursor speed multiplier
CURSOR_SPEED = 2.0

# Tap gesture thresholds (index finger curl as left click alternative)
# curl_ratio = (tip.y - pip.y) / hand_size; positive = curled
TAP_PRESS_THRESHOLD = 0.12    # curl_ratio to trigger press (finger curled past this)
TAP_RELEASE_THRESHOLD = 0.05  # curl_ratio to trigger release (finger extended below this)
TAP_VELOCITY_THRESHOLD = 0.04 # minimum curl velocity per frame (prevents slow fist)

# Frame skip for FPS optimization (process MediaPipe every Nth frame)
# 1 = every 2nd frame, 2 = every 3rd frame, 0 = no skip (process every frame)
FRAME_SKIP = 1

# Debug display
SHOW_DEBUG = True
DEBUG_WINDOW_NAME = "GestureOS — Debug"
