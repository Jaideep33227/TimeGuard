"""
app.py — Main application UI and controller.
Features proper tabbed navigation, stats screen, session complete flow.
"""

import customtkinter as ctk
import winsound
from constants import (
    COLORS, FONTS, WINDOW_TITLE, WINDOW_SIZE,
    MODE_TEST, MODE_REAL, MODE_HARDCORE, DEFAULT_MODE,
    MIN_TIMER_SECONDS, MAX_TIMER_SECONDS, get_level_info,
    TAB_TIMER, TAB_STATS, TAB_SETTINGS
)
from storage import StateManager, ReasonsLog, StatsTracker
from timer_engine import TimerEngine
from lock_screen import LockScreen
import startup as startup_mgr


class FocusLockApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        # Setup Window
        ctk.set_appearance_mode("dark")
        self.title(WINDOW_TITLE)
        self.geometry(WINDOW_SIZE)
        self.minsize(500, 700)
        self.configure(fg_color=COLORS["bg_primary"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)

        # Managers
        self.state_mgr = StateManager()
        self.reasons_log = ReasonsLog()
        self.stats = StatsTracker()
        self.timer = TimerEngine(self.state_mgr, self.stats)
        
        # Wire timer callbacks
        self.timer.on_tick = self._on_tick
        self.timer.on_complete = self._on_timer_complete
        self.timer.on_state_change = self._on_state_change

        self._mode = self.state_mgr.get("mode", DEFAULT_MODE)
        self._lock_screen = None
        self._current_tab = TAB_TIMER

        self._build_ui()
        self._update_all_stats()

        # Resume logic
        rem, tot = self.state_mgr.get_pending_session()
        if rem > 0:
            self.after(500, lambda: self._offer_resume(rem, tot))

    # ═══════════════════════════════════════════════════════════════════
    # UI BUILDING
    # ═══════════════════════════════════════════════════════════════════

    def _build_ui(self):
        # Top Navigation Bar
        self.nav_frame = ctk.CTkFrame(self, height=50, fg_color=COLORS["bg_nav"], corner_radius=0)
        self.nav_frame.pack(fill="x", side="top")

        self.nav_btns = {}
        for text, tab_id in [("⏱ Timer", TAB_TIMER), ("📊 Stats", TAB_STATS), ("⚙ Settings", TAB_SETTINGS)]:
            btn = ctk.CTkButton(
                self.nav_frame, text=text, font=FONTS["nav"],
                fg_color="transparent", text_color=COLORS["nav_inactive"],
                hover_color=COLORS["bg_card"], width=120, height=40,
                command=lambda tid=tab_id: self._switch_tab(tid)
            )
            btn.pack(side="left", padx=5, pady=5)
            self.nav_btns[tab_id] = btn

        # Main Content Area
        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.content_frame.pack(fill="both", expand=True, padx=20, pady=15)

        # Tab Frames
        self.tabs = {
            TAB_TIMER: self._build_timer_tab(),
            TAB_STATS: self._build_stats_tab(),
            TAB_SETTINGS: self._build_settings_tab(),
        }

        self._switch_tab(TAB_TIMER)

    def _card(self, parent) -> ctk.CTkFrame:
        c = ctk.CTkFrame(parent, fg_color=COLORS["bg_secondary"], corner_radius=16,
                         border_width=1, border_color=COLORS["border"])
        c.pack(fill="x", pady=8)
        return c

    # ─── Timer Tab ───────────────────────────────────────────────────

    def _build_timer_tab(self):
        frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        
        # Countdown
        cd_card = self._card(frame)
        self._timer_label = ctk.CTkLabel(cd_card, text="00:00:00", font=FONTS["timer_large"], text_color=COLORS["text_primary"])
        self._timer_label.pack(pady=(20, 5))
        
        self._timer_status = ctk.CTkLabel(cd_card, text="Ready to focus", font=FONTS["timer_label"], text_color=COLORS["text_secondary"])
        self._timer_status.pack(pady=(0, 10))
        
        self._progress = ctk.CTkProgressBar(cd_card, width=380, height=12, fg_color=COLORS["progress_bg"], progress_color=COLORS["progress_fill"])
        self._progress.set(0)
        self._progress.pack(pady=(0, 20))

        br = ctk.CTkFrame(cd_card, fg_color="transparent")
        br.pack(pady=(0, 20))
        self._start_btn = ctk.CTkButton(br, text="▶ Start", font=FONTS["button"], fg_color=COLORS["success"], width=110, height=40, command=self._start_timer)
        self._start_btn.pack(side="left", padx=5)
        self._pause_btn = ctk.CTkButton(br, text="⏸ Pause", font=FONTS["button"], fg_color=COLORS["warning"], width=110, height=40, command=self._toggle_pause, state="disabled")
        self._pause_btn.pack(side="left", padx=5)
        self._stop_btn = ctk.CTkButton(br, text="⏹ Stop", font=FONTS["button"], fg_color=COLORS["danger"], width=110, height=40, command=self._stop_timer, state="disabled")
        self._stop_btn.pack(side="left", padx=5)

        # Setup
        setup_card = self._card(frame)
        ctk.CTkLabel(setup_card, text="⏱ Set Timer", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(15, 10))
        
        tr = ctk.CTkFrame(setup_card, fg_color="transparent")
        tr.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(tr, text="Hours:", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left")
        self._hours_var = ctk.StringVar(value="1")
        ctk.CTkEntry(tr, textvariable=self._hours_var, width=60, justify="center", fg_color=COLORS["bg_input"]).pack(side="left", padx=(5, 20))
        ctk.CTkLabel(tr, text="Minutes:", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left")
        self._mins_var = ctk.StringVar(value="0")
        ctk.CTkEntry(tr, textvariable=self._mins_var, width=60, justify="center", fg_color=COLORS["bg_input"]).pack(side="left", padx=(5, 0))

        pr = ctk.CTkFrame(setup_card, fg_color="transparent")
        pr.pack(fill="x", padx=20, pady=(0, 15))
        for lbl, h, m in [("25m",0,25), ("45m",0,45), ("1h",1,0), ("2h",2,0), ("3h",3,0)]:
            ctk.CTkButton(pr, text=lbl, width=60, height=32, font=FONTS["body_small"], fg_color=COLORS["secondary"], command=lambda hh=h, mm=m: self._set_preset(hh, mm)).pack(side="left", padx=4)

        # Add Time
        add_card = self._card(frame)
        ctk.CTkLabel(add_card, text="➕ Add Extra Time", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(15, 10))
        ar = ctk.CTkFrame(add_card, fg_color="transparent")
        ar.pack(fill="x", padx=20)
        ctk.CTkLabel(ar, text="Minutes:", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left")
        self._add_min_var = ctk.StringVar(value="15")
        ctk.CTkEntry(ar, textvariable=self._add_min_var, width=60, justify="center", fg_color=COLORS["bg_input"]).pack(side="left", padx=(5, 0))
        
        ctk.CTkLabel(add_card, text="Reason:", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(anchor="w", padx=20, pady=(10, 2))
        self._add_reason_var = ctk.StringVar()
        ctk.CTkEntry(add_card, textvariable=self._add_reason_var, placeholder_text="Why do you need more time?", fg_color=COLORS["bg_input"]).pack(fill="x", padx=20)
        
        self._add_status = ctk.CTkLabel(add_card, text="", font=FONTS["body_small"])
        self._add_status.pack(pady=4)
        ctk.CTkButton(add_card, text="Request Extra Time", fg_color=COLORS["secondary"], command=self._add_extra_time).pack(fill="x", padx=20, pady=(0, 15))

        return frame

    # ─── Stats Tab ───────────────────────────────────────────────────

    def _build_stats_tab(self):
        frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        
        # Level Card
        lvl_card = self._card(frame)
        self._lvl_emoji = ctk.CTkLabel(lvl_card, text="🌱", font=FONTS["big_emoji"])
        self._lvl_emoji.pack(pady=(20, 5))
        self._lvl_title = ctk.CTkLabel(lvl_card, text="Level 1 — Beginner", font=("Segoe UI", 24, "bold"), text_color=COLORS["accent"])
        self._lvl_title.pack()
        self._lvl_xp = ctk.CTkLabel(lvl_card, text="0 / 100 XP", font=FONTS["body"], text_color=COLORS["text_secondary"])
        self._lvl_xp.pack(pady=(5, 10))
        self._lvl_prog = ctk.CTkProgressBar(lvl_card, width=380, height=12, fg_color=COLORS["progress_bg"], progress_color=COLORS["success"])
        self._lvl_prog.set(0)
        self._lvl_prog.pack(pady=(0, 25))

        # Today's Stats
        td_card = self._card(frame)
        ctk.CTkLabel(td_card, text="📅 Today", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(15, 10))
        sg1 = ctk.CTkFrame(td_card, fg_color="transparent")
        sg1.pack(fill="x", padx=15, pady=(0, 15))
        sg1.columnconfigure((0,1), weight=1)
        self._td_focus = self._stat_box(sg1, "Focus Time", "0m", 0, 0)
        self._td_sess = self._stat_box(sg1, "Sessions", "0", 0, 1)
        self._td_xp = self._stat_box(sg1, "XP Earned", "0", 1, 0)
        self._td_strk = self._stat_box(sg1, "Current Streak", "0", 1, 1)

        # Lifetime Stats
        lf_card = self._card(frame)
        ctk.CTkLabel(lf_card, text="🏆 Lifetime", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(15, 10))
        sg2 = ctk.CTkFrame(lf_card, fg_color="transparent")
        sg2.pack(fill="x", padx=15, pady=(0, 15))
        sg2.columnconfigure((0,1), weight=1)
        self._lf_focus = self._stat_box(sg2, "Total Focus", "0h 0m", 0, 0)
        self._lf_sess = self._stat_box(sg2, "Total Sessions", "0", 0, 1)
        self._lf_xp = self._stat_box(sg2, "Total XP", "0", 1, 0)
        self._lf_days = self._stat_box(sg2, "Days Active", "0", 1, 1)

        # Recent Reasons & Insights
        bottom_frame = ctk.CTkFrame(frame, fg_color="transparent")
        bottom_frame.pack(fill="x", pady=(0, 15))
        bottom_frame.columnconfigure((0, 1), weight=1)

        # Insights
        i_card = self._card(bottom_frame)
        i_card.grid(row=0, column=0, padx=(0, 5), sticky="nsew")
        ctk.CTkLabel(i_card, text="🧠 Smart Insights", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(15, 10))
        self._insight_label = ctk.CTkLabel(i_card, text="Analyzing behavior...", font=FONTS["body"], text_color=COLORS["text_secondary"], wraplength=200, justify="left")
        self._insight_label.pack(anchor="nw", padx=20, pady=(0, 15))

        # Recent Reasons
        r_card = self._card(bottom_frame)
        r_card.grid(row=0, column=1, padx=(5, 0), sticky="nsew")
        ctk.CTkLabel(r_card, text="📝 Recent Reasons", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(15, 10))
        self._reasons_frame = ctk.CTkFrame(r_card, fg_color="transparent")
        self._reasons_frame.pack(fill="both", expand=True, padx=20, pady=(0, 15))
        
        return frame

    def _stat_box(self, parent, label, value, row, col):
        f = ctk.CTkFrame(parent, fg_color=COLORS["bg_card"], corner_radius=12)
        f.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        vl = ctk.CTkLabel(f, text=value, font=FONTS["stat_value"], text_color=COLORS["text_primary"])
        vl.pack(pady=(12, 2))
        ctk.CTkLabel(f, text=label, font=FONTS["stat_label"], text_color=COLORS["text_secondary"]).pack(pady=(0, 12))
        return vl

    # ─── Settings Tab ────────────────────────────────────────────────

    def _build_settings_tab(self):
        frame = ctk.CTkScrollableFrame(self.content_frame, fg_color="transparent")
        
        set_card = self._card(frame)
        ctk.CTkLabel(set_card, text="⚙ Settings", font=FONTS["heading"], text_color=COLORS["text_primary"]).pack(anchor="w", padx=20, pady=(20, 15))
        
        mr = ctk.CTkFrame(set_card, fg_color="transparent")
        mr.pack(fill="x", padx=20, pady=(0, 15))
        ctk.CTkLabel(mr, text="Safety Mode:", font=FONTS["body"], text_color=COLORS["text_secondary"]).pack(side="left")
        
        mode_val = "🧪 Test Mode"
        if self._mode == MODE_REAL: mode_val = "🔒 Real Mode"
        elif self._mode == MODE_HARDCORE: mode_val = "🔥 Hardcore Mode"
            
        self._mode_var = ctk.StringVar(value=mode_val)
        ctk.CTkOptionMenu(mr, values=["🧪 Test Mode", "🔒 Real Mode", "🔥 Hardcore Mode"], variable=self._mode_var, command=self._on_mode_change, fg_color=COLORS["bg_input"]).pack(side="left", padx=(15, 0))

        self._startup_var = ctk.BooleanVar(value=startup_mgr.is_startup_enabled())
        ctk.CTkCheckBox(set_card, text="Start FocusLock when Windows starts", font=FONTS["body"], variable=self._startup_var, command=self._toggle_startup, fg_color=COLORS["accent"]).pack(anchor="w", padx=20, pady=(0, 20))

        self._footer = ctk.CTkLabel(set_card, text="Select a mode above.", font=FONTS["body_small"], text_color=COLORS["text_dim"])
        self._footer.pack(pady=(0, 20))

        # Reset Stats Danger Zone
        d_card = self._card(frame)
        ctk.CTkLabel(d_card, text="⚠ Danger Zone", font=FONTS["heading"], text_color=COLORS["danger"]).pack(anchor="w", padx=20, pady=(20, 10))
        ctk.CTkButton(d_card, text="Reset All Stats & Data", fg_color="transparent", border_width=1, border_color=COLORS["danger"], text_color=COLORS["danger"], hover_color="#3a1115", command=self._reset_data).pack(anchor="w", padx=20, pady=(0, 20))

        return frame

    def _switch_tab(self, tab_id):
        self._current_tab = tab_id
        for tid, btn in self.nav_btns.items():
            btn.configure(text_color=COLORS["nav_active"] if tid == tab_id else COLORS["nav_inactive"])
        for tid, frame in self.tabs.items():
            if tid == tab_id:
                frame.pack(fill="both", expand=True)
            else:
                frame.pack_forget()

    # ═══════════════════════════════════════════════════════════════════
    # ACTIONS
    # ═══════════════════════════════════════════════════════════════════

    @staticmethod
    def _fmt(seconds: int) -> str:
        s = max(0, int(seconds))
        return f"{s // 3600:02d}:{(s % 3600) // 60:02d}:{s % 60:02d}"

    def _set_preset(self, h, m):
        self._hours_var.set(str(h))
        self._mins_var.set(str(m))

    def _start_timer(self):
        try:
            h = int(self._hours_var.get() or 0)
            m = int(self._mins_var.get() or 0)
            tot = h * 3600 + m * 60
            if tot < MIN_TIMER_SECONDS or tot > MAX_TIMER_SECONDS:
                raise ValueError
            self.timer.start(tot)
        except ValueError:
            self._timer_status.configure(text="⚠ Valid time: 1 min to 12 hours", text_color=COLORS["danger"])

    def _toggle_pause(self):
        if self.timer.state == TimerEngine.RUNNING: self.timer.pause()
        elif self.timer.state == TimerEngine.PAUSED: self.timer.unpause()

    def _stop_timer(self):
        self.timer.stop()
        self._timer_label.configure(text="00:00:00")
        self._progress.set(0)
        self._update_all_stats()

    def _add_extra_time(self):
        if self.timer.state == TimerEngine.IDLE:
            self._add_status.configure(text="⚠ Start a timer first", text_color=COLORS["danger"])
            return
        try:
            mins = int(self._add_min_var.get())
            if not (0 < mins <= 480): raise ValueError
            reason = self._add_reason_var.get().strip()
            if not reason: raise ValueError
            
            self.reasons_log.add(reason, mins)
            self.timer.add_time(mins * 60)
            self._add_reason_var.set("")
            self._add_status.configure(text=f"✅ Added {mins}m!", text_color=COLORS["success"])
            self._update_reasons_list()
        except ValueError:
            self._add_status.configure(text="⚠ Valid mins + reason required", text_color=COLORS["danger"])

    # ═══════════════════════════════════════════════════════════════════
    # CALLBACKS
    # ═══════════════════════════════════════════════════════════════════

    def _on_tick(self, remaining):
        self.after(0, self._update_timer_display, remaining)

    def _update_timer_display(self, remaining):
        self._timer_label.configure(text=self._fmt(remaining))
        self._progress.set(self.timer.progress)

    def _on_timer_complete(self, xp_info):
        try: winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except: pass
        self.after(0, lambda: self._show_session_complete(xp_info))

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
        else:
            self._start_btn.configure(state="normal")
            self._pause_btn.configure(state="disabled", text="⏸ Pause")
            self._stop_btn.configure(state="disabled")
            self._timer_status.configure(text="Ready to focus", text_color=COLORS["text_secondary"])

    # ═══════════════════════════════════════════════════════════════════
    # SESSION COMPLETE & LOCK
    # ═══════════════════════════════════════════════════════════════════

    def _show_session_complete(self, xp_info):
        """Show XP gained, then trigger lock screen."""
        self._update_all_stats()
        
        dlg = ctk.CTkToplevel(self)
        dlg.title("Session Complete!")
        dlg.geometry("450x350")
        dlg.configure(fg_color=COLORS["bg_secondary"])
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="🎉", font=FONTS["big_emoji"]).pack(pady=(20, 5))
        ctk.CTkLabel(dlg, text="SESSION COMPLETE", font=FONTS["title"], text_color=COLORS["success"]).pack()
        
        f = ctk.CTkFrame(dlg, fg_color=COLORS["bg_card"], corner_radius=10)
        f.pack(fill="x", padx=40, pady=20, ipady=10)
        
        ctk.CTkLabel(f, text=f"Focused: {xp_info['focused_minutes']}m", font=FONTS["body"]).pack(pady=5)
        ctk.CTkLabel(f, text=f"+{xp_info['total_xp_gained']} XP", font=FONTS["xp_popup"], text_color=COLORS["accent"]).pack(pady=5)

        def proceed():
            dlg.destroy()
            self._show_lock_screen()

        ctk.CTkButton(dlg, text="Continue to Lock Screen", font=FONTS["button"], fg_color=COLORS["secondary"], height=40, command=proceed).pack(pady=10)
        self.after(5000, proceed)  # Auto-proceed after 5s

    def _show_lock_screen(self):
        if self._lock_screen:
            try: self._lock_screen.destroy()
            except Exception: pass
            
        self._lock_screen = LockScreen(
            self, mode=self._mode,
            on_unlock=self._on_lock_unlock,
            on_add_time=self._handle_lock_add_time
        )

    def _handle_lock_add_time(self, mins, reason):
        self.reasons_log.add(reason, mins)
        if mins > 0:
            self.timer.add_time(mins * 60)
            self._update_reasons_list()

    def _on_lock_unlock(self):
        self._lock_screen = None
        self.timer.stop()
        self._update_all_stats()

    # ═══════════════════════════════════════════════════════════════════
    # STATS & UI UPDATES
    # ═══════════════════════════════════════════════════════════════════

    def _update_all_stats(self):
        td = self.stats.get_today_stats()
        lf = self.stats.get_all_time_stats()
        lvl = get_level_info(lf["total_xp"])

        # Level Card
        self._lvl_emoji.configure(text=lvl["emoji"])
        self._lvl_title.configure(text=f"Level {lvl['level']} — {lvl['title']}")
        self._lvl_xp.configure(text=f"{lvl['xp_in_level']} / {lvl['xp_for_next']} XP to next level")
        self._lvl_prog.set(lvl["progress"])

        # Today
        fm = td.get("focus_minutes", 0)
        self._td_focus.configure(text=f"{fm//60}h {fm%60}m" if fm>=60 else f"{fm}m")
        self._td_sess.configure(text=str(td.get("sessions_completed", 0)))
        self._td_xp.configure(text=str(td.get("xp_earned", 0)))
        self._td_strk.configure(text=f"{lf['current_streak']} 🔥" if lf['current_streak']>0 else "0")

        # Lifetime
        lfm = lf["total_focus_minutes"]
        self._lf_focus.configure(text=f"{lfm//60}h {lfm%60}m")
        self._lf_sess.configure(text=str(lf["total_sessions"]))
        self._lf_xp.configure(text=str(lf["total_xp"]))
        self._lf_days.configure(text=str(lf["days_active"]))

        # Smart Insights
        adds_today = self.reasons_log.get_today_count()
        if adds_today >= 3:
            self._insight_label.configure(text=f"You added time {adds_today} times today.\n\nTry setting shorter initial timers (e.g. 25m) to build momentum instead of marathon sessions.")
        elif td.get("sessions_completed", 0) == 0 and fm > 0:
            self._insight_label.configure(text="You have focus time but no completed sessions today. Finish a timer to get bonus XP!")
        elif lf["current_streak"] >= 3:
            self._insight_label.configure(text=f"You're on a {lf['current_streak']}-day streak! Your consistency is building serious focus muscles.")
        else:
            self._insight_label.configure(text="Complete sessions to build your daily streak and earn bonus XP multipliers.")

        self._update_reasons_list()

    def _update_reasons_list(self):
        for widget in self._reasons_frame.winfo_children():
            widget.destroy()
            
        recent = self.reasons_log.get_recent(5)
        if not recent:
            ctk.CTkLabel(self._reasons_frame, text="No extra time requested yet.", text_color=COLORS["text_dim"]).pack(pady=10)
            return
            
        for r in reversed(recent):
            f = ctk.CTkFrame(self._reasons_frame, fg_color=COLORS["bg_input"], corner_radius=8)
            f.pack(fill="x", pady=4)
            d = r.get("date", "")
            m = r.get("minutes_added", 0)
            txt = r.get("reason", "")
            
            hd = ctk.CTkFrame(f, fg_color="transparent")
            hd.pack(fill="x", padx=10, pady=(8,2))
            ctk.CTkLabel(hd, text=d, font=FONTS["body_small"], text_color=COLORS["text_secondary"]).pack(side="left")
            if m > 0:
                ctk.CTkLabel(hd, text=f"+{m}m", font=FONTS["badge"], text_color=COLORS["accent"]).pack(side="right")
                
            ctk.CTkLabel(f, text=txt, font=FONTS["body"], text_color=COLORS["text_primary"], justify="left", wraplength=400).pack(anchor="w", padx=10, pady=(0,8))

    # ═══════════════════════════════════════════════════════════════════
    # SETTINGS & APP LIFECYCLE
    # ═══════════════════════════════════════════════════════════════════

    def _on_mode_change(self, val):
        if "Test" in val:
            self._mode = MODE_TEST
            self._footer.configure(text="🧪 Test Mode — Safe & reversible lock screen.")
        elif "Hardcore" in val:
            self._mode = MODE_HARDCORE
            self._footer.configure(text="🔥 Hardcore Mode — No extra time allowed on lock screen.")
        else:
            self._mode = MODE_REAL
            self._footer.configure(text="🔒 Real Mode — Enter reason to unlock.")
            
        self.state_mgr.set("mode", self._mode)
        self.state_mgr.save()

    def _toggle_startup(self):
        if self._startup_var.get(): startup_mgr.enable_startup()
        else: startup_mgr.disable_startup()
        self.state_mgr.set("startup_enabled", self._startup_var.get())
        self.state_mgr.save()

    def _reset_data(self):
        # Clear files in data dir (lazy way, requires restart)
        import os
        from constants import STATE_FILE, REASONS_FILE, STATS_FILE
        for f in [STATE_FILE, REASONS_FILE, STATS_FILE]:
            if os.path.exists(f): os.remove(f)
        self.destroy()

    def _offer_resume(self, rem, tot):
        dlg = ctk.CTkToplevel(self)
        dlg.title("Resume?")
        dlg.geometry("400x200")
        dlg.configure(fg_color=COLORS["bg_secondary"])
        dlg.attributes("-topmost", True)
        dlg.grab_set()

        ctk.CTkLabel(dlg, text="⏰ Unfinished Session", font=FONTS["heading"], text_color=COLORS["accent"]).pack(pady=(20, 5))
        ctk.CTkLabel(dlg, text=f"Remaining: {self._fmt(rem)}", font=FONTS["body"]).pack(pady=5)
        br = ctk.CTkFrame(dlg, fg_color="transparent")
        br.pack(pady=15)

        def resume():
            dlg.destroy()
            self.timer.resume_from_state(rem, tot)
        def discard():
            dlg.destroy()
            self.state_mgr.reset()

        ctk.CTkButton(br, text="▶ Resume", fg_color=COLORS["success"], width=100, command=resume).pack(side="left", padx=8)
        ctk.CTkButton(br, text="✕ Discard", fg_color=COLORS["danger"], width=100, command=discard).pack(side="left", padx=8)

    def _on_close(self):
        # Streak warning check
        td = self.stats.get_today_stats()
        lf = self.stats.get_all_time_stats()
        streak = lf.get("current_streak", 0)
        sessions_today = td.get("sessions_completed", 0)
        
        if streak > 0 and sessions_today == 0:
            dlg = ctk.CTkToplevel(self)
            dlg.title("Wait!")
            dlg.geometry("400x200")
            dlg.configure(fg_color=COLORS["bg_secondary"])
            dlg.attributes("-topmost", True)
            dlg.grab_set()

            ctk.CTkLabel(dlg, text="🔥 Don't lose your streak!", font=FONTS["heading"], text_color=COLORS["danger"]).pack(pady=(20, 5))
            ctk.CTkLabel(dlg, text=f"You're about to lose your {streak}-day streak.\nComplete a quick session to save it.", font=FONTS["body"]).pack(pady=5)
            
            br = ctk.CTkFrame(dlg, fg_color="transparent")
            br.pack(pady=15)
            
            def exit_anyway():
                dlg.destroy()
                self._force_close()
                
            def stay():
                dlg.destroy()

            ctk.CTkButton(br, text="Stay & Focus", fg_color=COLORS["success"], width=120, command=stay).pack(side="left", padx=8)
            ctk.CTkButton(br, text="Exit Anyway", fg_color="transparent", border_width=1, border_color=COLORS["danger"], text_color=COLORS["danger"], width=120, command=exit_anyway).pack(side="left", padx=8)
            return

        self._force_close()
        
    def _force_close(self):
        self.timer.save_current_state()
        self.destroy()
