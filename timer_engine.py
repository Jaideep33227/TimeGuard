"""
timer_engine.py — Background countdown timer engine.

Uses wall-clock timing for accuracy. Auto-saves state periodically.
All callbacks are fired from the background thread — UI must use .after()
to schedule updates on the main thread.
"""

import threading
import time
from constants import AUTO_SAVE_INTERVAL


class TimerEngine:
    """Accurate, crash-resilient background countdown timer."""

    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

    def __init__(self, state_manager, stats_tracker):
        self._state_manager = state_manager
        self._stats_tracker = stats_tracker

        self._total_seconds = 0
        self._remaining_seconds = 0.0  # Float for wall-clock precision
        self._state = self.IDLE

        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()
        self._lock = threading.Lock()

        self._last_tick_time = None
        self._accumulated_focus_seconds = 0.0

        # Callbacks (set by the app controller)
        self.on_tick = None
        self.on_complete = None
        self.on_state_change = None

    # ─── Properties ───────────────────────────────────────────────────

    @property
    def state(self) -> str:
        return self._state

    @property
    def remaining(self) -> int:
        """Remaining seconds as an integer (for display)."""
        with self._lock:
            return max(0, int(self._remaining_seconds))

    @property
    def total(self) -> int:
        return self._total_seconds

    @property
    def progress(self) -> float:
        """Elapsed progress from 0.0 to 1.0."""
        with self._lock:
            if self._total_seconds <= 0:
                return 0.0
            elapsed = self._total_seconds - self._remaining_seconds
            return min(1.0, max(0.0, elapsed / self._total_seconds))

    @property
    def focused_minutes(self) -> int:
        """Total minutes focused in the current/last session."""
        with self._lock:
            total_focused = self._total_seconds - self._remaining_seconds
            return max(0, int(total_focused / 60))

    # ─── Controls ─────────────────────────────────────────────────────

    def start(self, seconds: int):
        """Start a new countdown."""
        self.stop()

        with self._lock:
            self._total_seconds = seconds
            self._remaining_seconds = float(seconds)
            self._accumulated_focus_seconds = 0.0

        self._stop_event.clear()
        self._pause_event.set()
        self._set_state(self.RUNNING)
        self._save_state()

        self._thread = threading.Thread(target=self._run, daemon=True, name="TimerThread")
        self._thread.start()

    def resume_from_state(self, remaining: int, total: int):
        """Resume from a previously saved state."""
        if remaining <= 0:
            return

        with self._lock:
            self._total_seconds = total
            self._remaining_seconds = float(remaining)
            self._accumulated_focus_seconds = 0.0

        self._stop_event.clear()
        self._pause_event.set()
        self._set_state(self.RUNNING)

        self._thread = threading.Thread(target=self._run, daemon=True, name="TimerThread")
        self._thread.start()

    def pause(self):
        if self._state == self.RUNNING:
            self._pause_event.clear()
            self._set_state(self.PAUSED)
            self._flush_focus_time()
            self._save_state()

    def unpause(self):
        if self._state == self.PAUSED:
            with self._lock:
                self._last_tick_time = time.monotonic()
            self._pause_event.set()
            self._set_state(self.RUNNING)
            self._save_state()

    def stop(self):
        """Stop the timer and clean up."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._pause_event.set()
            self._thread.join(timeout=2)

        self._flush_focus_time()

        with self._lock:
            self._remaining_seconds = 0
            self._total_seconds = 0

        self._set_state(self.IDLE)
        self._state_manager.reset()

    def add_time(self, seconds: int):
        """Add extra time to the running countdown."""
        with self._lock:
            self._remaining_seconds += seconds
            self._total_seconds += seconds
        self._save_state()

        # If we already completed, restart the loop
        if self._state == self.COMPLETED:
            self._stop_event.clear()
            self._pause_event.set()
            self._set_state(self.RUNNING)
            self._thread = threading.Thread(target=self._run, daemon=True, name="TimerThread")
            self._thread.start()

    def save_current_state(self):
        """Public method for saving state (e.g. on app close)."""
        self._save_state()

    # ─── Background Loop ──────────────────────────────────────────────

    def _run(self):
        """Main timer loop on background thread."""
        with self._lock:
            self._last_tick_time = time.monotonic()
        last_save_time = time.monotonic()

        while not self._stop_event.is_set():
            # Block while paused
            self._pause_event.wait()
            if self._stop_event.is_set():
                break

            # Sleep ~1 second in small increments for responsiveness
            for _ in range(10):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)
            if self._stop_event.is_set():
                break

            # Wall-clock elapsed calculation
            now = time.monotonic()
            with self._lock:
                elapsed = now - self._last_tick_time
                self._last_tick_time = now
                self._remaining_seconds -= elapsed
                self._accumulated_focus_seconds += elapsed
                if self._remaining_seconds <= 0:
                    self._remaining_seconds = 0
                remaining_snapshot = int(self._remaining_seconds)

            # Fire tick callback
            if self.on_tick:
                try:
                    self.on_tick(remaining_snapshot)
                except Exception as e:
                    print(f"[Timer] tick error: {e}")

            # Check completion
            if remaining_snapshot <= 0:
                self._flush_focus_time()
                focused = self.focused_minutes
                xp_info = self._stats_tracker.record_session_complete(focused)
                self._set_state(self.COMPLETED)
                self._save_state()
                if self.on_complete:
                    try:
                        self.on_complete(xp_info)
                    except Exception as e:
                        print(f"[Timer] complete error: {e}")
                return

            # Periodic auto-save
            if now - last_save_time >= AUTO_SAVE_INTERVAL:
                self._save_state()
                self._flush_focus_time()
                last_save_time = now

    # ─── Internal Helpers ─────────────────────────────────────────────

    def _set_state(self, new_state: str):
        self._state = new_state
        if self.on_state_change:
            try:
                self.on_state_change(new_state)
            except Exception as e:
                print(f"[Timer] state_change error: {e}")

    def _save_state(self):
        self._state_manager.save_timer_state(
            remaining=self.remaining,
            total=self._total_seconds,
            is_running=(self._state == self.RUNNING),
            is_paused=(self._state == self.PAUSED),
        )

    def _flush_focus_time(self):
        """Convert accumulated seconds into recorded focus minutes."""
        with self._lock:
            minutes = int(self._accumulated_focus_seconds // 60)
            if minutes > 0:
                self._accumulated_focus_seconds -= minutes * 60
        if minutes > 0:
            self._stats_tracker.record_focus_time(minutes)
