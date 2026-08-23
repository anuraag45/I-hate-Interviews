import ctypes
import threading
import time
from ctypes import wintypes
from typing import Callable, Dict, Optional, Tuple

user32 = ctypes.windll.user32

# Win32 Constants
WM_HOTKEY = 0x0312
PM_NOREMOVE = 0x0000

# Modifier flags
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
MOD_NOREPEAT = 0x4000

# Virtual Key Codes
VK_SPACE = 0x20
VK_RETURN = 0x0D
VK_ESCAPE = 0x1B
VK_1 = 0x31
VK_2 = 0x32
VK_3 = 0x33
VK_S = 0x53
VK_H = 0x48
VK_T = 0x54
VK_J = 0x4A
VK_K = 0x4B
VK_A = 0x41
VK_C = 0x43
VK_Q = 0x51


class HotkeyDefinition:
    def __init__(self, hotkey_id: int, name: str, primary_mod: int, primary_vk: int,
                 fallback_mod: Optional[int] = None, fallback_vk: Optional[int] = None,
                 callback: Optional[Callable] = None):
        self.id = hotkey_id
        self.name = name
        self.primary_mod = primary_mod | MOD_NOREPEAT
        self.primary_vk = primary_vk
        self.fallback_mod = (fallback_mod | MOD_NOREPEAT) if fallback_mod is not None else None
        self.fallback_vk = fallback_vk
        self.callback = callback
        self.active_shortcut_str = ""
        self.registered = False

class Win32HotkeyManager:
    def __init__(self):
        self._thread: Optional[threading.Thread] = None
        self._running = False
        self._thread_id: Optional[int] = None
        self._hotkeys: Dict[int, HotkeyDefinition] = {}
        self._status_callbacks: Dict[str, str] = {}
        self._lock = threading.Lock()

    def add_hotkey(self, hotkey_id: int, name: str, primary_mod: int, primary_vk: int,
                   fallback_mod: Optional[int] = None, fallback_vk: Optional[int] = None,
                   callback: Optional[Callable] = None):
        self._hotkeys[hotkey_id] = HotkeyDefinition(
            hotkey_id, name, primary_mod, primary_vk, fallback_mod, fallback_vk, callback
        )

    def start(self):
        """Starts the dedicated Win32 message pump thread."""
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._message_loop, name="Win32HotkeyThread", daemon=True)
        self._thread.start()

    def _message_loop(self):
        # 1. Force Windows to create a message queue for this thread
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, PM_NOREMOVE)
        self._thread_id = kernel32_get_thread_id()

        # 2. Register all hotkeys with fallback cascade
        for hk_id, hk in self._hotkeys.items():
            success = user32.RegisterHotKey(None, hk_id, hk.primary_mod, hk.primary_vk)
            if success:
                hk.registered = True
                hk.active_shortcut_str = self._format_hotkey(hk.primary_mod, hk.primary_vk)
                self._status_callbacks[hk.name] = f"Active: {hk.active_shortcut_str}"
            elif hk.fallback_mod is not None and hk.fallback_vk is not None:
                # Primary collision - try fallback cascade
                fallback_success = user32.RegisterHotKey(None, hk_id, hk.fallback_mod, hk.fallback_vk)
                if fallback_success:
                    hk.registered = True
                    hk.active_shortcut_str = self._format_hotkey(hk.fallback_mod, hk.fallback_vk)
                    self._status_callbacks[hk.name] = f"Fallback Active: {hk.active_shortcut_str} (Primary Claimed)"
                else:
                    hk.registered = False
                    self._status_callbacks[hk.name] = "Failed (Collision on both Primary & Fallback)"
            else:
                hk.registered = False
                self._status_callbacks[hk.name] = "Failed (Hotkey Claimed by another App)"

        print("[Hotkeys] Registered Hotkey Statuses:")
        for name, status in self._status_callbacks.items():
            print(f"  - {name}: {status}")

        # 3. Blocking Win32 Message Pump
        try:
            while self._running:
                # GetMessage blocks until a message is received or WM_QUIT
                res = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if res == 0 or res == -1: # WM_QUIT or Error
                    break
                
                if msg.message == WM_HOTKEY:
                    triggered_id = msg.wParam
                    if triggered_id in self._hotkeys:
                        hk_def = self._hotkeys[triggered_id]
                        if hk_def.callback:
                            try:
                                # Dispatch in a non-blocking thread so the pump is never stalled
                                threading.Thread(target=hk_def.callback, daemon=True).start()
                            except Exception as ex:
                                print(f"[Hotkeys] Callback exception for {hk_def.name}: {ex}")
                
                user32.TranslateMessage(ctypes.byref(msg))
                user32.DispatchMessageW(ctypes.byref(msg))
        finally:
            # 4. Clean unregistration
            for hk_id, hk in self._hotkeys.items():
                if hk.registered:
                    user32.UnregisterHotKey(None, hk_id)

    def stop(self):
        """Stops the message loop and unregisters all hotkeys."""
        self._running = False
        if self._thread_id:
            # Post WM_QUIT to break GetMessage
            user32.PostThreadMessageW(self._thread_id, 0x0012, 0, 0) # WM_QUIT = 0x0012

    def get_status_dict(self) -> Dict[str, str]:
        return dict(self._status_callbacks)

    def _format_hotkey(self, mod: int, vk: int) -> str:
        parts = []
        if mod & MOD_CONTROL:
            parts.append("Ctrl")
        if mod & MOD_ALT:
            parts.append("Alt")
        if mod & MOD_SHIFT:
            parts.append("Shift")
        if mod & MOD_WIN:
            parts.append("Win")
        
        # Format key name
        if vk == VK_SPACE:
            parts.append("Space")
        elif vk == VK_1:
            parts.append("1")
        elif vk == VK_2:
            parts.append("2")
        elif vk == VK_3:
            parts.append("3")
        elif vk == VK_S:
            parts.append("S")
        elif vk == VK_H:
            parts.append("H")
        elif vk == VK_T:
            parts.append("T")
        elif vk == VK_J:
            parts.append("J")
        elif vk == VK_K:
            parts.append("K")
        elif vk == VK_A:
            parts.append("A")
        elif vk == VK_C:
            parts.append("C")
        else:
            parts.append(f"VK_{vk}")
        return "+".join(parts)

def kernel32_get_thread_id() -> int:
    return ctypes.windll.kernel32.GetCurrentThreadId()
