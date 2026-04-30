"""
storage.py — JSON persistence for timer state, extra-time reasons, and daily stats.

All data is stored locally in the /data directory as JSON files.
Thread-safe via threading.Lock for concurrent access from timer threads.
"""

import json
import os
import threading
from datetime import datetime, date
from constants import (
    STATE_FILE, REASONS_FILE, STATS_FILE,
    XP_PER_MINUTE, XP_SESSION_BONUS, XP_STREAK_MULTIPLIER, DEFAULT_MODE
)


class StateManager:
    """
    Manages the timer state: remaining time, running status, mode, and timestamps.
    Auto-saves periodically so crashes don't lose progress.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._state = self._load()

    def _load(self) -> dict:
        """Load state from disk, or return defaults."""
        try:
            if os.path.exists(STATE_FILE):
                with open(STATE_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    # Validate required keys exist
                    required = ["remaining_seconds", "total_seconds", "is_running", "mode"]
                    if all(k in data for k in required):
                        return data
        except (json.JSONDecodeError, IOError):
            pass
        return self._defaults()

    def _defaults(self) -> dict:
        return {
            "remaining_seconds": 0,
            "total_seconds": 0,
            "is_running": False,
            "is_paused": False,
            "mode": DEFAULT_MODE,
            "start_timestamp": None,
            "last_save_timestamp": None,
            "startup_enabled": False,
        }

    def save(self):
        """Persist current state to disk."""
        with self._lock:
            self._state["last_save_timestamp"] = datetime.now().isoformat()
            try:
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._state, f, indent=2)
            except IOError as e:
                print(f"[StateManager] Error saving state: {e}")

    def get(self, key: str, default=None):
        """Thread-safe getter."""
        with self._lock:
            return self._state.get(key, default)

    def set(self, key: str, value):
        """Thread-safe setter."""
        with self._lock:
            self._state[key] = value

    def update(self, **kwargs):
        """Thread-safe batch update."""
        with self._lock:
            self._state.update(kwargs)

    def reset(self):
        """Reset state to defaults (keeps mode and startup preference)."""
        mode = self.get("mode", DEFAULT_MODE)
        startup = self.get("startup_enabled", False)
        with self._lock:
            self._state = self._defaults()
            self._state["mode"] = mode
            self._state["startup_enabled"] = startup
        self.save()

    def has_pending_session(self) -> bool:
        """Check if there's a timer that was running before a crash/restart."""
        return (
            self.get("is_running", False)
            and self.get("remaining_seconds", 0) > 0
        )

    @property
    def state(self) -> dict:
        with self._lock:
            return dict(self._state)


class ReasonsLog:
    """
    Logs reasons for extra time requests to a JSON file.
    Each entry includes: timestamp, reason text, minutes added.
    """

    def __init__(self):
        self._lock = threading.Lock()

    def add(self, reason: str, minutes_added: int):
        """Add a new reason entry."""
        entry = {
            "timestamp": datetime.now().isoformat(),
            "reason": reason.strip(),
            "minutes_added": minutes_added,
        }
        with self._lock:
            entries = self._load()
            entries.append(entry)
            self._save(entries)

    def get_all(self) -> list:
        """Return all logged reasons."""
        with self._lock:
            return self._load()

    def get_today(self) -> list:
        """Return reasons logged today."""
        today = date.today().isoformat()
        return [
            e for e in self.get_all()
            if e.get("timestamp", "").startswith(today)
        ]

    def _load(self) -> list:
        try:
            if os.path.exists(REASONS_FILE):
                with open(REASONS_FILE, "r", encoding="utf-8") as f:
                    return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
        return []

    def _save(self, entries: list):
        try:
            with open(REASONS_FILE, "w", encoding="utf-8") as f:
                json.dump(entries, f, indent=2)
        except IOError as e:
            print(f"[ReasonsLog] Error saving: {e}")


class StatsTracker:
    """
    Tracks daily focus statistics, XP, streaks, and session history.
    Data is keyed by date for daily breakdown.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._data = self._load()

    def _load(self) -> dict:
        try:
            if os.path.exists(STATS_FILE):
                with open(STATS_FILE, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    if "total_xp" in data and "days" in data:
                        return data
        except (json.JSONDecodeError, IOError):
            pass
        return {
            "total_xp": 0,
            "days": {},
            "current_streak": 0,
            "longest_streak": 0,
            "last_active_date": None,
        }

    def save(self):
        """Persist stats to disk."""
        with self._lock:
            try:
                with open(STATS_FILE, "w", encoding="utf-8") as f:
                    json.dump(self._data, f, indent=2)
            except IOError as e:
                print(f"[StatsTracker] Error saving: {e}")

    def _today_key(self) -> str:
        return date.today().isoformat()

    def _ensure_today(self):
        """Ensure today's entry exists."""
        today = self._today_key()
        if today not in self._data["days"]:
            self._data["days"][today] = {
                "focus_minutes": 0,
                "sessions_completed": 0,
                "xp_earned": 0,
            }

    def record_focus_time(self, minutes: int):
        """Record minutes of focus time and award XP."""
        with self._lock:
            self._ensure_today()
            today = self._today_key()
            xp = minutes * XP_PER_MINUTE
            self._data["days"][today]["focus_minutes"] += minutes
            self._data["days"][today]["xp_earned"] += xp
            self._data["total_xp"] += xp
        self.save()

    def record_session_complete(self):
        """Record a completed session and award bonus XP."""
        with self._lock:
            self._ensure_today()
            today = self._today_key()
            self._data["days"][today]["sessions_completed"] += 1
            self._data["days"][today]["xp_earned"] += XP_SESSION_BONUS
            self._data["total_xp"] += XP_SESSION_BONUS
            self._update_streak()
        self.save()

    def _update_streak(self):
        """Update the daily streak counter."""
        today = self._today_key()
        last = self._data.get("last_active_date")

        if last == today:
            return  # Already counted today

        if last:
            last_date = date.fromisoformat(last)
            today_date = date.today()
            diff = (today_date - last_date).days

            if diff == 1:
                # Consecutive day
                self._data["current_streak"] += 1
                # Streak bonus XP
                streak_xp = XP_STREAK_MULTIPLIER * self._data["current_streak"]
                self._data["total_xp"] += streak_xp
                self._data["days"][today]["xp_earned"] += streak_xp
            elif diff > 1:
                # Streak broken
                self._data["current_streak"] = 1
        else:
            self._data["current_streak"] = 1

        self._data["last_active_date"] = today
        self._data["longest_streak"] = max(
            self._data["longest_streak"],
            self._data["current_streak"]
        )

    def get_today_stats(self) -> dict:
        """Get today's stats."""
        with self._lock:
            self._ensure_today()
            today = self._today_key()
            return dict(self._data["days"][today])

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
        """Aggregate stats across all days."""
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
