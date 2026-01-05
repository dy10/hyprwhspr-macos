# whisper-dictate

A fast, local speech-to-text dictation app for macOS. Double-tap Shift, speak, and watch your words appear in real-time.

![Platform](https://img.shields.io/badge/platform-macOS-blue)
![Python](https://img.shields.io/badge/python-3.10+-green)
![License](https://img.shields.io/badge/license-MIT-orange)

## Features

- **Double-tap Shift** to start/stop - no awkward key combos
- **Live transcription** - text appears as you pause speaking
- **100% local** - runs entirely on your Mac using Whisper, no cloud/API needed
- **Works everywhere** - types into any app (Slack, VS Code, browser, etc.)
- **Menu bar app** - unobtrusive, always accessible

## Demo

```
Double-tap Shift → 🔴 Recording...
"Hello world, this is a test" → ⏳ Processing...
→ Text appears in your active app: "Hello world, this is a test"
Keep speaking... (transcribes after each pause)
Double-tap Shift → 🎤 Stopped
```

## Installation

### Prerequisites

- macOS 12.0 (Monterey) or later
- Python 3.10+

### Setup

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/whisper-dictate.git
cd whisper-dictate

# Run setup (creates venv, installs deps, downloads Whisper model)
chmod +x setup.sh
./setup.sh
```

### Permissions

On first run, macOS will ask for:

1. **Accessibility** - for global keyboard shortcuts
   - System Preferences → Privacy & Security → Accessibility

2. **Microphone** - for audio recording
   - System Preferences → Privacy & Security → Microphone

## Usage

```bash
# Activate virtual environment
source ~/.local/share/whisper-dictate/venv/bin/activate

# Run menu bar app
python main.py

# Or run CLI mode (shows debug output)
python cli.py
```

### Controls

| Action | Trigger |
|--------|---------|
| Start dictation | Double-tap Shift |
| Stop dictation | Double-tap Shift |

That's it. No complex shortcuts to remember.

## How It Works

1. **Voice Activity Detection (VAD)** monitors your speech
2. When you pause (~0.7s of silence), the audio chunk is sent to Whisper
3. Transcribed text is immediately typed into your active application
4. Recording continues until you double-tap Shift again

## Configuration

Edit `~/.config/whisper-dictate/config.json`:

```json
{
  "model": "base.en",
  "auto_submit": false
}
```

### Options

| Setting | Description | Default |
|---------|-------------|---------|
| `model` | Whisper model size | `base.en` |
| `auto_submit` | Press Enter after each transcription | `false` |

### Whisper Models

| Model | Size | Speed | Accuracy |
|-------|------|-------|----------|
| `tiny.en` | 75 MB | Fastest | Good |
| `base.en` | 142 MB | Fast | Better |
| `small.en` | 466 MB | Medium | Great |
| `medium.en` | 1.5 GB | Slow | Excellent |

Download additional models:
```python
from pywhispercpp.model import Model
Model('small.en')  # Downloads automatically
```

## VAD Tuning

Adjust in `src/audio.py`:

```python
self.silence_threshold = 0.01   # Lower = more sensitive to silence
self.silence_duration = 0.7     # Seconds of silence before transcribing
self.min_chunk_duration = 0.3   # Minimum audio length to process
```

## Troubleshooting

### "Failed to create event tap"
Grant Accessibility permission in System Preferences → Privacy & Security → Accessibility

### "No microphone found"
Grant Microphone permission in System Preferences → Privacy & Security → Microphone

### Double-tap not detected
- Make sure you're tapping Shift quickly (within 0.4 seconds)
- Don't hold Shift - just tap twice
- Check that no other modifiers (Cmd, Alt, Ctrl) are pressed

### Model not found
```bash
python -c "from pywhispercpp.model import Model; Model('base.en')"
```

## Credits

This project is a macOS port inspired by [hyprwhspr](https://github.com/goodroot/hyprwhspr) - a speech-to-text dictation tool for Linux/Hyprland.

Key differences from the original:
- macOS-native using CoreGraphics (CGEvent) instead of evdev/ydotool
- Double-tap Shift shortcut instead of Super+Alt+D
- Live streaming VAD instead of record-then-transcribe
- Menu bar app using rumps instead of Waybar integration

## Tech Stack

- **[pywhispercpp](https://github.com/aarnphm/pywhispercpp)** - Whisper inference via whisper.cpp
- **[rumps](https://github.com/jaredks/rumps)** - macOS menu bar apps
- **[pyobjc](https://pyobjc.readthedocs.io/)** - macOS framework bindings
- **[sounddevice](https://python-sounddevice.readthedocs.io/)** - Audio capture

## License

MIT License - see [LICENSE](LICENSE)

## Contributing

PRs welcome! Some ideas:
- [ ] Configurable shortcut key
- [ ] Per-app language settings
- [ ] Audio feedback (beep on start/stop)
- [ ] Native macOS app bundle (.app)
