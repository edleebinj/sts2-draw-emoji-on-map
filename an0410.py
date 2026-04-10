# Updated drawing script using the robust worker from draw_emoji.py
import time
import threading
import os
import sys
import pyautogui
import cv2
import numpy as np
import math
from PIL import Image, ImageOps
from pynput import keyboard
from pynput.mouse import Controller as MouseController, Button

# Configuration (merged from original CONFIG and draw_emoji settings)
CONFIG = {
    # System basics
    'DEBUG': False,
    'STANDARD_WIDTH': 400,
    'MAX_DRAW_WIDTH': 1000,
    'MAX_DRAW_HEIGHT': 800,
    'DRAG_DELAY': 0.0007,
    'PIXEL_SKIP': 1,
    # Edge tracing (COUNTOUR mode)
    'CANNY_THRESH1': 40,
    'CANNY_THRESH2': 100,
    'MAX_GAP': 2,
    'MIN_STROKE_LENGTH': 3,
    # Hatching (HATCH mode)
    'HATCH_SPACING': 5,
    'HATCH_LENGTH': 8,
    'HATCH_ANGLE': 45,
    'HATCH_CONTRAST': 1.6,
    # Halftone (HALFTONE mode)
    'WHITE_THRESHOLD': 200,
    'CONTRAST': 2.0,
    'THRESHOLD_OFFSET': -45,
    'DOT_GRID_SIZE': 7,
    'DENSITY_FACTOR': 3,
    # Additional drawing tuning (from draw_emoji)
    'DRAW_DELAY': 0.0017,
    'CLICK_DELAY': 0.000025,
    'MIN_STROKE_LENGTH_DRAW': 30,
    'MAX_GAP_DRAW': 20,
    'PIXEL_SKIP_DRAW': 14,
    'MAX_DOTS': 5000,
    'DOT_CONTRAST_GAMMA': 20,
    'DRAW_MODE': "COMBINED",  # Options: EDGE, HALFTONE, COMBINED
    'MAX_DRAW_WIDTH_EMOJI': 400,
    'MAX_DRAW_HEIGHT_EMOJI': 400,
    # === Pen tool selection ===
    # Set this to the (x, y) screen coordinates of the pen/brush button.
    # The script will click this position before every drawing session.
    'PEN_POSITION': (70, 800),  # <-- tune this to your pen button location
    'PEN_COLOR': (102, 204, 255),  # The blue glow color to look for
}

mouse = MouseController()

# Global state
is_drawing = False
is_running = True
target_image = None
draw_start_pos = (0, 0)

def select_pen():
    """Click the pen tool until it glows blue (meaning it's selected)."""
    px, py = CONFIG['PEN_POSITION']
    target_color = CONFIG['PEN_COLOR']
    
    def is_pen_selected():
        try:
            # Target color from config
            target_r, target_g, target_b = target_color
            
            # Take ONE regional screenshot (much faster than multiple pixel checks on Mac)
            # Capture a small area (size 10) around the pen position
            region_size = 10
            screen_img = pyautogui.screenshot(region=(px - region_size//2, py - region_size//2, region_size, region_size))
            
            # Check pixels in the captured image
            for x in range(region_size):
                for y in range(region_size):
                    pixel = screen_img.getpixel((x, y))
                    r, g, b = pixel[:3]  # Extract RGB, works for both RGB and RGBA pixels
                    
                    # Match with increased tolerance (80)
                    if abs(r - target_r) < 80 and abs(g - target_g) < 80 and abs(b - target_b) < 80:
                        return True
            return False
        except Exception as e:
            print(f"Color check error: {e}")
            return False

    # Try checking first
    if is_pen_selected():
        print("✨ Pen already selected.")
        return

    for i in range(5):  # Try clicking up to 5 times
        print(f"👆 Clicking pen position (Attempt {i+1})...")
        mouse.position = (px, py)
        time.sleep(0.1)
        mouse.press(Button.left)
        mouse.release(Button.left)
        time.sleep(0.1)  # Wait for UI response
        
        if is_pen_selected():
            print("✅ Pen confirmed selected.")
            return
            
    print("⚠️ Warning: Pen might not be selected (color mismatch).")

def process_image(image_path, start_x, start_y):
    """Load image, resize to fit screen, and generate edge/dot masks based on CONFIG."""
    try:
        pil_img = Image.open(image_path).convert('L')
    except Exception as e:
        print(f"Error loading image '{image_path}': {e}")
        return None, None
    width, height = pil_img.size
    screen_w, screen_h = pyautogui.size()
    # Calculate safe boundaries for centered drawing
    dist_to_edge_w = min(start_x, screen_w - start_x)
    dist_to_edge_h = min(start_y, screen_h - start_y)
    
    max_w = min(CONFIG['MAX_DRAW_WIDTH_EMOJI'], dist_to_edge_w * 2 - 10)
    max_h = min(CONFIG['MAX_DRAW_HEIGHT_EMOJI'], dist_to_edge_h * 2 - 10)
    
    if max_w <= 0 or max_h <= 0:
        print("Error: Mouse too close to screen edge.")
        return None, None
    if width > max_w or height > max_h:
        ratio = min(max_w / width, max_h / height)
        pil_img = pil_img.resize((int(width * ratio), int(height * ratio)), Image.Resampling.LANCZOS)
        width, height = pil_img.size
    edges_mask = None
    dot_mask = None
    img_arr = np.array(pil_img)
    if CONFIG['DRAW_MODE'] in ["EDGE", "COMBINED"]:
        blurred = cv2.GaussianBlur(img_arr, (3, 3), 0) if CONFIG.get('CANNY_BLUR', 0) > 0 else img_arr
        edges_mask = cv2.Canny(blurred, CONFIG['CANNY_THRESH1'], CONFIG['CANNY_THRESH2'])
    if CONFIG['DRAW_MODE'] in ["HALFTONE", "COMBINED"]:
        img_norm = ImageOps.autocontrast(pil_img)
        arr = np.array(img_norm, dtype=np.float32)
        density = 255.0 - arr
        density = np.power(density / 255.0, CONFIG['DOT_CONTRAST_GAMMA'])
        pdf = density / np.sum(density) if np.sum(density) > 0 else np.ones_like(density) / (width * height)
        flat_pdf = pdf.flatten()
        num_pixels = width * height
        num_dots = min(CONFIG['MAX_DOTS'], num_pixels)
        try:
            chosen = np.random.choice(num_pixels, size=num_dots, replace=False, p=flat_pdf)
        except ValueError:
            chosen = np.random.choice(num_pixels, size=num_dots, replace=True, p=flat_pdf)
            chosen = np.unique(chosen)
        dot_arr = np.zeros((height, width), dtype=np.uint8)
        for idx in chosen:
            y = idx // width
            x = idx % width
            dot_arr[y, x] = 255
        dot_mask = dot_arr
    return edges_mask, dot_mask

def drawing_worker():
    global is_drawing, is_running, target_image, draw_start_pos
    while is_running:
        if is_drawing and target_image:
            start_x, start_y = draw_start_pos
            edges_mask, dot_mask = process_image(target_image, start_x, start_y)
            if edges_mask is None and dot_mask is None:
                is_drawing = False
                continue
            
            # Calculate centering offset
            mask_h, mask_w = (edges_mask if edges_mask is not None else dot_mask).shape
            origin_x = start_x - (mask_w // 2)
            origin_y = start_y - (mask_h // 2)

            strokes = []
            dots = []
            # Build strokes from edges
            if edges_mask is not None:
                # Use a dictionary for O(1) pixel presence checks
                h, w = edges_mask.shape
                unvisited = { (x, y) for y in range(h) for x in range(w) if edges_mask[y, x] == 255 }
                
                max_gap = CONFIG['MAX_GAP_DRAW']
                while unvisited:
                    cur = unvisited.pop()
                    cur_stroke = [cur]
                    while True:
                        best = None
                        # Search in expanding shells for efficiency
                        found_nb = False
                        for r in range(1, max_gap + 1):
                            # Boundary of square with radius r
                            for dx in range(-r, r + 1):
                                for dy in [-r, r]: # Top and Bottom edges
                                    nb = (cur[0] + dx, cur[1] + dy)
                                    if nb in unvisited:
                                        best = nb; found_nb = True; break
                                if found_nb: break
                                for dy in range(-r + 1, r): # Left and Right edges (minus corners)
                                    for dx in [-r, r]:
                                        nb = (cur[0] + dx, cur[1] + dy)
                                        if nb in unvisited:
                                            best = nb; found_nb = True; break
                                    if found_nb: break
                            if found_nb: break
                        
                        if best:
                            unvisited.remove(best)
                            cur_stroke.append(best)
                            cur = best
                        else:
                            break
                    if len(cur_stroke) >= CONFIG['MIN_STROKE_LENGTH_DRAW']:
                        strokes.append(cur_stroke)
            # Build dots list
            if dot_mask is not None:
                h, w = dot_mask.shape
                for y in range(h):
                    for x in range(w):
                        if dot_mask[y, x] == 255:
                            dots.append((x, y))
                dots.sort(key=lambda p: (p[1], p[0]))
            # Execute drawing
            print("🚀 DRAWING NOW!")
            select_pen()
            time.sleep(0.2)
            # Strokes
            for stroke in strokes:
                if not is_drawing:
                    break
                sx, sy = stroke[0]
                mouse.position = (origin_x + sx, origin_y + sy)
                time.sleep(CONFIG['DRAW_DELAY'])
                mouse.press(Button.left)
                time.sleep(CONFIG['DRAW_DELAY'])
                for x, y in stroke[1::CONFIG['PIXEL_SKIP_DRAW']]:
                    mouse.position = (origin_x + x, origin_y + y)
                    time.sleep(CONFIG['DRAG_DELAY'])
                    if not is_drawing:
                        break
                ex, ey = stroke[-1]
                mouse.position = (origin_x + ex, origin_y + ey)
                mouse.release(Button.left)
                time.sleep(CONFIG['DRAW_DELAY'])
            # Dots
            for dx, dy in dots:
                if not is_drawing:
                    break
                time.sleep(CONFIG['CLICK_DELAY'])
                mouse.position = (origin_x + dx, origin_y + dy)
                mouse.press(Button.left)
                mouse.release(Button.left)
            if is_drawing:
                print("✅ Done drawing! Press 1-9 for another image, or ESC to quit.")
            else:
                print("🛑 Drawing CANCELLED. Ready for the next command.")
            is_drawing = False
        time.sleep(0.01)

def on_press(key):
    global is_drawing, is_running, target_image, draw_start_pos
    try:
        if key.char in [str(i) for i in range(1, 10)]:
            if not is_drawing:
                target_image = f"image{key.char}.png"
                draw_start_pos = mouse.position
                is_drawing = True
        elif key.char == '0':
            if is_drawing:
                print("🛑 Cancelling current draw! Program remains active...")
                is_drawing = False
    except AttributeError:
        pass
    if key == keyboard.Key.esc:
        print("🚨 SHUTTING DOWN PROGRAM ENTIRELY...")
        is_drawing = False
        is_running = False
        return False

if __name__ == "__main__":
    print("Drawing script (converted from draw_emoji) ready.")
    thread = threading.Thread(target=drawing_worker, daemon=True)
    thread.start()
    with keyboard.Listener(on_press=on_press) as listener:
        listener.join()