"""
main.py — Entry point for FocusLock.
Handles single-instance check and launches the app.
"""

import sys
import os
import msvcrt

# Add the script directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from constants import LOCK_FILE, DATA_DIR


def acquire_lock():
    """Ensure only one instance of FocusLock runs at a time."""
    os.makedirs(DATA_DIR, exist_ok=True)
    try:
        lock_fd = open(LOCK_FILE, "w")
        msvcrt.locking(lock_fd.fileno(), msvcrt.LK_NBLCK, 1)
        lock_fd.write(str(os.getpid()))
        lock_fd.flush()
        return lock_fd
    except (IOError, OSError):
        print("[FocusLock] Another instance is already running. Exiting.")
        sys.exit(0)


def main():
    lock_fd = acquire_lock()

    try:
        from app import FocusLockApp
        app = FocusLockApp()
        app.mainloop()
    except Exception as e:
        print(f"[FocusLock] Fatal error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # Release lock
        try:
            msvcrt.locking(lock_fd.fileno(), msvcrt.LK_UNLCK, 1)
            lock_fd.close()
            if os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except Exception:
            pass


if __name__ == "__main__":
    main()
