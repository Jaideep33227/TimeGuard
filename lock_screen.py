"""
lock_screen.py — Full-screen lock overlay.

SAFETY:
  - Always a reversible overlay, never system-level lock.
  - Ctrl+Shift+U ALWAYS exits. Task Manager NEVER disabled.
"""

import customtkinter as ctk
import winsound
import threading
from constants import COLORS, FONTS, BEEP_FREQUENCY, BEEP_DURATION, BEEP_COUNT, MODE_TEST


class LockScreen(ctk.CTkToplevel):
    def __init__(self, parent, mode=MODE_TEST, on_unlock=None, on_add_time=None):
        super().__init__(parent)
        self._mode = mode
        self._on_unlock = on_unlock
        self._on_add_time = on_add_time
        self._is_closing = False

        self.title("FocusLock — Time's Up!")
        self.configure(fg_color=COLORS["bg_primary"])
        self.overrideredirect(True)
        self.attributes("-topmost", True)
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        self.geometry(f"{sw}x{sh}+0+0")
        self.protocol("WM_DELETE_WINDOW", lambda: None)
        self.bind("<Control-Shift-U>", lambda e: self._unlock())
        self.bind("<Control-Shift-u>", lambda e: self._unlock())
        self.focus_force()
        self.grab_set()
        self.lift()
        self._build_ui()
        threading.Thread(target=self._play_sound, daemon=True).start()
        self._keep_on_top()

    def _build_ui(self):
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.place(relx=0.5, rely=0.5, anchor="center")

        glow = ctk.CTkFrame(container, fg_color=COLORS["bg_secondary"],
                            corner_radius=30, border_width=2, border_color=COLORS["accent"])
        glow.pack(padx=60, pady=40, ipadx=60, ipady=40)

        ctk.CTkLabel(glow, text="⏰", font=("Segoe UI Emoji", 72),
                     text_color=COLORS["accent"]).pack(pady=(20, 5))
        ctk.CTkLabel(glow, text="TIME'S UP!", font=("Segoe UI", 48, "bold"),
                     text_color=COLORS["accent"]).pack(pady=(5, 5))
        ctk.CTkLabel(glow, text="Your focus session has ended.\nTake a break or request more time.",
                     font=FONTS["body"], text_color=COLORS["text_secondary"],
                     justify="center").pack(pady=(0, 20))

        mode_text = "🧪 TEST MODE — Safe Overlay" if self._mode == MODE_TEST else "🔒 REAL MODE"
        mode_color = COLORS["success"] if self._mode == MODE_TEST else COLORS["warning"]
        ctk.CTkLabel(glow, text=mode_text, font=FONTS["badge"], text_color=mode_color,
                     fg_color=COLORS["bg_card"], corner_radius=12, padx=16, pady=4).pack(pady=(0, 25))

        # Add time section
        atf = ctk.CTkFrame(glow, fg_color=COLORS["bg_card"], corner_radius=15)
        atf.pack(fill="x", padx=30, pady=(0, 15))

        ctk.CTkLabel(atf, text="➕ Request Extra Time", font=FONTS["subheading"],
                     text_color=COLORS["text_primary"]).pack(pady=(15, 8))

        mr = ctk.CTkFrame(atf, fg_color="transparent")
        mr.pack(fill="x", padx=20)
        ctk.CTkLabel(mr, text="Minutes:", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(side="left", padx=(0, 10))
        self._extra_min = ctk.StringVar(value="15")
        ctk.CTkEntry(mr, textvariable=self._extra_min, width=80, font=FONTS["body"],
                     fg_color=COLORS["bg_input"], text_color=COLORS["text_primary"],
                     border_color=COLORS["border"], justify="center").pack(side="left")

        ctk.CTkLabel(atf, text="Reason (required):", font=FONTS["body"],
                     text_color=COLORS["text_secondary"]).pack(anchor="w", padx=20, pady=(10, 2))
        self._reason = ctk.StringVar()
        ctk.CTkEntry(atf, textvariable=self._reason, placeholder_text="Why do you need more time?",
                     font=FONTS["body"], fg_color=COLORS["bg_input"],
                     text_color=COLORS["text_primary"], border_color=COLORS["border"]
                     ).pack(fill="x", padx=20, pady=(0, 10))

        ctk.CTkButton(atf, text="Add Extra Time", font=FONTS["button"],
                      fg_color=COLORS["secondary"], hover_color=COLORS["accent"],
                      text_color=COLORS["text_primary"], corner_radius=10, height=38,
                      command=self._request_extra_time).pack(fill="x", padx=20, pady=(0, 15))

        self._status = ctk.CTkLabel(glow, text="", font=FONTS["body_small"],
                                    text_color=COLORS["danger"])
        self._status.pack(pady=(0, 5))

        if self._mode == MODE_TEST:
            ctk.CTkButton(glow, text="🔓  Unlock (Test Mode)", font=("Segoe UI", 16, "bold"),
                          fg_color=COLORS["success"], hover_color=COLORS["success_hover"],
                          text_color=COLORS["bg_primary"], corner_radius=12, height=50,
                          command=self._unlock).pack(fill="x", padx=30, pady=(5, 10))
        else:
            ctk.CTkButton(glow, text="🔓  Unlock (Enter Reason)", font=("Segoe UI", 14, "bold"),
                          fg_color=COLORS["warning"], hover_color=COLORS["accent_hover"],
                          text_color=COLORS["bg_primary"], corner_radius=12, height=45,
                          command=self._unlock_real).pack(fill="x", padx=30, pady=(5, 10))

        ctk.CTkLabel(glow, text="Press Ctrl + Shift + U to emergency exit",
                     font=FONTS["body_small"], text_color=COLORS["text_dim"]).pack(pady=(0, 15))

    def _keep_on_top(self):
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
        reason = self._reason.get().strip()
        if not reason:
            self._status.configure(text="⚠ Enter a reason to unlock.", text_color=COLORS["warning"])
            return
        if self._on_add_time:
            self._on_add_time(0, f"[UNLOCK] {reason}")
        self._unlock()

    def _request_extra_time(self):
        try:
            mins = int(self._extra_min.get())
            if mins <= 0 or mins > 480:
                raise ValueError
        except ValueError:
            self._status.configure(text="⚠ Enter valid minutes (1–480).", text_color=COLORS["danger"])
            return
        reason = self._reason.get().strip()
        if not reason:
            self._status.configure(text="⚠ Enter a reason for extra time.", text_color=COLORS["danger"])
            return
        self._status.configure(text=f"✅ Added {mins} minutes!", text_color=COLORS["success"])
        if self._on_add_time:
            self._on_add_time(mins, reason)
        self.after(1500, self._unlock)
