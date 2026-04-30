"""
constants.py — App-wide constants, color palette, XP configuration, and file paths.
"""

import os
import sys

# ─── App Identity ─────────────────────────────────────────────────────────────
APP_NAME = "FocusLock"
APP_VERSION = "1.0.0"
WINDOW_TITLE = f"🎯 {APP_NAME} v{APP_VERSION}"
WINDOW_SIZE = "520x820"

# ─── File Paths ───────────────────────────────────────────────────────────────
# Data directory: stored next to the script (or exe) for portability
if getattr(sys, 'frozen', False):
    BASE_DIR = os.path.dirname(sys.executable)
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

DATA_DIR = os.path.join(BASE_DIR, "data")
STATE_FILE = os.path.join(DATA_DIR, "state.json")
REASONS_FILE = os.path.join(DATA_DIR, "reasons.json")
STATS_FILE = os.path.join(DATA_DIR, "stats.json")
LOCK_FILE = os.path.join(DATA_DIR, ".focuslock.lock")

# Ensure data directory exists
os.makedirs(DATA_DIR, exist_ok=True)

# ─── Timer Defaults ──────────────────────────────────────────────────────────
DEFAULT_HOURS = 1
DEFAULT_MINUTES = 0
MIN_TIMER_SECONDS = 60          # Minimum 1 minute
MAX_TIMER_SECONDS = 12 * 3600   # Maximum 12 hours
AUTO_SAVE_INTERVAL = 30         # Save state every 30 seconds

# ─── Modes ────────────────────────────────────────────────────────────────────
MODE_TEST = "test"
MODE_REAL = "real"
DEFAULT_MODE = MODE_TEST

# ─── Color Palette (Dark Theme) ──────────────────────────────────────────────
COLORS = {
    "bg_primary":     "#0f0f1a",      # Deep dark background
    "bg_secondary":   "#1a1a2e",      # Card / section background
    "bg_card":        "#16213e",      # Elevated card background
    "bg_input":       "#0d1b2a",      # Input field background
    "accent":         "#e94560",      # Vibrant coral-red (primary accent)
    "accent_hover":   "#ff6b81",      # Lighter accent for hover
    "accent_dark":    "#c73e54",      # Darker accent for press
    "secondary":      "#0f3460",      # Medium blue (secondary accent)
    "text_primary":   "#eaeaea",      # Primary text
    "text_secondary": "#8892b0",      # Muted text
    "text_dim":       "#4a5568",      # Very muted text
    "success":        "#4ecca3",      # Mint green
    "success_hover":  "#6ee7b7",      # Lighter green
    "warning":        "#f0a500",      # Amber
    "danger":         "#ff4757",      # Red for danger
    "border":         "#2a2a4a",      # Subtle border
    "progress_bg":    "#1e1e3a",      # Progress bar track
    "progress_fill":  "#e94560",      # Progress bar fill
    "glow":           "#e9456033",    # Glow effect (semi-transparent)
}

# ─── Font Configuration ──────────────────────────────────────────────────────
FONTS = {
    "title":          ("Segoe UI", 20, "bold"),
    "timer_large":    ("Consolas", 56, "bold"),
    "timer_label":    ("Segoe UI", 13),
    "heading":        ("Segoe UI", 15, "bold"),
    "subheading":     ("Segoe UI", 12, "bold"),
    "body":           ("Segoe UI", 12),
    "body_small":     ("Segoe UI", 10),
    "button":         ("Segoe UI", 12, "bold"),
    "stat_value":     ("Segoe UI", 16, "bold"),
    "stat_label":     ("Segoe UI", 10),
    "badge":          ("Segoe UI", 9, "bold"),
}

# ─── XP / Reward System ──────────────────────────────────────────────────────
XP_PER_MINUTE = 2              # XP earned per minute of focus
XP_SESSION_BONUS = 50          # Bonus XP for completing a full session
XP_STREAK_MULTIPLIER = 25     # XP per streak day bonus

# Level thresholds and titles
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
    """Get current level info based on total XP."""
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
            next_threshold = LEVELS[i + 1][0] if i + 1 < len(LEVELS) else threshold
        else:
            break

    return {
        "level": level,
        "title": title,
        "emoji": emoji,
        "total_xp": total_xp,
        "xp_in_level": total_xp - current_threshold,
        "xp_for_next": next_threshold - current_threshold,
        "progress": (total_xp - current_threshold) / max(1, next_threshold - current_threshold),
    }

# ─── Notification ─────────────────────────────────────────────────────────────
BEEP_FREQUENCY = 800   # Hz
BEEP_DURATION = 500    # ms
BEEP_COUNT = 3         # Number of beeps when timer ends
