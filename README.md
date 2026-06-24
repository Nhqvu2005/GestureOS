# GestureOS

**Control your computer mouse using hand gestures via webcam — built with MediaPipe and OpenCV.**

GestureOS captures real-time video from your webcam, detects hand landmarks using Google MediaPipe, classifies gestures, and maps them to mouse actions (move, click, scroll, drag). It's a pure computer vision demo showcasing real-time hand tracking, gesture classification, and OS-level automation.

---

## Features

| Gesture | Action | Description |
|---------|--------|-------------|
| Open palm (5 fingers) | **Activate** | Enable gesture control mode |
| Fist (0 fingers) | **Disable / Idle** | Disable gesture control mode |
| Index finger only | **Move cursor** | Point with index finger to move the mouse |
| Curl index finger | **Left click (tap)** | Quickly curl your index finger downward to click |
| Pinch thumb + index | **Left click (pinch)** | Alternate left-click method |
| Pinch thumb + middle | **Right click** | Quick pinch for right-click |
| Index + middle up, move hand up | **Scroll up** | Two-finger salute, move hand upward |
| Index + middle up, move hand down | **Scroll down** | Two-finger salute, move hand downward |

### Click Methods

- **Tap (recommended):** While pointing with your index finger, quickly curl it downward — this triggers a left click. The cursor position is locked before the curl, preventing the accidental movement common with pinch-based clicking.
- **Pinch (alternative):** Pinch your thumb and index finger together for a traditional pinch-to-click.

---

## Architecture

```
GestureOS/
├── main.py                  # Entry point
├── virtual_mouse.py         # Main orchestrator (facade)
├── hand_tracker.py          # MediaPipe HandLandmarker wrapper
├── gesture_recognizer.py    # Landmark classification → GestureState
├── mouse_controller.py      # GestureState → OS mouse actions
├── config.py                # Thresholds, smoothing, parameters
├── hand_landmarker.task     # MediaPipe hand landmark model
├── requirements.txt
├── README.md
└── README.vi.md
```

**Pipeline:** `Camera → MediaPipe → 21 landmarks/frame → GestureRecognizer → GestureState → MouseController → OS cursor`

### Key Design Details

- **Smoothing:** Exponential Moving Average (EMA) on index tip coordinates (`alpha = 0.3`) with a configurable dead zone to reduce jitter.
- **Frame skip:** MediaPipe processes every 2nd frame by default. Results are cached and reused for skipped frames, roughly doubling FPS without sacrificing smoothness.
- **Scale-invariant pinch:** Pinch distance is normalized by hand size (`distance(wrist, middle_mcp)`) with hysteresis (0.20 engage / 0.25 release) to prevent rapid toggling.
- **Cursor lock:** During click actions, cursor position is frozen at the pre-click location to prevent unintended movement.
- **Safety timeout:** If the hand is lost for more than ~1 second, all held mouse buttons are automatically released.

---

## Requirements

- Python 3.8+
- Webcam
- Windows / Linux / macOS

## Installation

```bash
# Clone the repository
git clone https://github.com/Tencia/GestureOS.git
cd GestureOS

# Install dependencies
pip install -r requirements.txt
```

The hand landmark model (`hand_landmarker.task`) is included in the repository. If missing, download it manually:

```bash
curl -L -o hand_landmarker.task "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
```

## Usage

```bash
python main.py
```

| Key | Action |
|-----|--------|
| `ESC` | Quit the application |

### Tips for Best Results

- Ensure good lighting — avoid strong backlight or shadows on your hand.
- Keep your hand within the camera's field of view (recommended distance: 30–60 cm).
- For tap clicking, curl your index finger **quickly** — a slow curl is ignored (prevents accidental clicks when making a fist).
- If the cursor feels too slow or too fast, adjust `CURSOR_SPEED` in `config.py`.

---

## Configuration

All tunable parameters are in `config.py`:

| Parameter | Default | Description |
|-----------|---------|-------------|
| `SMOOTHING_ALPHA` | `0.3` | EMA smoothing factor (lower = smoother, higher = more responsive) |
| `DEAD_ZONE` | `0.005` | Minimum cursor movement (normalized) to register |
| `CURSOR_SPEED` | `2.0` | Cursor speed multiplier |
| `PINCH_THRESHOLD` | `0.20` | Pinch detection threshold (scaled by hand size) |
| `PINCH_HYSTERESIS` | `0.25` | Higher threshold to release pinch (prevents toggling) |
| `FRAME_SKIP` | `1` | Process MediaPipe every Nth frame (1 = every 2nd frame) |
| `TAP_PRESS_THRESHOLD` | `0.12` | Index curl ratio to trigger a tap click |
| `TAP_VELOCITY_THRESHOLD` | `0.04` | Minimum curl velocity per frame for tap detection |

---

## Troubleshooting

| Problem | Solution |
|---------|----------|
| Camera not opening | Check `CAM_ID` in `config.py` (try `0`, `1`, `2`) |
| Low FPS | Increase `FRAME_SKIP` in `config.py` or reduce `CAM_WIDTH`/`CAM_HEIGHT` |
| Cursor jumps during click | Make sure your index finger is stable before curling/pinching |
| Hand not detected | Improve lighting, reduce background clutter, check camera focus |
| `ModuleNotFoundError` | Run `pip install -r requirements.txt` |

---

## License

MIT License — see [LICENSE](LICENSE) for details.

## Author

**Nhqvu2005 (Tencia)**
