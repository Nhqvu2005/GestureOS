"""
GestureOS — Recognizes hand gestures from MediaPipe landmarks.
"""
from enum import Enum, auto
import config


class GestureState(Enum):
    MOVE = auto()          # Single index finger → move cursor
    LEFT_CLICK_DOWN = auto()  # Pinch thumb + index → click down
    LEFT_CLICK_UP = auto()    # Release pinch → click up
    RIGHT_CLICK = auto()   # Pinch thumb + middle → right click
    SCROLL_UP = auto()     # Two fingers up, hand moves up
    SCROLL_DOWN = auto()   # Two fingers up, hand moves down
    IDLE = auto()          # Fist / no gesture
    ACTIVATE = auto()      # Open palm (5 fingers up) → activate


class GestureRecognizer:
    """Classifies landmark positions into gesture states."""

    # Finger tip → pip pair mapping for finger-up detection
    FINGER_TIP_PIP = [
        (config.THUMB_TIP, config.THUMB_CMC),  # thumb uses CMC (sideways)
        (config.INDEX_TIP, config.INDEX_PIP),
        (config.MIDDLE_TIP, config.MIDDLE_PIP),
        (config.RING_TIP, config.RING_PIP),
        (config.PINKY_TIP, config.PINKY_PIP),
    ]

    def __init__(self):
        self._prev_gesture = GestureState.IDLE
        self._prev_y = None  # For scroll delta tracking
        self._pinch_active = False  # Track pinch hold state

        # Tap (index curl) state
        self._tap_active = False
        self._prev_curl_ratio = None

    def _fingers_up(self, landmarks):
        """Return list of 5 booleans indicating each finger is up."""
        up = [False] * 5

        # Index, middle, ring, pinky (compare y: tip y < pip y → up)
        for i, (tip, pip) in enumerate(self.FINGER_TIP_PIP[1:], start=1):
            if landmarks[tip][1] < landmarks[pip][1]:
                up[i] = True

        # Thumb: compare distance from index MCP (landmark 5)
        ix_mcp = landmarks[5]
        tip_dx = landmarks[config.THUMB_TIP][0] - ix_mcp[0]
        tip_dy = landmarks[config.THUMB_TIP][1] - ix_mcp[1]
        ip_dx = landmarks[config.THUMB_IP][0] - ix_mcp[0]
        ip_dy = landmarks[config.THUMB_IP][1] - ix_mcp[1]
        tip_dist = (tip_dx * tip_dx + tip_dy * tip_dy) ** 0.5
        ip_dist = (ip_dx * ip_dx + ip_dy * ip_dy) ** 0.5
        up[0] = tip_dist > ip_dist

        return up

    def _pinch_distance(self, landmarks, tip_a, tip_b):
        """Euclidean distance (normalized) between two landmarks."""
        dx = landmarks[tip_a][0] - landmarks[tip_b][0]
        dy = landmarks[tip_a][1] - landmarks[tip_b][1]
        return (dx * dx + dy * dy) ** 0.5

    def _hand_size(self, landmarks):
        """Compute hand size as distance between wrist and middle MCP for scale normalization."""
        dx = landmarks[config.WRIST][0] - landmarks[config.MIDDLE_MCP][0]
        dy = landmarks[config.WRIST][1] - landmarks[config.MIDDLE_MCP][1]
        return (dx * dx + dy * dy) ** 0.5

    def _relative_pinch(self, landmarks, tip_a, tip_b):
        """Pinch distance relative to hand size (scale-invariant)."""
        dist = self._pinch_distance(landmarks, tip_a, tip_b)
        size = self._hand_size(landmarks)
        if size < 0.01:
            return 1.0  # No valid hand
        return dist / size

    def recognize(self, landmarks, frame_width, frame_height):
        """Classify gesture from landmarks.

        Returns GestureState.
        """
        if landmarks is None:
            self._pinch_active = False
            self._tap_active = False
            self._prev_curl_ratio = None
            return GestureState.IDLE

        fingers = self._fingers_up(landmarks)
        num_up = sum(fingers)

        # Scale-invariant pinch distances
        thumb_index_dist = self._relative_pinch(
            landmarks, config.THUMB_TIP, config.INDEX_TIP
        )
        thumb_middle_dist = self._relative_pinch(
            landmarks, config.THUMB_TIP, config.MIDDLE_TIP
        )

        # Determine pinch thresholds with hysteresis
        if self._pinch_active:
            pinch_threshold = config.PINCH_HYSTERESIS
        else:
            pinch_threshold = config.PINCH_THRESHOLD

        # Check pinches first (highest priority)
        if num_up <= 2 and thumb_middle_dist < pinch_threshold:
            self._pinch_active = False
            return GestureState.RIGHT_CLICK

        if num_up <= 2 and thumb_index_dist < pinch_threshold:
            self._pinch_active = True
            if self._prev_gesture in (GestureState.LEFT_CLICK_DOWN, GestureState.LEFT_CLICK_UP):
                return GestureState.LEFT_CLICK_UP
            return GestureState.LEFT_CLICK_DOWN

        self._pinch_active = False

        # --- LEFT CLICK via TAP (index finger curl) ---
        hand_sz = self._hand_size(landmarks)
        curl_ratio = (landmarks[config.INDEX_TIP][1] - landmarks[config.INDEX_PIP][1]) / max(hand_sz, 0.01)

        if self._tap_active:
            # Holding a tap press — check for release (finger extended back)
            if curl_ratio < config.TAP_RELEASE_THRESHOLD:
                self._tap_active = False
                self._prev_curl_ratio = curl_ratio
                return GestureState.LEFT_CLICK_UP
            # Still curled — hold the click
            self._prev_curl_ratio = curl_ratio
            return GestureState.LEFT_CLICK_DOWN

        # Detect tap press: index curls quickly past threshold
        if self._prev_curl_ratio is not None:
            curl_vel = curl_ratio - self._prev_curl_ratio
            if curl_ratio > config.TAP_PRESS_THRESHOLD and curl_vel > config.TAP_VELOCITY_THRESHOLD:
                self._tap_active = True
                self._prev_curl_ratio = curl_ratio
                return GestureState.LEFT_CLICK_DOWN

        self._prev_curl_ratio = curl_ratio

        # Scroll: index + middle up, ring + pinky down
        if fingers[1] and fingers[2] and not fingers[3] and not fingers[4]:
            index_y = landmarks[config.INDEX_TIP][1]
            if self._prev_y is not None:
                dy = index_y - self._prev_y
                if abs(dy) * frame_height > config.SCROLL_THRESHOLD:
                    self._prev_y = index_y
                    if dy < 0:
                        return GestureState.SCROLL_UP
                    else:
                        return GestureState.SCROLL_DOWN
            self._prev_y = index_y
            return self._prev_gesture  # Hold previous while scrolling

        self._prev_y = None

        # Activate: all 5 fingers up (open palm)
        # But don't activate if we just came from a pinch
        if num_up >= 4:
            self._prev_curl_ratio = None
            return GestureState.ACTIVATE

        # Move: only index finger up (others down)
        if fingers[1] and not fingers[2] and not fingers[3] and not fingers[4]:
            return GestureState.MOVE

        # Idle / fist
        return GestureState.IDLE

    def reset(self):
        """Reset internal state (call when hand is lost)."""
        self._prev_gesture = GestureState.IDLE
        self._prev_y = None
        self._pinch_active = False
        self._tap_active = False
        self._prev_curl_ratio = None
