#!/usr/bin/env python3
"""
mac-hyprwhspr CLI mode
Run without menu bar for testing/debugging
"""

import sys
import time
import signal

from src.config import Config
from src.shortcuts import DoubleTapShortcut
from src.audio import AudioCapture
from src.transcriber import Transcriber
from src.text_injector import TextInjector


class CLI:
    """Command-line interface for mac-hyprwhspr"""

    def __init__(self):
        self.config = Config()
        self.audio = AudioCapture()
        self.transcriber = Transcriber(self.config)
        self.injector = TextInjector(self.config)
        self.shortcuts = None

        self.is_recording = False
        self.running = True

    def setup(self) -> bool:
        """Initialize components"""
        print("[CLI] Initializing...")

        # Check audio
        if not self.audio.is_available():
            print("[ERROR] No microphone found")
            return False

        # Initialize transcriber
        if not self.transcriber.initialize():
            print("[ERROR] Failed to initialize Whisper model")
            return False

        # Setup double-tap shift shortcut
        self.shortcuts = DoubleTapShortcut(
            modifier='shift',
            callback=self._on_shortcut,
            tap_interval=0.4
        )

        if not self.shortcuts.start():
            print("[ERROR] Failed to start shortcuts")
            print("[ERROR] Grant Accessibility permission in System Preferences")
            return False

        return True

    def _on_shortcut(self):
        """Handle double-shift shortcut"""
        if self.is_recording:
            self._stop_recording()
        else:
            self._start_recording()

    def _start_recording(self):
        """Start recording with VAD"""
        if self.is_recording:
            return

        self.is_recording = True
        print("\n🔴 Recording... (double-tap Shift to stop)")

        if not self.audio.start_recording(vad_callback=self._on_speech_chunk):
            print("[ERROR] Failed to start recording")
            self.is_recording = False

    def _on_speech_chunk(self, audio_data):
        """Called when VAD detects pause - transcribe and inject"""
        if not self.is_recording:
            return

        print("⏳ Processing...", end=" ", flush=True)

        text = self.transcriber.transcribe(audio_data)

        if text and text.strip():
            print(f"✓ {text}")
            self.injector.inject(text)
        else:
            print("(no speech)")

    def _stop_recording(self):
        """Stop recording"""
        if not self.is_recording:
            return

        self.is_recording = False
        self.audio.stop_recording()
        print("🎤 Stopped")

    def run(self):
        """Main loop"""
        print("\n[CLI] Ready!")
        print("[CLI] Double-tap Shift to start/stop recording")
        print("[CLI] Ctrl+C to quit\n")

        def handle_sigint(sig, frame):
            print("\n[CLI] Shutting down...")
            self.running = False

        signal.signal(signal.SIGINT, handle_sigint)

        while self.running:
            time.sleep(0.1)

        self.cleanup()

    def cleanup(self):
        """Cleanup resources"""
        if self.is_recording:
            self._stop_recording()
        if self.shortcuts:
            self.shortcuts.stop()
        print("[CLI] Goodbye!")


def main():
    cli = CLI()

    if not cli.setup():
        sys.exit(1)

    cli.run()


if __name__ == "__main__":
    main()
