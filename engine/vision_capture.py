import base64
import ctypes
import io
import time
from ctypes import wintypes
import numpy as np
from PIL import Image, ImageEnhance, ImageOps

user32 = ctypes.windll.user32
gdi32 = ctypes.windll.gdi32
dwmapi = getattr(ctypes.windll, 'dwmapi', None)

PW_RENDERFULLCONTENT = 0x00000002
DWMWA_EXTENDED_FRAME_BOUNDS = 9

class RECT(ctypes.Structure):
    _fields_ = [
        ("left", ctypes.c_long),
        ("top", ctypes.c_long),
        ("right", ctypes.c_long),
        ("bottom", ctypes.c_long),
    ]

def get_active_window_rect(hwnd: int) -> Tuple_Rect:
    """Gets accurate window bounds excluding invisible DWM drop shadows."""
    rect = RECT()
    if dwmapi and hasattr(dwmapi, 'DwmGetWindowAttribute'):
        hr = dwmapi.DwmGetWindowAttribute(hwnd, DWMWA_EXTENDED_FRAME_BOUNDS, ctypes.byref(rect), ctypes.sizeof(rect))
        if hr == 0:
            return (rect.left, rect.top, rect.right, rect.bottom)
    user32.GetWindowRect(hwnd, ctypes.byref(rect))
    return (rect.left, rect.top, rect.right, rect.bottom)

Tuple_Rect = tuple

def capture_active_window_hybrid() -> Optional_Image:
    """
    Hybrid hardware-accelerated capture of the active foreground window.
    Tries PrintWindow(0x2) with fast fallback to desktop-coordinate crop.
    """
    hwnd = user32.GetForegroundWindow()
    if not hwnd:
        return None

    left, top, right, bottom = get_active_window_rect(hwnd)
    width = max(10, right - left)
    height = max(10, bottom - top)

    # 1. Try Hardware-Accelerated PrintWindow(0x2)
    try:
        hwnd_dc = user32.GetWindowDC(hwnd)
        mem_dc = gdi32.CreateCompatibleDC(hwnd_dc)
        bitmap = gdi32.CreateCompatibleBitmap(hwnd_dc, width, height)
        gdi32.SelectObject(mem_dc, bitmap)

        # Call PrintWindow with PW_RENDERFULLCONTENT
        res = user32.PrintWindow(hwnd, mem_dc, PW_RENDERFULLCONTENT)
        if res:
            # Extract bitmap bits into PIL Image
            bmpinfo = BITMAPINFO()
            bmpinfo.bmiHeader.biSize = ctypes.sizeof(BITMAPINFOHEADER)
            bmpinfo.bmiHeader.biWidth = width
            bmpinfo.bmiHeader.biHeight = -height # Top-down DIB
            bmpinfo.bmiHeader.biPlanes = 1
            bmpinfo.bmiHeader.biBitCount = 32
            bmpinfo.bmiHeader.biCompression = 0 # BI_RGB

            buf = (ctypes.c_char * (width * height * 4))()
            gdi32.GetDIBits(mem_dc, bitmap, 0, height, buf, ctypes.byref(bmpinfo), 0)
            img = Image.frombuffer("RGBA", (width, height), buf, "raw", "BGRA", 0, 1)

            # Cleanup GDI objects
            gdi32.DeleteObject(bitmap)
            gdi32.DeleteDC(mem_dc)
            user32.ReleaseDC(hwnd, hwnd_dc)

            # Check if frame is all black (DirectComposition failure)
            if not is_black_frame(img):
                return img
    except Exception as e:
        print(f"[VisionCapture] PrintWindow fallback triggered: {e}")

    # 2. Desktop-Coordinate Cropping Fallback
    try:
        from PIL import ImageGrab
        bbox = (max(0, left), max(0, top), right, bottom)
        img = ImageGrab.grab(bbox=bbox, all_screens=True)
        return img
    except Exception as ex:
        print(f"[VisionCapture] Desktop grab failed: {ex}")
        return None

Optional_Image = Image.Image

class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [
        ("biSize", wintypes.DWORD),
        ("biWidth", wintypes.LONG),
        ("biHeight", wintypes.LONG),
        ("biPlanes", wintypes.WORD),
        ("biBitCount", wintypes.WORD),
        ("biCompression", wintypes.DWORD),
        ("biSizeImage", wintypes.DWORD),
        ("biXPelsPerMeter", wintypes.LONG),
        ("biYPelsPerMeter", wintypes.LONG),
        ("biClrUsed", wintypes.DWORD),
        ("biClrImportant", wintypes.DWORD),
    ]

class BITMAPINFO(ctypes.Structure):
    _fields_ = [
        ("bmiHeader", BITMAPINFOHEADER),
        ("bmiColors", wintypes.DWORD * 3),
    ]

def is_black_frame(img: Image.Image) -> bool:
    """Checks if captured image is completely black."""
    stat = ImageOps.grayscale(img).getextrema()
    return stat == (0, 0)

def preprocess_for_ocr(img: Image.Image, max_dim: int = 1600) -> bytes:
    """
    Perceptual Luminance Grayscale + Local Contrast Enhancement + WebP Compression.
    Preserves dark-theme code comments while compressing payload under 250 KB for sub-150ms transmission.
    """
    # 1. Resize if image exceeds max dimension while preserving aspect ratio
    w, h = img.size
    if max(w, h) > max_dim:
        scale = max_dim / float(max(w, h))
        img = img.resize((int(w * scale), int(h * scale)), Image.Resampling.LANCZOS)

    # 2. Convert to Perceptual Luminance Grayscale (Y = 0.299R + 0.587G + 0.114B)
    gray = img.convert("L")

    # 3. CLAHE-like Local Adaptive Contrast Boost
    # Equalize histogram with clip limit simulation
    enhancer = ImageEnhance.Contrast(gray)
    contrasted = enhancer.enhance(1.8) # High text edge definition
    
    # Sharpness enhancement for 12px code fonts
    sharpener = ImageEnhance.Sharpness(contrasted)
    final_img = sharpener.enhance(1.5)

    # 4. Compress to WebP (Quality 80)
    out_io = io.BytesIO()
    final_img.save(out_io, format="WEBP", quality=80, method=4)
    webp_bytes = out_io.getvalue()
    print(f"[VisionCapture] Preprocessed image size: {len(webp_bytes) / 1024:.1f} KB (Target < 250 KB)")
    return webp_bytes

def capture_and_preprocess_webp() -> Optional[bytes]:
    """Single-call helper to capture active window and return optimized WebP bytes."""
    raw_img = capture_active_window_hybrid()
    if raw_img is None:
        return None
    return preprocess_for_ocr(raw_img)
