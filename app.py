"""
app.py — Main application UI and controller for FocusLock.
Wires together timer engine, storage, lock screen, and UI.
"""

import customtkinter as ctk
import threading
from constants import (
    COLORS, FONTS, WINDOW_TITLE, WINDOW_SIZE,
    MODE_TEST, MODE_REAL, DEFAULT_MODE,
    MIN_TIMER_SECONDS, MAX_TIMER_SECONDS, get_level_info
)
from storage import StateManager, ReasonsLog, StatsTracker
from timer_engine import TimerEngine
from lock_screen import LockScreen
import startup as startup_mgr


class FocusLockApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # ─── App config ──────────────────────────────────────────────
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(480, 700)
        self.configure(fg_color=COLORS["bg_primary"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # ─── Managers ────────────────────────────────────────────────
        self.state_mgr = StateManager()
        self.reasons_log = ReasonsLog()
        self.stats = StatsTracker()
        self.timer = TimerEngine(self.state_mgr, self.stats)
        self.timer.on_tick = self._on_tick
        self.timer.on_complete = self._on_timer_complete
        self.timer.on_state_change = self._on_state_change

        self._mode = self.state_mgr.get("mode", DEFAULT_MODE)
        self._lock_screen = None

        # ─── Build UI ───────────────────────────────────────────────
        self._build_ui()
        self._update_stats_display()

        # ─── Check for pending session ───────────────────────────────
        if self.state_mgr.has_pending_session():
            remaining = self.state_mgr.get("remaining_seconds", 0)
            total = self.state_mgr.get("total_seconds", 0)
            if remaining > 0:
                self.after(500, lambda: self._offer_resume(remaining, total))

    # ═══════════════════════════════════════════════════════════════════
    # UI BUILDING
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Scrollable main frame
        main = ctk.CTkScrollableFrame(self, fg_color="transparent")
        main.pack(fill="both", expand=True, padx=15, pady=10)

        # Title bar
        header = ctk.CTkFrame(main, fg_color="transparent")
        header.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(header, text="🎯 FocusLock", font=FONTS["title"],
                     text_color=COLORS["accent"]).pack(side="left")

        # ─── Countdown Display ────────────────────────────────────────
        cd_card = self._card(main)
        self._timer_label = ctk.CTkLabel(cd_card, text="00:00:00",
                                         font=FONTS["timer_large"],
                                         text_color=COLORS["text_primary"])
        self._timer_label.pack(pady=(15, 2))

        self._timer_status = ctk.CTkLabel(cd_card, text="Ready to focus",
                                          font=FONTS["timer_label"],
                                          text_color=COLORS["text_secondary"])
        self._timer_status.pack(pady=(0, 8))

        self._progress = ctk.CTkProgressBar(cd_card, width=380, height=10,
                                            fg_color=COLORS["progress_bg"],
                                            progress_color=COLORS["progress_fill"],
                                            corner_radius=5)
        self._progress.set(0)
        self._progress.pack(pady=(0, 12))

        # Control buttons
        btn_row = ctk.CTkFrame(cd_card, fg_color="transparent")
        btn_row.pack(pady=(0, 15))

        self._start_btn = ctk.CTkButton(btn_row, text="▶ Start", width=110, height=38,
                                        font=FONTS["button"], fg_color=COLORS["success"],
                                        hover_color=COLORS["success_hover"],
                                        text_color=COLORS["bg_primary"],
                                        corner_radius=10, command=self._start_timer)
        self._start_btn.pack(side="left", padx=4)

        self._pause_btn = ctk.CTkButton(btn_row, text="⏸ Pause", width=110, height=38,
                                        font=FONTS["button"], fg_color=COLORS["warning"],
                                        hover_color=COLORS["accent_hover"],
                                        text_color=COLORS["bg_primary"],
                                        corner_radius=10, command=self._toggle_pause,
                                        state="disabled")
        self._pause_btn.pack(side="left", padx=4)

        self._stop_btn = ctk.CTkButton(btn_row, text="⏹ Stop", width=110, height=38,
                                       font=FONTS["button"], fg_color=COLORS["danger"],
                                       hover_color=COLORS["accent_hover"],
                                       text_color=COLORS["text_primary"],
                                       corner_radius=10, command=self._stop_timer,
                                       state="disabled")
        self._stop_btn.pack(side="left", padx=4)

        # ─── Timer Setup ─────────────────────────────────────────────
        setup_card = self._card(main)
        ctk.CTkLabel(setup_card, text="⏱ Set Timer", font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(12, 8))

        time_row = ctk.CTkFrame(setup_card, fg_color="transparent")
        time_row.pack(fill="x", padx=15, pady=(0, 12))

        ctk.CTkLabel(time_row, text="Hours:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._hours_var = ctk.StringVar(value="1")
        ctk.CTkEntry(time_row, textvariable=self._hours_var, width=60,
                     font=FONTS["body"], fg_color=COLORS["bg_input"],
                     text_color=COLORS["text_primary"],
                     border_color=COLORS["border"], justify="center"
                     ).pack(side="left", padx=(5, 15))

        ctk.CTkLabel(time_row, text="Minutes:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._mins_var = ctk.StringVar(value="0")
        ctk.CTkEntry(time_row, textvariable=self._mins_var, width=60,
                     font=FONTS["body"], fg_color=COLORS["bg_input"],
                     text_color=COLORS["text_primary"],
                     border_color=COLORS["border"], justify="center"
                     ).pack(side="left", padx=(5, 15))

        # Quick presets
        preset_row = ctk.CTkFrame(setup_card, fg_color="transparent")
        preset_row.pack(fill="x", padx=15, pady=(0, 12))
        for label, h, m in [("25m", 0, 25), ("45m", 0, 45), ("1h", 1, 0), ("2h", 2, 0), ("3h", 3, 0)]:
            ctk.CTkButton(preset_row, text=label, width=58, height=30,
                          font=FONTS["body_small"], fg_color=COLORS["secondary"],
                          hover_color=COLORS["accent"], text_color=COLORS["text_primary"],
                          corner_radius=8,
                          command=lambda hh=h, mm=m: self._set_preset(hh, mm)
                          ).pack(side="left", padx=3)

        # ─── Add Extra Time ───────────────────────────────────────────
        add_card = self._card(main)
        ctk.CTkLabel(add_card, text="➕ Add Extra Time", font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(12, 8))

        ar = ctk.CTkFrame(add_card, fg_color="transparent")
        ar.pack(fill="x", padx=15)
        ctk.CTkLabel(ar, text="Minutes:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._add_min_var = ctk.StringVar(value="15")
        ctk.CTkEntry(ar, textvariable=self._add_min_var, width=60, font=FONTS["body"],
                     fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
                     border_color=COLORS["border"], justify="center"
                     ).pack(side="left", padx=(5, 0))

        ctk.CTkLabel(add_card, text="Reason:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=15, pady=(8, 2))
        self._add_reason_var = ctk.StringVar()
        ctk.CTkEntry(add_card, textvariable=self._add_reason_var,
                     placeholder_text="Why do you need more time?",
                     font=FONTS["body"], fg_color=COLORS["bg_input"],
                     text_color=COLORS["text_primary"],
                     border_color=COLORS["border"]).pack(fill="x", padx=15)

        self._add_status = ctk.CTkLabel(add_card, text="", font=FONTS["body_small"],
                                        text_color=COLORS["success"])
        self._add_status.pack(pady=2)

        ctk.CTkButton(add_card, text="Request Extra Time", font=FONTS["button"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["accent"],
                      text_color=COLORS["text_primary"], corner_radius=10, height=36,
                      command=self._add_extra_time).pack(fill="x", padx=15, pady=(4, 12))

        # ─── Stats ────────────────────────────────────────────────────
        stats_card = self._card(main)
        ctk.CTkLabel(stats_card, text="📊 Today's Stats", font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(12, 8))

        sg = ctk.CTkFrame(stats_card, fg_color="transparent")
        sg.pack(fill="x", padx=15, pady=(0, 5))
        sg.columnconfigure((0, 1), weight=1)

        self._stat_focus = self._stat_box(sg, "Focus Time", "0m", 0, 0)
        self._stat_sessions = self._stat_box(sg, "Sessions", "0", 0, 1)
        self._stat_xp = self._stat_box(sg, "XP Earned", "0", 1, 0)
        self._stat_streak = self._stat_box(sg, "Streak", "0 days", 1, 1)

        # Level display
        self._level_label = ctk.CTkLabel(stats_card, text="🌱 Level 1 — Beginner",
                                         font=FONTS["subheading"],
                                         text_color=COLORS["accent"])
        self._level_label.pack(pady=(2, 4))

        self._xp_progress = ctk.CTkProgressBar(stats_card, width=340, height=8,
                                                fg_color=COLORS["progress_bg"],
                                                progress_color=COLORS["success"],
                                                corner_radius=4)
        self._xp_progress.set(0)
        self._xp_progress.pack(pady=(0, 12))

        # ─── Settings ────────────────────────────────────────────────
        set_card = self._card(main)
        ctk.CTkLabel(set_card, text="⚙ Settings", font=FONTS["heading"],
                     text_color=COLORS["text_primary"]).pack(anchor="w", padx=15, pady=(12, 8))

        # Mode selector
        mode_row = ctk.CTkFrame(set_card, fg_color="transparent")
        mode_row.pack(fill="x", padx=15, pady=(0, 8))
        ctk.CTkLabel(mode_row, text="Mode:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left")
        self._mode_var = ctk.StringVar(value="🧪 Test Mode" if self._mode == MODE_TEST else "🔒 Real Mode")
        ctk.CTkOptionMenu(mode_row, values=["🧪 Test Mode", "🔒 Real Mode"],
                          variable=self._mode_var, font=FONTS["body"],
                          fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
                          button_color=COLORS["secondary"],
                          button_hover_color=COLORS["accent"],
                          dropdown_fg_color=COLORS["bg_card"],
                          dropdown_text_color=COLORS["text_primary"],
                          command=self._on_mode_change
                          ).pack(side="left", padx=(10, 0))

        # Startup toggle
        self._startup_var = ctk.BooleanVar(value=startup_mgr.is_startup_enabled())
        ctk.CTkCheckBox(set_card, text="Start with Windows", font=FONTS["body"],
                        text_color=COLORS["text_secondary"],
                        fg_color=COLORS["accent"], hover_color=COLORS["accent_hover"],
                        variable=self._startup_var,
                        command=self._toggle_startup).pack(anchor="w", padx=15, pady=(0, 4))

        # Status bar
        mode_txt = "🧪 Test Mode — Lock screen is safe & reversible" if self._mode == MODE_TEST else "🔒 Real Mode"
        self._footer = ctk.CTkLabel(set_card, text=mode_txt, font=FONTS["body_small"],
                                    text_color=COLORS["text_dim"])
        self._footer.pack(pady=(0, 12))

    # ═══════════════════════════════════════════════════════════════════
    # HELPERS
    # ═══════════════════════════════════════════════════════════════════

    def _card(self, parent) -> ctk.CTkFrame:
        c = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"], corner_radius=16,
                         border_width=1, border_color=COLORS["border"])
        c.pack(fill="x", pady=6)
        return c

    def _stat_box(self, parent, label, value, row, col):
        f = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=10)
        f.grid(row=row, column=col, padx=4, pady=4, sticky="nsew")
        vl = ctk.CTkLabel(f, text=value, font=FONTS["stat_value"],
                          text_color=COLORS["text_primary"])
        vl.pack(pady=(8, 0))
        ctk.CTkLabel(f, text=label, font=FONTS["stat_label"],
                     text_color=COLORS["text_secondary"]).pack(pady=(0, 8))
        return vl

    @staticmethod
    def _fmt(seconds: int) -> str:
        s = max(0, int(seconds))
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

    # ═══════════════════════════════════════════════════════════════════
    # TIMER ACTIONS
    # ═══════════════════════════════════════════════════════════════════

    def _set_preset(self, h, m):
        self._hours_var.set(str(h))
        self._mins_var.set(str(m))

    def _start_timer(self):
        try:
            h = int(self._hours_var.get() or 0)
            m = int(self._mins_var.get() or 0)
        except ValueError:
            self._timer_status.configure(text="⚠ Enter valid numbers", text_color=COLORS["danger"])
            return
        total = h * 3600 + m * 60
        if total < MIN_TIMER_SECONDS:
            self._timer_status.configure(text="⚠ Minimum 1 minute", text_color=COLORS["danger"])
            return
        if total > MAX_TIMER_SECONDS:
            self._timer_status.configure(text="⚠ Maximum 12 hours", text_color=COLORS["danger"])
            return
        self.timer.start(total)

    def _toggle_pause(self):
        if self.timer.state == TimerEngine.RUNNING:
            self.timer.pause()
        elif self.timer.state == TimerEngine.PAUSED:
            self.timer.unpause()

    def _stop_timer(self):
        self.timer.stop()
        self._timer_label.configure(text="00:00:00")
        self._progress.set(0)
        self._update_stats_display()

    def _add_extra_time(self):
        if self.timer.state not in (TimerEngine.RUNNING, TimerEngine.PAUSED, TimerEngine.COMPLETED):
            self._add_status.configure(text="⚠ No active timer", text_color=COLORS["danger"])
            return
        try:
            mins = int(self._add_min_var.get())
            if mins <= 0 or mins > 480:
                raise ValueError
        except ValueError:
            self._add_status.configure(text="⚠ Enter valid minutes (1-480)", text_color=COLORS["danger"])
            return
        reason = self._add_reason_var.get().strip()
        if not reason:
            self._add_status.configure(text="⚠ Please enter a reason", text_color=COLORS["danger"])
            return

        self._handle_add_time(mins, reason)
        self._add_reason_var.set("")
        self._add_status.configure(text=f"✅ Added {mins} min!", text_color=COLORS["success"])

    def _handle_add_time(self, minutes, reason):
        self.reasons_log.add(reason, minutes)
        if minutes > 0:
            self.timer.add_time(minutes * 60)

    def _offer_resume(self, remaining, total):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Resume Session?")
        dlg.geometry("400x200")
        dlg.configure(fg_color=COLORS["bg_secondary"])
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="⏰ Unfinished Session Found", font=FONTS["heading"],
                     text_color=COLORS["accent"]).pack(pady=(20, 5))
        ctk.CTkLabel(dlg, text=f"Time remaining: {self._fmt(remaining)}",
                     font=FONTS["body"], text_color=COLORS["text_primary"]).pack(pady=5)

        br = ctk.CTkFrame(dlg, fg_color="transparent")
        br.pack(pady=15)

        def resume():
            dlg.destroy()
            self.timer.resume_from_state(remaining, total)

        def discard():
            dlg.destroy()
            self.state_mgr.reset()

        ctk.CTkButton(br, text="▶ Resume", font=FONTS["button"], fg_color=COLORS["success"],
                      hover_color=COLORS["success_hover"], text_color=COLORS["bg_primary"],
                      width=120, command=resume).pack(side="left", padx=8)
        ctk.CTkButton(br, text="✕ Discard", font=FONTS["button"], fg_color=COLORS["danger"],
                      hover_color=COLORS["accent_hover"], text_color=COLORS["text_primary"],
                      width=120, command=discard).pack(side="left", padx=8)

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════════════

    def _on_tick(self, remaining):
        try:
            self.after(0, self._update_timer_display, remaining)
        except Exception:
            pass

    def _update_timer_display(self, remaining):
        self._timer_label.configure(text=self._fmt(remaining))
        self._progress.set(self.timer.progress)

    def _on_timer_complete(self):
        self.after(0, self._show_lock_screen)

    def _on_state_change(self, state):
        self.after(0, self._update_button_states, state)

    def _update_button_states(self, state):
        if state == TimerEngine.RUNNING:
            self._start_btn.configure(state="disabled")
            self._pause_btn.configure(state="normal", text="⏸ Pause")
            self._stop_btn.configure(state="normal")
            self._timer_status.configure(text="Focusing...", text_color=COLORS["success"])
        elif state == TimerEngine.PAUSED:
            self._start_btn.configure(state="disabled")
            self._pause_btn.configure(state="normal", text="▶ Resume")
            self._stop_btn.configure(state="normal")
            self._timer_status.configure(text="Paused", text_color=COLORS["warning"])
        elif state == TimerEngine.COMPLETED:
            self._start_btn.configure(state="normal")
            self._pause_btn.configure(state="disabled", text="⏸ Pause")
            self._stop_btn.configure(state="disabled")
            self._timer_status.configure(text="Session complete!", text_color=COLORS["accent"])
            self._update_stats_display()
        else:
            self._start_btn.configure(state="normal")
            self._pause_btn.configure(state="disabled", text="⏸ Pause")
            self._stop_btn.configure(state="disabled")
            self._timer_status.configure(text="Ready to focus", text_color=COLORS["text_secondary"])
            self._update_stats_display()

    def _show_lock_screen(self):
        if self._lock_screen is not None:
            try:
                self._lock_screen.destroy()
            except Exception:
                pass
        self._lock_screen = LockScreen(
            self, mode=self._mode,
            on_unlock=self._on_lock_unlock,
            on_add_time=self._handle_add_time
        )

    def _on_lock_unlock(self):
        self._lock_screen = None
        self._update_stats_display()
        self.timer.stop()

    # ═══════════════════════════════════════════════════════════════════
    # STATS
    # ═══════════════════════════════════════════════════════════════════

    def _update_stats_display(self):
        today = self.stats.get_today_stats()
        fm = today.get("focus_minutes", 0)
        if fm >= 60:
            self._stat_focus.configure(text=f"{fm // 60}h {fm % 60}m")
        else:
            self._stat_focus.configure(text=f"{fm}m")
        self._stat_sessions.configure(text=str(today.get("sessions_completed", 0)))
        self._stat_xp.configure(text=str(today.get("xp_earned", 0)))
        streak = self.stats.get_streak()
        self._stat_streak.configure(text=f"{streak} 🔥" if streak > 0 else "0")

        info = get_level_info(self.stats.get_total_xp())
        self._level_label.configure(text=f"{info['emoji']} Level {info['level']} — {info['title']}")
        self._xp_progress.set(info["progress"])

    # ═══════════════════════════════════════════════════════════════════
    # SETTINGS
    # ═══════════════════════════════════════════════════════════════════

    def _on_mode_change(self, selection):
        self._mode = MODE_TEST if "Test" in selection else MODE_REAL
        self.state_mgr.set("mode", self._mode)
        self.state_mgr.save()
        txt = "🧪 Test Mode — Safe & reversible" if self._mode == MODE_TEST else "🔒 Real Mode"
        self._footer.configure(text=txt)

    def _toggle_startup(self):
        if self._startup_var.get():
            startup_mgr.enable_startup()
        else:
            startup_mgr.disable_startup()
        self.state_mgr.set("startup_enabled", self._startup_var.get())
        self.state_mgr.save()

    def _on_close(self):
        if self.timer.state in (TimerEngine.RUNNING, TimerEngine.PAUSED):
            self.timer._save_state()
        self.destroy()
