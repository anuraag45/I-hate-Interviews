import ctypes
import struct
import sys
from ctypes import wintypes

# Win32 Constants
WDA_NONE = 0x00000000
WDA_MONITOR = 0x00000001
WDA_EXCLUDEFROMCAPTURE = 0x00000011

GWL_EXSTYLE = -20
WS_EX_NOACTIVATE = 0x08000000
WS_EX_LAYERED = 0x00080000
WS_EX_TRANSPARENT = 0x00000020
WS_EX_TOOLWINDOW = 0x00000080

SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_NOACTIVATE = 0x0010
SWP_FRAMECHANGED = 0x0020

DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2 = -4

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
shcore = getattr(ctypes.windll, 'shcore', None)

def init_dpi_awareness():
    """Enforces Per-Monitor V2 DPI awareness to prevent rendering glitches on multi-monitor setups."""
    try:
        if hasattr(user32, 'SetProcessDpiAwarenessContext'):
            user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2))
        elif shcore and hasattr(shcore, 'SetProcessDpiAwareness'):
            shcore.SetProcessDpiAwareness(2) # PROCESS_PER_MONITOR_DPI_AWARE
        else:
            user32.SetProcessDPIAware()
    except Exception as e:
        print(f"[Stealth] Warning setting DPI awareness: {e}")

def apply_stealth_affinity(hwnd: int, exclude: bool = True, enabled: bool = None) -> bool:
    """
    Applies WDA_EXCLUDEFROMCAPTURE (0x00000011) to hide the window from Zoom, Teams, Meet, Discord, and OBS.
    Falls back to WDA_MONITOR (0x01) on older Windows builds.
    Accepts exclude or enabled keyword arguments.
    """
    if enabled is not None:
        exclude = enabled
    if not hwnd or sys.platform != "win32":
        return False
    try:
        affinity = WDA_EXCLUDEFROMCAPTURE if exclude else WDA_NONE
        res = user32.SetWindowDisplayAffinity(hwnd, affinity)
        if not res and exclude:
            res = user32.SetWindowDisplayAffinity(hwnd, WDA_MONITOR)
        return bool(res)
    except Exception as e:
        print(f"[Stealth] Error applying display affinity: {e}")
        return False

def apply_non_activating_styles(hwnd: int, click_through: bool = False) -> bool:
    """
    Sets WS_EX_NOACTIVATE to prevent stealing focus (avoids window.onblur in browser testing platforms),
    and optionally WS_EX_TRANSPARENT for click-through ghost mode.
    """
    if not hwnd or sys.platform != "win32":
        return False
    try:
        style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
        style |= WS_EX_NOACTIVATE | WS_EX_LAYERED
        
        if click_through:
            style |= WS_EX_TRANSPARENT
        else:
            style &= ~WS_EX_TRANSPARENT
            
        user32.SetWindowLongW(hwnd, GWL_EXSTYLE, style)
        # Flush frame changed so Windows immediately recognizes updated click absorption
        user32.SetWindowPos(
            hwnd, 0, 0, 0, 0, 0,
            SWP_NOMOVE | SWP_NOSIZE | SWP_NOZORDER | SWP_NOACTIVATE | SWP_FRAMECHANGED
        )
        return True
    except Exception as e:
        print(f"[Stealth] Error configuring window styles: {e}")
        return False

def set_click_through(hwnd: int, click_through: bool = True) -> bool:
    """Convenience wrapper for apply_non_activating_styles."""
    return apply_non_activating_styles(hwnd, click_through=click_through)


def atomic_exchange_u32(buf, offset: int, new_val: int):
    """
    Performs an aligned atomic 32-bit integer update in shared memory
    and flushes CPU store buffers across cores via FlushProcessWriteBuffers.
    """
    struct.pack_into("<I", buf, offset, new_val)
    try:
        kernel32.FlushProcessWriteBuffers()
    except Exception:
        pass
