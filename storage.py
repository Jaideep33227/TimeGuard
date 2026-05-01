"""
storage.py — JSON persistence for timer state, reasons, and daily stats.

Thread-safe. Handles corrupted/missing files gracefully.
"""

import json
import os
import threading
from datetime import datetime, date
from constants import (
    STATE_FILE, REASONS_FILE, STATS_FILE,
    XP_PER_MINUTE, XP_SESSION_BONUS, XP_STREAK_MULTIPLIER, DEFAULT_MODE
)


def _safe_load_json(filepath, default):
    """Load JSON from file, returning default on any error."""
    try:
        if os.path.exists(filepath):
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
    except (json.JSONDecodeError, IOError, ValueError):
        pass
    return default


def _safe_save_json(filepath, data):
    """Save JSON to file with error handling."""
    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except IOError as e:
        print(f"[storage] Error saving {filepath}: {e}")


# ═══════════════════════════════════════════════════════════════════════════════
# STATE MANAGER — Timer state persistence
# ═══════════════════════════════════════════════════════════════════════════════

class StateManager:
    """Manages timer state with atomic read/write operations."""

    _DEFAULTS = {
        "remaining_seconds": 0,
        "total_seconds": 0,
        "is_running": False,
        "is_paused": False,
        "mode": DEFAULT_MODE,
        "start_timestamp": None,
        "last_save_timestamp": None,
        "startup_enabled": False,
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._state = self._load()

    def _load(self) -> dict:
        data = _safe_load_json(STATE_FILE, None)
        if data and all(k in data for k in ["remaining_seconds", "total_seconds", "mode"]):
            # Merge with defaults to fill any missing keys
            merged = dict(self._DEFAULTS)
            merged.update(data)
            return merged
        return dict(self._DEFAULTS)

    def save(self):
        with self._lock:
            self._state["last_save_timestamp"] = datetime.now().isoformat()
            _safe_save_json(STATE_FILE, self._state)

    def get(self, key: str, default=None):
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value):
        with self._lock:
            self._state[key] = value

    def update(self, **kwargs):
        with self._lock:
            self._state.update(kwargs)

    def reset(self):
        """Reset timer state but preserve mode and startup preference."""
        with self._lock:
            mode = self._state.get("mode", DEFAULT_MODE)
            startup = self._state.get("startup_enabled", False)
            self._state = dict(self._DEFAULTS)
            self._state["mode"] = mode
            self._state["startup_enabled"] = startup
        self.save()

    def get_pending_session(self) -> tuple:
        """Atomically check for a pending session.
        Returns (remaining, total) or (0, 0) if none."""
        with self._lock:
            is_running = self._state.get("is_running", False)
            remaining = self._state.get("remaining_seconds", 0)
            total = self._state.get("total_seconds", 0)
        if is_running and remaining > 0:
            return (remaining, total)
        return (0, 0)

    def save_timer_state(self, remaining: int, total: int, is_running: bool, is_paused: bool):
        """Atomic save of all timer fields at once."""
        self.update(
            remaining_seconds=remaining,
            total_seconds=total,
            is_running=is_running,
            is_paused=is_paused,
        )
        self.save()


# ═══════════════════════════════════════════════════════════════════════════════
# REASONS LOG — Extra time request history
# ═══════════════════════════════════════════════════════════════════════════════

class ReasonsLog:
    """Logs reasons for extra time requests to a JSON file."""

    def __init__(self):
        self._lock = threading.Lock()

    def add(self, reason: str, minutes_added: int):
        entry = {
            "timestamp": datetime.now().isoformat(),
            "date": date.today().isoformat(),
            "reason": reason.strip(),
            "minutes_added": minutes_added,
        }
        with self._lock:
            entries = _safe_load_json(REASONS_FILE, [])
            if not isinstance(entries, list):
                entries = []
            entries.append(entry)
            _safe_save_json(REASONS_FILE, entries)

    def get_all(self) -> list:
        with self._lock:
            data = _safe_load_json(REASONS_FILE, [])
            return data if isinstance(data, list) else []

    def get_recent(self, count: int = 5) -> list:
        """Return the most recent N reasons."""
        all_reasons = self.get_all()
        return all_reasons[-count:] if all_reasons else []

    def get_today_count(self) -> int:
        """Return the number of times extra time was requested today."""
        today = date.today().isoformat()
        with self._lock:
            data = _safe_load_json(REASONS_FILE, [])
            if not isinstance(data, list): return 0
            return sum(1 for entry in data if entry.get("date") == today)


# ═══════════════════════════════════════════════════════════════════════════════
# STATS TRACKER — XP, streaks, daily focus data
# ═══════════════════════════════════════════════════════════════════════════════

class StatsTracker:
    """Tracks daily focus statistics, XP, and streaks."""

    _DEFAULTS = {
        "total_xp": 0,
        "days": {},
        "current_streak": 0,
        "longest_streak": 0,
        "last_active_date": None,
    }

    _DAY_DEFAULTS = {
        "focus_minutes": 0,
        "sessions_completed": 0,
        "xp_earned": 0,
    }

    def __init__(self):
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        data = _safe_load_json(STATS_FILE, None)
        if data and "total_xp" in data and "days" in data:
            merged = dict(self._DEFAULTS)
            merged.update(data)
            return merged
        return dict(self._DEFAULTS)

    def save(self):
        with self._lock:
            _safe_save_json(STATS_FILE, self._data)

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _ensure_today(self):
        today = self._today_key()
        if today not in self._data["days"]:
            self._data["days"][today] = dict(self._DAY_DEFAULTS)

    def record_focus_time(self, minutes: int):
        """Record focus minutes and award per-minute XP."""
        with self._lock:
            self._ensure_today()
            today = self._today_key()
            xp = minutes * XP_PER_MINUTE
            self._data["days"][today]["focus_minutes"] += minutes
            self._data["days"][today]["xp_earned"] += xp
            self._data["total_xp"] += xp
        self.save()

    def record_session_complete(self, focused_minutes: int) -> dict:
        """Record a completed session. Returns XP breakdown for the completion screen."""
        with self._lock:
            self._ensure_today()
            today = self._today_key()

            # Session completion bonus
            session_xp = XP_SESSION_BONUS
            self._data["days"][today]["sessions_completed"] += 1
            self._data["days"][today]["xp_earned"] += session_xp
            self._data["total_xp"] += session_xp

            # Streak update
            streak_xp = self._update_streak()

            total_xp_gained = session_xp + streak_xp

        self.save()

        return {
            "session_xp": session_xp,
            "streak_xp": streak_xp,
            "total_xp_gained": total_xp_gained,
            "focused_minutes": focused_minutes,
            "total_xp": self._data["total_xp"],
        }

    def _update_streak(self) -> int:
        """Update streak counter. Returns bonus XP from streak."""
        today = self._today_key()
        last = self._data.get("last_active_date")
        streak_xp = 0

        if last == today:
            return 0  # Already counted today

        if last:
            try:
                last_date = date.fromisoformat(last)
                diff = (date.today() - last_date).days
            except ValueError:
                diff = 999  # Corrupted date, reset streak

            if diff == 1:
                self._data["current_streak"] += 1
                streak_xp = XP_STREAK_MULTIPLIER * self._data["current_streak"]
                self._data["total_xp"] += streak_xp
                self._data["days"][today]["xp_earned"] += streak_xp
            elif diff > 1:
                self._data["current_streak"] = 1
        else:
            self._data["current_streak"] = 1

        self._data["last_active_date"] = today
        self._data["longest_streak"] = max(
            self._data["longest_streak"],
            self._data["current_streak"]
        )
        return streak_xp

    def get_today_stats(self) -> dict:
        with self._lock:
            self._ensure_today()
            return dict(self._data["days"][self._today_key()])

    def get_total_xp(self) -> int:
        with self._lock:
            return self._data.get("total_xp", 0)

    def get_streak(self) -> int:
        with self._lock:
            return self._data.get("current_streak", 0)

    def get_longest_streak(self) -> int:
        with self._lock:
            return self._data.get("longest_streak", 0)

    def get_all_time_stats(self) -> dict:
        with self._lock:
            total_minutes = 0
            total_sessions = 0
            for day_data in self._data["days"].values():
                total_minutes += day_data.get("focus_minutes", 0)
                total_sessions += day_data.get("sessions_completed", 0)
            return {
                "total_focus_minutes": total_minutes,
                "total_sessions": total_sessions,
                "total_xp": self._data.get("total_xp", 0),
                "current_streak": self._data.get("current_streak", 0),
                "longest_streak": self._data.get("longest_streak", 0),
                "days_active": len(self._data["days"]),
            }
