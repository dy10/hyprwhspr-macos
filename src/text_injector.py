"""
Text injector for macOS using CGEvent key simulation
Copies text to clipboard and simulates Cmd+V
"""

import time
import re
import subprocess

import pyperclip
from Quartz import (
    CGEventCreateKeyboardEvent,
    CGEventPost,
    CGEventSetFlags,
    kCGHIDEventTap,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
)


# macOS key codes
KEY_V = 9
KEY_RETURN = 36


class TextInjector:
    """Injects text into active application via clipboard + paste"""

    def __init__(self, config=None):
        self.config = config

    def inject(self, text: str) -> bool:
        """
        Inject text into the active application

        Args:
            text: Text to inject

        Returns:
            True if successful
        """
        if not text or not text.strip():
            return True

        # Preprocess text
        processed = self._preprocess(text)

        try:
            # Copy to clipboard
            pyperclip.copy(processed)
            time.sleep(0.05)  # Brief delay for clipboard sync

            # Simulate Cmd+V
            self._simulate_paste()

            # Optional: send Enter if auto_submit enabled
            if self.config and self.config.get('auto_submit', False):
                time.sleep(0.05)
                self._simulate_enter()

            return True

        except Exception as e:
            print(f"Text injection failed: {e}")
            return False

    def _simulate_paste(self):
        """Simulate Cmd+V keystroke"""
        # Key down with Cmd modifier
        event_down = CGEventCreateKeyboardEvent(None, KEY_V, True)
        CGEventSetFlags(event_down, kCGEventFlagMaskCommand)
        CGEventPost(kCGHIDEventTap, event_down)

        time.sleep(0.01)

        # Key up
        event_up = CGEventCreateKeyboardEvent(None, KEY_V, False)
        CGEventSetFlags(event_up, kCGEventFlagMaskCommand)
        CGEventPost(kCGHIDEventTap, event_up)

    def _simulate_enter(self):
        """Simulate Enter keystroke"""
        event_down = CGEventCreateKeyboardEvent(None, KEY_RETURN, True)
        CGEventPost(kCGHIDEventTap, event_down)

        time.sleep(0.01)

        event_up = CGEventCreateKeyboardEvent(None, KEY_RETURN, False)
        CGEventPost(kCGHIDEventTap, event_up)

    def _preprocess(self, text: str) -> str:
        """Preprocess transcribed text"""
        # Remove extra whitespace
        processed = text.strip()

        # Apply word overrides
        if self.config:
            overrides = self.config.get('word_overrides', {})
            for original, replacement in overrides.items():
                pattern = r'\b' + re.escape(original) + r'\b'
                processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

        # Built-in speech-to-text replacements
        replacements = {
            r'\bperiod\b': '.',
            r'\bcomma\b': ',',
            r'\bquestion mark\b': '?',
            r'\bexclamation mark\b': '!',
            r'\bcolon\b': ':',
            r'\bsemicolon\b': ';',
            r'\bnew line\b': '\n',
            r'\btab\b': '\t',
        }

        for pattern, replacement in replacements.items():
            processed = re.sub(pattern, replacement, processed, flags=re.IGNORECASE)

        # Add trailing space for natural typing flow
        return processed + ' '
