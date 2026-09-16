from __future__ import annotations

import ctypes
import os
import sys
import winreg
from ctypes import wintypes

DWMWA_USE_IMMERSIVE_DARK_MODE = 20
DWMWA_SYSTEMBACKDROP_TYPE = 38
DWMSBT_MAINWINDOW = 2


def system_uses_dark_mode() -> bool:
    if sys.platform != "win32":
        return True
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize",
        ) as key:
            return winreg.QueryValueEx(key, "AppsUseLightTheme")[0] == 0
    except OSError:
        return True


def reduced_motion_enabled() -> bool:
    if sys.platform != "win32":
        return False
    try:
        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER, r"Control Panel\Desktop\WindowMetrics"
        ) as key:
            return winreg.QueryValueEx(key, "MinAnimate")[0] == "0"
    except OSError:
        return False


def apply_mica(window_id: int, dark: bool) -> bool:
    if sys.platform != "win32" or os.name != "nt":
        return False
    try:
        dwm = ctypes.WinDLL("dwmapi")
        hwnd = wintypes.HWND(window_id)
        dark_value = ctypes.c_int(1 if dark else 0)
        backdrop = ctypes.c_int(DWMSBT_MAINWINDOW)
        dark_result = dwm.DwmSetWindowAttribute(
            hwnd,
            DWMWA_USE_IMMERSIVE_DARK_MODE,
            ctypes.byref(dark_value),
            ctypes.sizeof(dark_value),
        )
        backdrop_result = dwm.DwmSetWindowAttribute(
            hwnd,
            DWMWA_SYSTEMBACKDROP_TYPE,
            ctypes.byref(backdrop),
            ctypes.sizeof(backdrop),
        )
        return dark_result == 0 and backdrop_result == 0
    except (AttributeError, OSError):
        return False

