"""
GestureOS — Main facade class orchestrating the full pipeline.
"""
import cv2
import numpy as np
import sys

import config
from hand_tracker import HandTracker
from gesture_recognizer import GestureRecognizer, GestureState
from mouse_controller import MouseController


class GestureOS:
    """High-level hand gesture mouse control system."""

    def __init__(self):
        self.tracker = HandTracker()
        self.recognizer = GestureRecognizer()
        self.mouse = MouseController()
        self.cap = cv2.VideoCapture(config.CAM_ID)

        if not self.cap.isOpened():
            raise RuntimeError(f"Cannot open camera #{config.CAM_ID}")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, config.CAM_WIDTH)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, config.CAM_HEIGHT)
        self.cap.set(cv2.CAP_PROP_FPS, config.CAM_FPS)

        # Smoothing state
        self._smooth_x = None
        self._smooth_y = None

        # Activation state
        self._active = True

        # Cursor lock during pinch
        self._lock_x = None
        self._lock_y = None

        # Safety: release held buttons if hand lost
        self._no_hand_frames = 0
        self._max_no_hand_frames = 30  # ~1 second at 30fps

        # FPS counter
        self._fps = 0
        self._frame_count = 0
        self._fps_timer = cv2.getTickCount()

        # Frame skip
        self._skip_counter = 0
        self._last_annotated = None
        self._last_hands_data = None
        self._last_landmarks = None
        self._last_fingers = [False] * 5
        self._last_gesture = GestureState.IDLE

        # Last MOVE position (for tap cursor lock)
        self._last_move_x = None
        self._last_move_y = None

    def _apply_smoothing(self, x, y):
        """Exponential Moving Average smoothing."""
        if self._smooth_x is None:
            self._smooth_x = x
            self._smooth_y = y

        dx = x - self._smooth_x
        dy = y - self._smooth_y

        # Dead zone (normalized coords)
        if abs(dx) < config.DEAD_ZONE:
            dx = 0
        if abs(dy) < config.DEAD_ZONE:
            dy = 0

        self._smooth_x += dx * config.SMOOTHING_ALPHA
        self._smooth_y += dy * config.SMOOTHING_ALPHA

        return self._smooth_x, self._smooth_y

    def _draw_status(self, frame, gesture, fingers, fps):
        """Overlay debug info on the frame."""
        h, w, _ = frame.shape

        # Background panel
        cv2.rectangle(frame, (0, 0), (w, 80), (0, 0, 0, 180), -1)

        # Status text
        status = f"{'ACTIVE' if self._active else 'DISABLED'}"
        gesture_name = gesture.name.replace('_', ' ').title()
        cv2.putText(frame, f"{status} | Gesture: {gesture_name}", (10, 25),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)

        # Fingers state
        finger_labels = ['Thumb', 'Index', 'Mid', 'Ring', 'Pinky']
        finger_str = ' '.join(f"{'1' if f else '0'}" for f in fingers)
        cv2.putText(frame, f"Fingers: {finger_str}  |  FPS: {fps:.0f}", (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)

        # Instructions
        cv2.putText(frame, "ESC: Quit  |  Fist=Idle  |  Palm=Activate", (10, 72),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.4, (150, 150, 150), 1)

        return frame

    def run(self):
        """Main loop — captures, processes, controls."""
        print("GestureOS started!")
        print("   Palm -> Activate  |  Fist -> Idle")
        print("   Index -> Move cursor  |  Curl index -> Left click (tap)")
        print("   Pinch (thumb+index) -> Left click  |  Pinch (thumb+middle) -> Right click")
        print("   Two fingers -> Scroll  |  ESC to quit.\n")

        try:
            while True:
                ret, frame = self.cap.read()
                if not ret:
                    print("Failed to capture frame")
                    break

                frame = cv2.flip(frame, 1)  # Mirror
                h, w, _ = frame.shape

                # Frame skip: process MediaPipe every Nth frame
                self._skip_counter += 1
                should_process = (config.FRAME_SKIP == 0) or (self._skip_counter > config.FRAME_SKIP)

                if should_process:
                    self._skip_counter = 0

                    # Step 1: Process hand tracking
                    annotated, hands_data = self.tracker.process(frame)

                    # Cache results for skipped frames
                    if config.SHOW_DEBUG:
                        self._last_annotated = annotated.copy()
                    self._last_hands_data = hands_data

                    # Step 2: Recognize gesture
                    if hands_data:
                        self._last_landmarks = hands_data[0]['landmarks']
                        self._last_fingers = self.recognizer._fingers_up(self._last_landmarks)
                        self._last_gesture = self.recognizer.recognize(self._last_landmarks, w, h)
                    else:
                        self._last_landmarks = None
                        self._last_fingers = [False] * 5
                        self._last_gesture = GestureState.IDLE
                else:
                    # Skipped frame: reuse cached results
                    annotated = self._last_annotated if self._last_annotated is not None else frame
                    hands_data = self._last_hands_data

                # Use latest results (from cache or fresh processing)
                landmarks = self._last_landmarks
                fingers = self._last_fingers
                gesture = self._last_gesture

                # Step 3: Handle activate/deactivate (run even when inactive)
                if gesture == GestureState.ACTIVATE and not self._active:
                    self._active = True
                    self._smooth_x = None  # Reset smoothing
                    self._lock_x = None
                    self._lock_y = None
                    self._last_move_x = None
                    self._last_move_y = None
                    self.recognizer.reset()
                    print("Activated")
                elif gesture == GestureState.IDLE and self._active and landmarks:
                    if not any(fingers):  # Fist
                        self._active = False
                        self._lock_x = None
                        self._lock_y = None
                        self._last_move_x = None
                        self._last_move_y = None
                        self.mouse.release_all()
                        self.recognizer.reset()
                        print("Disabled (fist)")

                # Safety: release held buttons if hand is lost for too long
                if self._lock_x is not None and not hands_data:
                    self._no_hand_frames += 1
                    if self._no_hand_frames > self._max_no_hand_frames:
                        self._lock_x = None
                        self._lock_y = None
                        self._smooth_x = None
                        self._smooth_y = None
                        self._last_move_x = None
                        self._last_move_y = None
                        self.mouse.release_all()
                        self.recognizer.reset()
                        print("Safety: released buttons (hand lost)")
                else:
                    self._no_hand_frames = 0

                # Step 4: Execute mouse actions (only when active)
                if self._active:
                    self._execute_gesture(gesture, landmarks)

                # Step 5: Draw debug
                if config.SHOW_DEBUG:
                    annotated = self._draw_status(
                        annotated, gesture, fingers, self._fps
                    )

                    # Draw gesture indicator circle
                    color = (0, 255, 0) if self._active else (0, 0, 255)
                    cv2.circle(annotated, (30, 130), 10, color, -1)

                    cv2.imshow(config.DEBUG_WINDOW_NAME, annotated)

                # FPS calculation
                self._frame_count += 1
                if self._frame_count >= 30:
                    now = cv2.getTickCount()
                    self._fps = self._frame_count / ((now - self._fps_timer) / cv2.getTickFrequency())
                    self._fps_timer = now
                    self._frame_count = 0

                # Exit / toggle
                key = cv2.waitKey(1) & 0xFF
                if key == 27:  # ESC
                    print("Exiting...")
                    break

        finally:
            self.cleanup()

    def _cursor_pos(self, landmarks):
        """Get smoothed cursor position from index tip, or locked position during pinch."""
        if not landmarks:
            return None, None

        # If cursor is locked during pinch, use locked position
        # Don't update smoothing while locked
        if self._lock_x is not None:
            return self._lock_x, self._lock_y

        index_tip = landmarks[config.INDEX_TIP]
        sx, sy = self._apply_smoothing(index_tip[0], index_tip[1])
        return sx, sy

    def _execute_gesture(self, gesture, landmarks):
        """Map gesture to mouse action."""
        # Get cursor position (possibly locked)
        sx, sy = self._cursor_pos(landmarks) if landmarks else (None, None)

        # Gesture actions
        if gesture == GestureState.MOVE:
            if sx is not None:
                self.mouse.move(sx, sy)
                # Save for tap cursor lock
                self._last_move_x, self._last_move_y = sx, sy

        elif gesture == GestureState.LEFT_CLICK_DOWN:
            # Lock cursor at pointing position (pre-curl for tap, or current for pinch)
            if sx is not None:
                if self.recognizer._tap_active:
                    # Tap: lock at last MOVE position (pre-curl)
                    if self._lock_x is None:
                        self._lock_x = self._last_move_x if self._last_move_x is not None else sx
                        self._lock_y = self._last_move_y if self._last_move_y is not None else sy
                        self.mouse.move(self._lock_x, self._lock_y)
                else:
                    # Pinch: lock at current position
                    if self._lock_x is None:
                        self._lock_x, self._lock_y = sx, sy
                        self.mouse.move(sx, sy)
            self.mouse.left_click_down()

        elif gesture == GestureState.LEFT_CLICK_UP:
            # Release at the locked position, then unlock
            if self._lock_x is not None:
                self.mouse.move(self._lock_x, self._lock_y)
            self.mouse.left_click_up()
            # Reset smoothing to avoid cursor jump after release
            self._smooth_x = None
            self._smooth_y = None
            self._lock_x = None
            self._lock_y = None

        elif gesture == GestureState.RIGHT_CLICK:
            self._lock_x = None
            if sx is not None:
                self.mouse.move(sx, sy)
            self.mouse.right_click()

        elif gesture == GestureState.SCROLL_UP:
            self.mouse.scroll(1)

        elif gesture == GestureState.SCROLL_DOWN:
            self.mouse.scroll(-1)

        # Track last gesture
        self.recognizer._prev_gesture = gesture

    def cleanup(self):
        """Release all resources."""
        self._lock_x = None
        self._lock_y = None
        self._last_move_x = None
        self._last_move_y = None
        self.mouse.release_all()
        self.recognizer.reset()
        self.tracker.release()
        self.cap.release()
        cv2.destroyAllWindows()
        print("Clean exit.")
