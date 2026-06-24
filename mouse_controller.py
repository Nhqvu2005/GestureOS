"""
GestureOS — Controls OS mouse cursor using pyautogui + pynput.
"""
import time
import pyautogui
from pynput.mouse import Button, Controller as PynputMouse

import config


class MouseController:
    """Handles mouse actions triggered by gestures."""

    def __init__(self):
        # Disable pyautogui fail-safe (corners) — intentional for gesture control
        pyautogui.FAILSAFE = False
        self._pynput = PynputMouse()
        self._screen_w, self._screen_h = pyautogui.size()
        # Debounce: ignore repeated clicks within this window
        self._last_click_time = 0
        self._click_cooldown = 0.3
        # Track whether left button is currently held
        self._left_held = False
        self._last_gesture = None
        self._last_click_pos = None

    def move(self, x_norm, y_norm):
        """Move cursor to normalized (0-1) screen coordinates."""
        screen_x = int(x_norm * self._screen_w * config.CURSOR_SPEED)
        screen_y = int(y_norm * self._screen_h * config.CURSOR_SPEED)
        # Clamp
        screen_x = max(0, min(self._screen_w - 1, screen_x))
        screen_y = max(0, min(self._screen_h - 1, screen_y))
        pyautogui.moveTo(screen_x, screen_y)

    def left_click_down(self):
        """Press left mouse button."""
        if not self._left_held:
            self._pynput.press(Button.left)
            self._left_held = True

    def left_click_up(self):
        """Release left mouse button."""
        if self._left_held:
            self._pynput.release(Button.left)
            self._left_held = False

    def right_click(self):
        """Perform a right click with debounce."""
        now = time.time()
        if now - self._last_click_time > self._click_cooldown:
            self._pynput.click(Button.right)
            self._last_click_time = now

    def scroll(self, direction):
        """Scroll up or down. direction: 1 (up) or -1 (down)."""
        pyautogui.scroll(3 * direction)

    def release_all(self):
        """Release any held buttons (cleanup)."""
        if self._left_held:
            self._pynput.release(Button.left)
            self._left_held = False
