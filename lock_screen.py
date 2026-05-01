"""
lock_screen.py — Safe full-screen lock overlay.

SAFETY GUARANTEES:
  - Always a tkinter overlay, never system-level lock.
  - Ctrl+Shift+U ALWAYS exits in both Test and Real mode.
  - Unlock button always visible in Test mode.
  - Task Manager is NEVER disabled.
"""

import customtkinter as ctk
import winsound
import threading
from constants import COLORS, FONTS, BEEP_FREQUENCY, BEEP_DURATION, BEEP_COUNT, MODE_TEST, MODE_HARDCORE


class LockScreen(ctk.CTkToplevel):
    """Full-screen overlay shown when timer expires. Always safe and reversible."""

    def __init__(self, parent, mode=MODE_TEST, on_unlock=None, on_add_time=None, hardcore_quits=0, on_give_up=None):
        super().__init__(parent)

        self._mode = mode
        self._on_unlock = on_unlock
        self._on_add_time = on_add_time
        self._on_give_up = on_give_up
        self._is_closing = False
        
        # Calculate dynamic delay
        self._delay_ms = 10000
        if self._mode == MODE_HARDCORE:
            if hardcore_quits == 1: self._delay_ms = 30000
            elif hardcore_quits >= 2: self._delay_ms = 60000

        # ─── Window config ────────────────────────────────────────────
        self.title("FocusLock — Time's Up!")
        self.configure(fg_color=COLORS["bg_primary"])
        self.protocol("WM_DELETE_WINDOW", lambda: None)

        # Bind emergency exit BEFORE any visual setup
        self.bind("<Control-Shift-U>", lambda e: self._unlock())
        self.bind("<Control-Shift-u>", lambda e: self._unlock())

        # Full-screen setup (deferred slightly to ensure window is mapped)
        self.after(50, self._apply_fullscreen)

        # Build UI
        self._build_ui()

        # Play notification sound
        threading.Thread(target=self._play_sound, daemon=True).start()

    def _apply_fullscreen(self):
        """Apply fullscreen attributes after the window is mapped."""
        try:
            self.overrideredirect(True)
            self.attributes("-topmost", True)
            sw = self.winfo_screenwidth()
            sh = self.winfo_screenheight()
            self.geometry(f"{sw}x{sh}+0+0")
            self.focus_force()
            self.grab_set()
            self.lift()
            self._keep_on_top()
        except Exception:
            pass

    def _build_ui(self):
        """Build the lock screen interface."""
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        # Main card
        card = ctk.CTkFrame(
            container, fg_color=COLORS["bg_secondary"],
            corner_radius=30, border_width=2, border_color=COLORS["accent"]
        )
        card.pack(padx=40, pady=30, ipadx=50, ipady=30)

        # Icon + Title
        ctk.CTkLabel(card, text="⏰", font=FONTS["big_emoji"],
                     text_color=COLORS["accent"]).pack(pady=(20, 5))

        ctk.CTkLabel(card, text="TIME'S UP!", font=("Segoe UI", 42, "bold"),
                     text_color=COLORS["accent"]).pack(pady=(0, 5))

        ctk.CTkLabel(card, text="Your focus session has ended.\nTake a break or request more time.",
                     font=FONTS["body"], text_color=COLORS["text_secondary"],
                     justify="center").pack(pady=(0, 15))

        # Mode badge
        if self._mode == MODE_TEST:
            mode_text, mode_color = "🧪 TEST MODE — Safe Overlay", COLORS["success"]
        elif self._mode == MODE_HARDCORE:
            mode_text, mode_color = "🔥 HARDCORE MODE — No Escape", COLORS["danger"]
        else:
            mode_text, mode_color = "🔒 REAL MODE", COLORS["warning"]
            
        ctk.CTkLabel(card, text=mode_text, font=FONTS["badge"],
                     text_color=mode_color, fg_color=COLORS["bg_card"],
                     corner_radius=12, padx=16, pady=4).pack(pady=(0, 20))

        # ─── Add Time Section ─────────────────────────────────────────
        if self._mode != MODE_HARDCORE:
            self._build_add_time_section(card)

        # Status label
        self._status = ctk.CTkLabel(card, text="", font=FONTS["body_small"],
                                    text_color=COLORS["danger"])
        self._status.pack(pady=(0, 5))

        # ─── Unlock Button (Delayed) ──────────────────────────────────
        self._unlock_frame = ctk.CTkFrame(card, fg_color="transparent")
        self._unlock_frame.pack(fill="x", padx=25, pady=(5, 8))
        
        delay_sec = self._delay_ms // 1000
        self._delay_label = ctk.CTkLabel(self._unlock_frame, text=f"You made a promise to yourself.\nDon't break it.\n(Unlock available in {delay_sec}s...)", 
                                        font=FONTS["body_small"], text_color=COLORS["text_dim"])
        self._delay_label.pack(pady=10)
        
        # Shortcut hint
        ctk.CTkLabel(card, text="Press Ctrl + Shift + U to emergency exit",
                     font=FONTS["body_small"],
                     text_color=COLORS["text_dim"]).pack(pady=(0, 12))

        # Start delayed unlock timer
        self.after(self._delay_ms, self._show_unlock_button)

    def _build_add_time_section(self, card):
        add_frame = ctk.CTkFrame(card, fg_color=COLORS["bg_card"], corner_radius=15)
        add_frame.pack(fill="x", padx=25, pady=(0, 12))

        ctk.CTkLabel(add_frame, text="➕ Request Extra Time",
                     font=FONTS["subheading"],
                     text_color=COLORS["text_primary"]).pack(pady=(12, 6))

        # Minutes row
        min_row = ctk.CTkFrame(add_frame, fg_color="transparent")
        min_row.pack(fill="x", padx=18)
        ctk.CTkLabel(min_row, text="Minutes:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 8))
        self._extra_min = ctk.StringVar(value="15")
        ctk.CTkEntry(min_row, textvariable=self._extra_min, width=70,
                     font=FONTS["body"], fg_color=COLORS["bg_input"],
                     text_color=COLORS["text_primary"],
                     border_color=COLORS["border"], justify="center"
                     ).pack(side="left")

        # Reason input
        ctk.CTkLabel(add_frame, text="Reason (required):", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]
                     ).pack(anchor="w", padx=18, pady=(8, 2))
        self._reason = ctk.StringVar()
        ctk.CTkEntry(add_frame, textvariable=self._reason,
                     placeholder_text="Why do you need more time?",
                     font=FONTS["body"], fg_color=COLORS["bg_input"],
                     text_color=COLORS["text_primary"],
                     border_color=COLORS["border"]
                     ).pack(fill="x", padx=18, pady=(0, 8))

        ctk.CTkButton(add_frame, text="Add Extra Time", font=FONTS["button"],
                      fg_color=COLORS["secondary"],
                      hover_color=COLORS["secondary_hover"],
                      text_color=COLORS["text_primary"],
                      corner_radius=10, height=36,
                      command=self._request_extra_time
                      ).pack(fill="x", padx=18, pady=(0, 12))

    def _show_unlock_button(self):
        if self._is_closing: return
        try:
            self._delay_label.destroy()
            if self._mode == MODE_TEST:
                ctk.CTkButton(
                    self._unlock_frame, text="🔓  Unlock (Test Mode)",
                    font=("Segoe UI", 16, "bold"),
                    fg_color=COLORS["success"],
                    hover_color=COLORS["success_hover"],
                    text_color=COLORS["bg_primary"],
                    corner_radius=12, height=48,
                    command=self._unlock
                ).pack(fill="x")
            elif self._mode == MODE_HARDCORE:
                ctk.CTkButton(
                    self._unlock_frame, text="🔓  Give Up (Hardcore Penalty)",
                    font=("Segoe UI", 14, "bold"),
                    fg_color=COLORS["danger"],
                    hover_color=COLORS["accent_hover"],
                    text_color=COLORS["text_primary"],
                    corner_radius=12, height=44,
                    command=self._trigger_give_up
                ).pack(fill="x")
            else:
                ctk.CTkButton(
                    self._unlock_frame, text="🔓  Unlock (Enter Reason Above)",
                    font=("Segoe UI", 14, "bold"),
                    fg_color=COLORS["warning"],
                    hover_color=COLORS["accent_hover"],
                    text_color=COLORS["bg_primary"],
                    corner_radius=12, height=44,
                    command=self._unlock_real
                ).pack(fill="x")
        except Exception:
            pass

    # ─── Behaviour ────────────────────────────────────────────────────

    def _trigger_give_up(self):
        """Trigger the hardcore give up penalty flow."""
        if self._is_closing: return
        self._is_closing = True
        try: self.grab_release()
        except Exception: pass
        if self._on_give_up: self._on_give_up()
        try: self.destroy()
        except Exception: pass

    def _keep_on_top(self):
        """Re-assert topmost position periodically."""
        if not self._is_closing:
            try:
                self.attributes("-topmost", True)
                self.lift()
                self.focus_force()
                self.after(500, self._keep_on_top)
            except Exception:
                pass

    def _play_sound(self):
        try:
            for _ in range(BEEP_COUNT):
                winsound.Beep(BEEP_FREQUENCY, BEEP_DURATION)
                winsound.Beep(int(BEEP_FREQUENCY * 1.25), BEEP_DURATION)
        except Exception:
            pass

    def _unlock(self):
        """Dismiss the lock screen. Always works."""
        if self._is_closing:
            return
        self._is_closing = True
        try:
            self.grab_release()
        except Exception:
            pass
        if self._on_unlock:
            self._on_unlock()
        try:
            self.destroy()
        except Exception:
            pass

    def _unlock_real(self):
        """Real mode: require a reason to unlock."""
        reason = self._reason.get().strip()
        if not reason:
            self._status.configure(text="⚠ Enter a reason to unlock.",
                                   text_color=COLORS["warning"])
            return
        if self._on_add_time:
            self._on_add_time(0, f"[UNLOCK] {reason}")
        self._unlock()

    def _request_extra_time(self):
        """Handle extra time request from the lock screen."""
        try:
            mins = int(self._extra_min.get())
            if mins <= 0 or mins > 480:
                raise ValueError
        except ValueError:
            self._status.configure(text="⚠ Enter valid minutes (1–480).",
                                   text_color=COLORS["danger"])
            return

        reason = self._reason.get().strip()
        if not reason:
            self._status.configure(text="⚠ Enter a reason for extra time.",
                                   text_color=COLORS["danger"])
            return

        self._status.configure(text=f"✅ Added {mins} minutes!",
                               text_color=COLORS["success"])
        if self._on_add_time:
            self._on_add_time(mins, reason)
        self.after(1200, self._unlock)
