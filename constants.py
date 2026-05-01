"""
constants.py — App-wide constants, color palette, XP config, and file paths.
Central configuration for the entire FocusLock application.
"""

import os
import sys

# ─── App Identity ─────────────────────────────────────────────────────────────
APP_NAME = "FocusLock"
APP_VERSION = "2.0.0"
WINDOW_TITLE = f"🎯 {APP_NAME}"
WINDOW_SIZE = "540x780"

# ─── File Paths ───────────────────────────────────────────────────────────────
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
REASONS_FILE = os.path.join(DATA_DIR, "reasons.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
LOCK_FILE = os.path.join(DATA_DIR, ".focuslock.lock")

os.makedirs(DATA_DIR, exist_ok=True)

# ─── Timer ────────────────────────────────────────────────────────────────────
DEFAULT_HOURS = 1
DEFAULT_MINUTES = 0
MIN_TIMER_SECONDS = 60
MAX_TIMER_SECONDS = 12 * 3600
AUTO_SAVE_INTERVAL = 30

# ─── Modes ────────────────────────────────────────────────────────────────────
MODE_TEST = "test"
MODE_REAL = "real"
MODE_HARDCORE = "hardcore"
DEFAULT_MODE = MODE_TEST

# ─── Color Palette ────────────────────────────────────────────────────────────
COLORS = {
    # Backgrounds
    "bg_primary":     "#0b0b14",
    "bg_secondary":   "#12122a",
    "bg_card":        "#1a1a3e",
    "bg_input":       "#0d0d20",
    "bg_nav":         "#0e0e1c",

    # Accents
    "accent":         "#e94560",
    "accent_hover":   "#ff6b81",
    "accent_dark":    "#c73e54",
    "secondary":      "#0f3460",
    "secondary_hover":"#1a4a80",

    # Text
    "text_primary":   "#eaeaea",
    "text_secondary": "#8892b0",
    "text_dim":       "#4a5568",

    # Semantic
    "success":        "#4ecca3",
    "success_hover":  "#6ee7b7",
    "warning":        "#f0a500",
    "danger":         "#ff4757",

    # UI elements
    "border":         "#2a2a4a",
    "progress_bg":    "#1e1e3a",
    "progress_fill":  "#e94560",
    "nav_active":     "#e94560",
    "nav_inactive":   "#4a5568",
}

# ─── Fonts ────────────────────────────────────────────────────────────────────
FONTS = {
    "title":          ("Segoe UI", 22, "bold"),
    "timer_large":    ("Consolas", 52, "bold"),
    "timer_label":    ("Segoe UI", 13),
    "heading":        ("Segoe UI", 16, "bold"),
    "subheading":     ("Segoe UI", 12, "bold"),
    "body":           ("Segoe UI", 12),
    "body_small":     ("Segoe UI", 10),
    "button":         ("Segoe UI", 12, "bold"),
    "stat_value":     ("Segoe UI", 18, "bold"),
    "stat_label":     ("Segoe UI", 10),
    "badge":          ("Segoe UI", 9, "bold"),
    "nav":            ("Segoe UI", 11, "bold"),
    "big_emoji":      ("Segoe UI Emoji", 56),
    "xp_popup":       ("Segoe UI", 24, "bold"),
}

# ─── XP System ────────────────────────────────────────────────────────────────
XP_PER_MINUTE = 2
XP_SESSION_BONUS = 50
XP_STREAK_MULTIPLIER = 25

LEVELS = [
    (0,     "Beginner",             "🌱"),
    (100,   "Focused Novice",       "🔰"),
    (300,   "Time Keeper",          "⏰"),
    (600,   "Deep Worker",          "💪"),
    (1000,  "Flow Master",          "🌊"),
    (1500,  "Zen Coder",            "🧘"),
    (2500,  "Focus Warrior",        "⚔️"),
    (4000,  "Time Lord",            "👑"),
    (6000,  "Productivity Legend",  "🏆"),
    (10000, "Transcended",          "✨"),
]


def get_level_info(total_xp: int) -> dict:
    """Calculate level, title, emoji, and progress from total XP."""
    level = 1
    title = LEVELS[0][1]
    emoji = LEVELS[0][2]
    current_threshold = 0
    next_threshold = LEVELS[1][0] if len(LEVELS) > 1 else total_xp

    for i, (threshold, name, icon) in enumerate(LEVELS):
        if total_xp >= threshold:
            level = i + 1
            title = name
            emoji = icon
            current_threshold = threshold
            if i + 1 < len(LEVELS):
                next_threshold = LEVELS[i + 1][0]
            else:
                next_threshold = threshold  # Max level
        else:
            break

    xp_for_next = max(1, next_threshold - current_threshold)
    xp_in_level = total_xp - current_threshold

    return {
        "level": level,
        "title": title,
        "emoji": emoji,
        "total_xp": total_xp,
        "xp_in_level": xp_in_level,
        "xp_for_next": xp_for_next,
        "progress": min(1.0, xp_in_level / xp_for_next),
    }


# ─── Notification ─────────────────────────────────────────────────────────────
BEEP_FREQUENCY = 800
BEEP_DURATION = 400
BEEP_COUNT = 3

# ─── Navigation Tabs ─────────────────────────────────────────────────────────
TAB_TIMER = "timer"
TAB_STATS = "stats"
TAB_SETTINGS = "settings"
