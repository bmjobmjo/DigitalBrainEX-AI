"""
Win32 platform helpers for DigitalBrainEX AI.
Handles AppUserModelID registration and native taskbar/window icon binding.
"""
import sys
import os

APP_USER_MODEL_ID = "DigitalBrain.DigitalBrainEX.AI.2.0"


def setup_windows_app_id():
    """Tells Windows that this process is a standalone application, not generic python.exe."""
    if sys.platform != "win32":
        return
    import ctypes
    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_USER_MODEL_ID)
    except Exception as e:
        print(f"Could not set AppUserModelID: {e}")


def apply_native_window_icon(hwnd: int, icon_path: str):
    """Binds native Win32 icon handles to window HWND for taskbar and alt-tab display."""
    if sys.platform != "win32" or not os.path.exists(icon_path):
        return
    import ctypes

    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040
    WM_SETICON = 0x0080
    ICON_SMALL = 0
    ICON_BIG = 1

    try:
        h_icon_big = ctypes.windll.user32.LoadImageW(
            0, icon_path, IMAGE_ICON, 0, 0, LR_LOADFROMFILE | LR_DEFAULTSIZE
        )
        h_icon_small = ctypes.windll.user32.LoadImageW(
            0, icon_path, IMAGE_ICON, 16, 16, LR_LOADFROMFILE
        )
        if h_icon_big:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_BIG, h_icon_big)
        if h_icon_small:
            ctypes.windll.user32.SendMessageW(hwnd, WM_SETICON, ICON_SMALL, h_icon_small)
    except Exception as e:
        print(f"Could not apply native window icon: {e}")
