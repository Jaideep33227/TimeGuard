# 🎯 FocusLock — Focus Timer + PC Lock System

A Windows desktop app that helps you stay focused with a countdown timer and a safe screen lock overlay.

## Features

- **Countdown Timer** — Set custom hours/minutes with quick presets (25m, 45m, 1h, 2h, 3h)
- **Safe Lock Screen** — Full-screen overlay when timer expires (always reversible!)
- **Test Mode** (default) — Unlock button always visible, no risk of lockout
- **Real Mode** — Requires a reason to unlock (still fully safe)
- **Add Extra Time** — Request more time with a logged reason
- **XP & Leveling** — Earn XP for focus time, level up through 10 ranks
- **Daily Stats** — Track focus minutes, sessions, streaks
- **Crash Recovery** — Timer state saved every 30s, resumes after restart
- **Windows Startup** — Optional auto-start with Windows
- **Single Instance** — Prevents duplicate app processes

## Safety Guarantees

- ✅ **NEVER** uses system-level locking (`LockWorkStation`)
- ✅ **NEVER** disables Task Manager
- ✅ `Ctrl+Shift+U` **ALWAYS** exits the lock screen
- ✅ Unlock button always visible in Test Mode
- ✅ Everything is fully reversible

## Requirements

- Python 3.10+
- Windows OS

## Setup & Run

```bash
# 1. Navigate to the project
cd focus-timer

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run the app
python main.py
```

## File Structure

```
focus-timer/
├── main.py           # Entry point (single-instance check)
├── app.py            # Main UI + controller
├── timer_engine.py   # Background timer logic
├── lock_screen.py    # Full-screen lock overlay
├── storage.py        # JSON persistence (state, reasons, stats)
├── startup.py        # Windows startup registry management
├── constants.py      # Colors, fonts, XP config, paths
├── requirements.txt  # Dependencies
├── README.md         # This file
└── data/             # Created at runtime
    ├── state.json    # Timer state (auto-saved)
    ├── reasons.json  # Extra time request log
    └── stats.json    # XP, streaks, daily stats
```

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| `Ctrl+Shift+U` | Emergency exit from lock screen |

## XP Leveling System

| Level | XP | Title |
|-------|----|-------|
| 1 | 0 | 🌱 Beginner |
| 2 | 100 | 🔰 Focused Novice |
| 3 | 300 | ⏰ Time Keeper |
| 4 | 600 | 💪 Deep Worker |
| 5 | 1000 | 🌊 Flow Master |
| 6 | 1500 | 🧘 Zen Coder |
| 7 | 2500 | ⚔️ Focus Warrior |
| 8 | 4000 | 👑 Time Lord |
| 9 | 6000 | 🏆 Productivity Legend |
| 10 | 10000 | ✨ Transcended |
