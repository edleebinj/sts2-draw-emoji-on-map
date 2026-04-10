# sts2-draw-emoji-on-map
Slay the Spire automated image/emoji drawing tool for the map.

This is a **vibe-coded** project designed to let you express yourself on the Slay the Spire map by "drawing" images using rapid mouse inputs. It uses OpenCV for edge detection and `pynput` for cross-platform input control, specifically optimized for high-performance execution on macOS.

## 🚀 Features
- **Multi-Image Support**: Store up to 9 different images (`image1.png` to `image9.png`).
- **One-Key Triggers**: Press keys `1-9` to instantly start drawing the corresponding image at your mouse cursor.
- **Smart Centering**: The image is automatically centered at your current mouse position when the task starts.
- **Auto Pen Selection**: The script automatically detects if your drawing pen is selected by checking for a specific "blue glow" color at a configurable screen position.
- **Composite Drawing Mode**: Combines **Edge Tracing** (Canny) and **Stochastic Halftoning** (random dots) for a detailed, sketchy hand-drawn look.
- **Performance Optimized**: 
    - Fast pathfinding algorithm to minimize pen-up/pen-down movements.
    - Optimized regional screenshots for macOS to eliminate interface lag.

## 🛠 Setup
1. **Install dependencies**:
   ```bash
   pip install Pillow opencv-python numpy pyautogui pynput
   ```
2. **Prepare your images**: Place your images in the same directory as the script, named `image1.png`, `image2.png`, etc. (Transparent PNGs are automatically handled with a white background).
3. **Configure the Pen**: Open `an0410.py` and adjust the `PEN_POSITION` in the `CONFIG` section to match the coordinates of your pen tool on the screen.

## 🎮 How to Use
1. Run the script:
   ```bash
   python an0410.py
   ```
2. In-game, hover your mouse where you want to draw.
3. **Press `1-9`**: Starts the drawing process.
4. **Press `0`**: Cancels the current drawing task immediately.
5. **Press `Esc`**: Safely shuts down the entire script.

## ⚙️ Configuration
You can tune the "vibe" of the drawing in the `CONFIG` dictionary:
- `DRAW_MODE`: Choose between `"EDGE"`, `"HALFTONE"`, or `"COMBINED"`.
- `DRAG_DELAY`: Controls the speed of the line drawing.
- `PIXEL_SKIP_DRAW`: Controls the density of the lines (higher = faster but sketchier).
- `PEN_COLOR`: The specific RGB color of the "selected" pen tool (default is bright blue).

---
*Created with 💙 by Antigravity.*
