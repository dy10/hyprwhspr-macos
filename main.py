#!/usr/bin/env python3
"""
mac-hyprwhspr - macOS Speech-to-Text Dictation
Menu bar app with global hotkey support
Uses VAD for live streaming transcription
"""

import sys
import threading
import time
from datetime import datetime

import rumps


def _log(msg: str) -> None:
    """Print log message with timestamp"""
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"{ts} {msg}")

from src.config import Config
from src.shortcuts import DoubleTapShortcut
from src.audio import AudioCapture
from src.transcriber import Transcriber
from src.text_injector import TextInjector


class MacHyprwhspr(rumps.App):
    """Menu bar application for speech-to-text dictation"""

    def __init__(self):
        super().__init__(
            name="hyprwhspr",
            title="🎤",  # Emoji indicator
            icon=None,
            quit_button=None
        )

        # Components
        self.config = Config()
        self.audio = AudioCapture()
        self.transcriber = Transcriber(self.config)
        self.injector = TextInjector(self.config)
        self.shortcuts = None

        # State
        self.is_recording = False
        self.is_processing = False
        self._lock = threading.Lock()

        # Build menu items
        self._record_btn = rumps.MenuItem("Start Recording (Shift+Shift)", callback=self.toggle_recording)
        self._status_item = rumps.MenuItem("Status: Idle", callback=None)

        # Build menu
        self.menu = [
            self._record_btn,
            None,
            self._status_item,
            None,
            rumps.MenuItem("Settings...", callback=self.show_settings),
            rumps.MenuItem("Quit", callback=self.quit_app),
        ]

        # Initialize
        self._init_components()

    def _init_components(self):
        """Initialize all components"""
        # Check audio
        if not self.audio.is_available():
            rumps.alert(
                title="Audio Error",
                message="No microphone found. Please check your audio settings."
            )
            return

        # Initialize transcriber
        if not self.transcriber.initialize():
            rumps.alert(
                title="Model Error",
                message=f"Failed to load Whisper model '{self.config.get('model')}'.\n\n"
                        f"Download it first:\npython -c \"from pywhispercpp.model import Model; Model('{self.config.get('model')}')\""
            )
            return

        # Setup double-tap shift shortcut
        self.shortcuts = DoubleTapShortcut(
            modifier='shift',
            callback=self._on_shortcut,
            tap_interval=0.4
        )

        if not self.shortcuts.start():
            rumps.alert(
                title="Accessibility Permission Required",
                message="mac-hyprwhspr needs Accessibility permission.\n\n"
                        "Grant access in:\nSystem Preferences -> Privacy & Security -> Accessibility"
            )
            return

        self._update_status("Ready")
        _log("[APP] Ready - Double-tap Shift to start/stop dictation")

    def _on_shortcut(self):
        """Handle double-shift shortcut"""
        self.toggle_recording(None)

    def toggle_recording(self, sender):
        """Toggle recording state"""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start voice recording with VAD streaming"""
        with self._lock:
            if self.is_recording:
                return
            self.is_recording = True

        try:
            # Start recording with VAD callback for live transcription
            if self.audio.start_recording(vad_callback=self._on_speech_chunk):
                self._update_icon("recording")
                self._update_status("Listening...")
                self._record_btn.title = "Stop Recording (Shift+Shift)"
                _log("[APP] Recording started - speak now")
            else:
                self.is_recording = False
                self._update_status("Error: Mic unavailable")

        except Exception as e:
            _log(f"[APP] Start recording error: {e}")
            self.is_recording = False

    def _on_speech_chunk(self, audio_data):
        """Called when VAD detects end of speech - transcribe and inject"""
        if not self.is_recording:
            return

        try:
            self._update_icon("processing")

            # Transcribe
            text = self.transcriber.transcribe(audio_data)

            if text and text.strip():
                _log(f"[APP] Transcribed: {text}")
                self.injector.inject(text)
                self._update_status(f"✓ {text[:25]}...")
            else:
                self._update_status("...")

            # Back to recording state
            if self.is_recording:
                self._update_icon("recording")

        except Exception as e:
            _log(f"[APP] Transcription error: {e}")

    def _stop_recording(self):
        """Stop recording"""
        with self._lock:
            if not self.is_recording:
                return
            self.is_recording = False

        self._update_icon("idle")
        self._update_status("Stopped")
        self._record_btn.title = "Start Recording (Shift+Shift)"

        # Stop audio (this will flush any remaining buffer)
        self.audio.stop_recording()
        _log("[APP] Recording stopped")

    def _update_icon(self, state: str):
        """Update menu bar icon/title"""
        titles = {
            "idle": "🎤",
            "recording": "🔴",
            "processing": "⏳",
        }
        self.title = titles.get(state, "🎤")

    def _update_status(self, status: str):
        """Update status menu item"""
        self._status_item.title = f"Status: {status}"

    def show_settings(self, _):
        """Show settings dialog"""
        model = self.config.get('model', 'base.en')

        message = (
            f"Current Settings:\n\n"
            f"Shortcut: Double-tap Shift\n"
            f"Model: {model}\n"
            f"Mode: Live streaming (VAD)\n\n"
            f"Edit config at:\n{self.config.config_file}"
        )

        rumps.alert(title="Settings", message=message)

    def quit_app(self, _):
        """Quit the application"""
        if self.is_recording:
            self._stop_recording()
        if self.shortcuts:
            self.shortcuts.stop()
        rumps.quit_application()


def main():
    """Entry point"""
    _log("mac-hyprwhspr starting...")
    _log("[APP] Shortcut: Double-tap Shift to toggle recording")
    _log("[APP] Mode: Live transcription (speaks as you pause)")

    app = MacHyprwhspr()
    app.run()


if __name__ == "__main__":
    main()
