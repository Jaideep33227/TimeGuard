"""
startup.py — Windows startup registry management.

Manages adding/removing the app from the Windows startup registry
(HKCU\\Software\\Microsoft\\Windows\\CurrentVersion\\Run).
No admin privileges required.
"""

import sys
import os
import winreg

from constants import APP_NAME


def _get_app_command() -> str:
    """Get the command to launch this app."""
    if getattr(sys, 'frozen', False):
        # Running as compiled exe (e.g., PyInstaller)
        return f'"{sys.executable}"'
    else:
        # Running as Python script
        script = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "main.py"
        ))
        return f'"{sys.executable}" "{script}"'


def enable_startup() -> bool:
    """
    Add the app to Windows startup.
    Returns True on success, False on failure.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, APP_NAME, 0, winreg.REG_SZ, _get_app_command())
        winreg.CloseKey(key)
        return True
    except Exception as e:
        print(f"[startup] Failed to enable startup: {e}")
        return False


def disable_startup() -> bool:
    """
    Remove the app from Windows startup.
    Returns True on success, False on failure.
    """
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_SET_VALUE
        )
        winreg.DeleteValue(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        # Entry doesn't exist — that's fine
        return True
    except Exception as e:
        print(f"[startup] Failed to disable startup: {e}")
        return False


def is_startup_enabled() -> bool:
    """Check if the app is currently set to start with Windows."""
    try:
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Run",
            0,
            winreg.KEY_READ
        )
        winreg.QueryValueEx(key, APP_NAME)
        winreg.CloseKey(key)
        return True
    except FileNotFoundError:
        return False
    except Exception:
        return False
