"""
timer_engine.py — Background timer engine with callbacks.

Runs the countdown on a separate thread and fires callbacks for:
  - on_tick(remaining_seconds)   — called every second
  - on_complete()                — called when timer reaches 0
  - on_state_change(state_str)   — called when timer state changes

Thread-safe. Auto-saves state periodically via StateManager.
"""

import threading
import time
from constants import AUTO_SAVE_INTERVAL


class TimerEngine:
    """
    A background countdown timer that is accurate and crash-resilient.
    Uses wall-clock comparison (not sleep-based counting) for accuracy.
    """

    # Timer states
    IDLE = "idle"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"

    def __init__(self, state_manager, stats_tracker):
        self._state_manager = state_manager
        self._stats_tracker = stats_tracker

        # Timer values
        self._total_seconds = 0
        self._remaining_seconds = 0
        self._state = self.IDLE

        # Thread control
        self._thread = None
        self._stop_event = threading.Event()
        self._pause_event = threading.Event()
        self._pause_event.set()  # Not paused initially
        self._lock = threading.Lock()

        # Wall-clock tracking for accuracy
        self._last_tick_time = None
        self._accumulated_focus_seconds = 0  # For XP tracking

        # Callbacks (set by the UI)
        self.on_tick = None          # Called every second with remaining_seconds
        self.on_complete = None      # Called when timer hits 0
        self.on_state_change = None  # Called with state string

    @property
    def state(self) -> str:
        return self._state

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self._remaining_seconds)

    @property
    def total(self) -> int:
        return self._total_seconds

    @property
    def progress(self) -> float:
        """Returns progress as 0.0 to 1.0 (1.0 = complete)."""
        if self._total_seconds <= 0:
            return 0.0
        elapsed = self._total_seconds - self._remaining_seconds
        return min(1.0, max(0.0, elapsed / self._total_seconds))

    def start(self, seconds: int):
        """Start a new countdown for the given number of seconds."""
        self.stop()  # Stop any existing timer

        with self._lock:
            self._total_seconds = seconds
            self._remaining_seconds = seconds
            self._accumulated_focus_seconds = 0

        self._stop_event.clear()
        self._pause_event.set()
        self._set_state(self.RUNNING)

        # Save initial state
        self._save_state()

        # Start background thread
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def resume_from_state(self, remaining: int, total: int):
        """Resume a timer from saved state (after crash/restart)."""
        if remaining <= 0:
            return

        with self._lock:
            self._total_seconds = total
            self._remaining_seconds = remaining
            self._accumulated_focus_seconds = 0

        self._stop_event.clear()
        self._pause_event.set()
        self._set_state(self.RUNNING)

        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def pause(self):
        """Pause the timer."""
        if self._state == self.RUNNING:
            self._pause_event.clear()
            self._set_state(self.PAUSED)
            self._record_focus_time()
            self._save_state()

    def unpause(self):
        """Resume from pause."""
        if self._state == self.PAUSED:
            self._pause_event.set()
            self._last_tick_time = time.monotonic()
            self._set_state(self.RUNNING)
            self._save_state()

    def stop(self):
        """Stop the timer completely."""
        if self._thread and self._thread.is_alive():
            self._stop_event.set()
            self._pause_event.set()  # Unblock if paused
            self._thread.join(timeout=2)

        self._record_focus_time()
        self._set_state(self.IDLE)

        with self._lock:
            self._remaining_seconds = 0
            self._total_seconds = 0

        # Clear saved state
        self._state_manager.reset()

    def add_time(self, seconds: int):
        """Add extra time to the current countdown."""
        with self._lock:
            self._remaining_seconds += seconds
            self._total_seconds += seconds
        self._save_state()

        # If completed, restart the timer loop
        if self._state == self.COMPLETED:
            self._stop_event.clear()
            self._pause_event.set()
            self._set_state(self.RUNNING)
            self._thread = threading.Thread(target=self._run, daemon=True)
            self._thread.start()

    def _run(self):
        """Main timer loop running on background thread."""
        self._last_tick_time = time.monotonic()
        last_save_time = time.monotonic()

        while not self._stop_event.is_set():
            # Wait if paused
            self._pause_event.wait()

            if self._stop_event.is_set():
                break

            # Sleep for ~1 second (in small increments for responsiveness)
            for _ in range(10):
                if self._stop_event.is_set():
                    return
                time.sleep(0.1)

            if self._stop_event.is_set():
                break

            # Calculate elapsed using wall clock
            now = time.monotonic()
            elapsed = now - self._last_tick_time
            self._last_tick_time = now

            with self._lock:
                self._remaining_seconds -= elapsed
                self._accumulated_focus_seconds += elapsed

                if self._remaining_seconds <= 0:
                    self._remaining_seconds = 0

            # Fire tick callback
            if self.on_tick:
                try:
                    self.on_tick(self.remaining)
                except Exception as e:
                    print(f"[TimerEngine] on_tick error: {e}")

            # Check completion
            if self.remaining <= 0:
                self._record_focus_time()
                self._stats_tracker.record_session_complete()
                self._set_state(self.COMPLETED)
                self._save_state()
                if self.on_complete:
                    try:
                        self.on_complete()
                    except Exception as e:
                        print(f"[TimerEngine] on_complete error: {e}")
                return

            # Auto-save periodically
            if now - last_save_time >= AUTO_SAVE_INTERVAL:
                self._save_state()
                self._record_focus_time()
                last_save_time = now

    def _set_state(self, new_state: str):
        """Update state and fire callback."""
        self._state = new_state
        if self.on_state_change:
            try:
                self.on_state_change(new_state)
            except Exception as e:
                print(f"[TimerEngine] on_state_change error: {e}")

    def _save_state(self):
        """Persist current timer state to disk."""
        self._state_manager.update(
            remaining_seconds=int(self.remaining),
            total_seconds=self._total_seconds,
            is_running=self._state == self.RUNNING,
            is_paused=self._state == self.PAUSED,
        )
        self._state_manager.save()

    def _record_focus_time(self):
        """Record accumulated focus time for XP."""
        with self._lock:
            minutes = int(self._accumulated_focus_seconds // 60)
            if minutes > 0:
                self._stats_tracker.record_focus_time(minutes)
                self._accumulated_focus_seconds -= minutes * 60
