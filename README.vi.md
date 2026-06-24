# GestureOS

**Điều khiển chuột máy tính bằng cử chỉ bàn tay qua webcam — xây dựng với MediaPipe và OpenCV.**

GestureOS quay video real-time từ webcam, nhận diện các điểm mốc bàn tay bằng Google MediaPipe, phân loại cử chỉ và ánh xạ thành các thao tác chuột (di chuyển, click, cuộn, kéo thả). Đây là sản phẩm demo về thị giác máy tính thể hiện khả năng xử lý real-time, nhận diện cử chỉ và tương tác với hệ điều hành.

---

## Tính năng

| Cử chỉ | Hành động | Mô tả |
|--------|-----------|-------|
| Xòe bàn tay (5 ngón) | **Activate** | Bật chế độ điều khiển bằng cử chỉ |
| Nắm tay (0 ngón) | **Disable / Idle** | Tắt chế độ điều khiển |
| Chỉ ngón trỏ | **Move cursor** | Di chuyển chuột theo ngón trỏ |
| Gập ngón trỏ nhanh | **Left click (tap)** | Click chuột trái bằng cách búng ngón trỏ |
| Chụm ngón cái + trỏ | **Left click (pinch)** | Click trái kiểu chụm (dự phòng) |
| Chụm ngón cái + giữa | **Right click** | Click chuột phải |
| Giơ ngón trỏ + giữa, đưa tay lên | **Cuộn lên** | Hai ngón, đưa tay lên để cuộn |
| Giơ ngón trỏ + giữa, đưa tay xuống | **Cuộn xuống** | Hai ngón, đưa tay xuống để cuộn |

### Cách click trái

- **Tap (khuyên dùng):** Đang chỉ ngón trỏ, gập nhanh ngón trỏ xuống — sẽ trigger left click. Vị trí chuột được khoá trước khi gập, tránh bị lệch chuột khi click.
- **Pinch (dự phòng):** Chụm ngón cái và ngón trỏ vào nhau.

---

## Kiến trúc

```
GestureOS/
├── main.py                  # Điểm vào chương trình
├── virtual_mouse.py         # Điều phối chính
├── hand_tracker.py          # Bao bọc MediaPipe HandLandmarker
├── gesture_recognizer.py    # Phân loại landmark → GestureState
├── mouse_controller.py      # GestureState → thao tác chuột
├── config.py                # Ngưỡng, tham số, độ mượt
├── hand_landmarker.task     # Model MediaPipe hand landmark
├── requirements.txt
├── README.md
└── README.vi.md
```

**Pipeline:** `Camera → MediaPipe → 21 landmarks/frame → GestureRecognizer → GestureState → MouseController → OS cursor`

### Chi tiết thiết kế

- **Làm mượt (Smoothing):** Exponential Moving Average (EMA) trên tọa độ đầu ngón trỏ (`alpha = 0.3`) kèm dead zone để giảm rung.
- **Frame skip:** Mặc định MediaPipe xử lý mỗi 2 frame một lần. Kết quả được cache cho các frame bỏ qua, tăng gần gấp đôi FPS mà không ảnh hưởng độ mượt.
- **Phát hiện pinch tỉ lệ:** Khoảng cách pinch được chuẩn hóa theo kích thước bàn tay (`distance(cổ tay, đốt giữa ngón giữa)`) với hysteresis (0.20 bắt / 0.25 nhả) để tránh bật tắt liên tục.
- **Khoá chuột (Cursor lock):** Trong khi click, vị trí chuột bị đóng băng tại điểm trước khi click để tránh di lệch.
- **Safety timeout:** Nếu mất tay khỏi khung hình hơn ~1 giây, tất cả nút chuột đang giữ sẽ tự động nhả.

---

## Yêu cầu

- Python 3.8+
- Webcam
- Windows / Linux / macOS

## Cài đặt

```bash
# Clone repository
git clone https://github.com/Tencia/GestureOS.git
cd GestureOS

# Cài dependencies
pip install -r requirements.txt
```

File model (`hand_landmarker.task`) đã được bao gồm trong repository. Nếu bị thiếu, tải thủ công:

```bash
curl -L -o hand_landmarker.task "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task"
```

## Sử dụng

```bash
python main.py
```

| Phím | Hành động |
|------|-----------|
| `ESC` | Thoát chương trình |

### Mẹo sử dụng tốt nhất

- Đảm bảo ánh sáng tốt — tránh ngược sáng hoặc bóng đổ lên tay.
- Giữ tay trong khung hình camera (khoảng cách khuyên dùng: 30–60 cm).
- Khi click tap, gập ngón trỏ **nhanh** — gập chậm sẽ bị bỏ qua (tránh click nhầm khi nắm tay).
- Nếu chuột di chuyển quá chậm hoặc quá nhanh, điều chỉnh `CURSOR_SPEED` trong `config.py`.

---

## Cấu hình

Tất cả tham số đều nằm trong `config.py`:

| Tham số | Mặc định | Mô tả |
|---------|----------|-------|
| `SMOOTHING_ALPHA` | `0.3` | Hệ số làm mượt EMA (thấp = mượt hơn, cao = phản hồi nhanh hơn) |
| `DEAD_ZONE` | `0.005` | Ngưỡng bỏ qua rung chuột tối thiểu (normalized) |
| `CURSOR_SPEED` | `2.0` | Hệ số nhân tốc độ chuột |
| `PINCH_THRESHOLD` | `0.20` | Ngưỡng phát hiện pinch (theo tỉ lệ tay) |
| `PINCH_HYSTERESIS` | `0.25` | Ngưỡng nhả pinch cao hơn (chống bật tắt) |
| `FRAME_SKIP` | `1` | Xử lý MediaPipe mỗi N frame (1 = mỗi 2 frame) |
| `TAP_PRESS_THRESHOLD` | `0.12` | Tỉ lệ gập ngón trỏ để kích hoạt tap |
| `TAP_VELOCITY_THRESHOLD` | `0.04` | Vận tốc gập tối thiểu mỗi frame |

---

## Xử lý sự cố

| Vấn đề | Giải pháp |
|--------|-----------|
| Camera không mở | Kiểm tra `CAM_ID` trong `config.py` (thử `0`, `1`, `2`) |
| FPS thấp | Tăng `FRAME_SKIP` trong `config.py` hoặc giảm `CAM_WIDTH`/`CAM_HEIGHT` |
| Chuột nhảy khi click | Giữ ngón trỏ ổn định trước khi gập/chụm |
| Không nhận diện được tay | Cải thiện ánh sáng, giảm background lộn xộn |
| `ModuleNotFoundError` | Chạy `pip install -r requirements.txt` |

---

## Giấy phép

MIT License — xem [LICENSE](LICENSE) để biết chi tiết.

## Tác giả

**Nhqvu2005 (Tencia)**
