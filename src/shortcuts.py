"""
Global shortcuts for macOS using CGEvent tap
Requires Accessibility permissions in System Preferences
"""

import threading
from typing import Callable, Optional, Set

from Quartz import (
    CGEventTapCreate,
    CGEventTapEnable,
    CGEventMaskBit,
    CGEventGetFlags,
    CGEventGetIntegerValueField,
    kCGSessionEventTap,
    kCGHeadInsertEventTap,
    kCGEventKeyDown,
    kCGEventKeyUp,
    kCGEventFlagsChanged,
    kCGKeyboardEventKeycode,
    kCGEventFlagMaskCommand,
    kCGEventFlagMaskShift,
    kCGEventFlagMaskAlternate,
    kCGEventFlagMaskControl,
)
from Quartz import CFMachPortCreateRunLoopSource, CFRunLoopAddSource, CFRunLoopGetCurrent, CFRunLoopRun, CFRunLoopStop, kCFRunLoopCommonModes
import Quartz


# macOS key codes (from Events.h)
KEY_CODES = {
    'a': 0, 'b': 11, 'c': 8, 'd': 2, 'e': 14, 'f': 3, 'g': 5, 'h': 4,
    'i': 34, 'j': 38, 'k': 40, 'l': 37, 'm': 46, 'n': 45, 'o': 31, 'p': 35,
    'q': 12, 'r': 15, 's': 1, 't': 17, 'u': 32, 'v': 9, 'w': 13, 'x': 7,
    'y': 16, 'z': 6,
    '0': 29, '1': 18, '2': 19, '3': 20, '4': 21, '5': 23, '6': 22, '7': 26,
    '8': 28, '9': 25,
    'f1': 122, 'f2': 120, 'f3': 99, 'f4': 118, 'f5': 96, 'f6': 97,
    'f7': 98, 'f8': 100, 'f9': 101, 'f10': 109, 'f11': 103, 'f12': 111,
    'space': 49, 'return': 36, 'tab': 48, 'delete': 51, 'escape': 53,
    'left': 123, 'right': 124, 'down': 125, 'up': 126,
}

# Modifier flags
MODIFIERS = {
    'cmd': kCGEventFlagMaskCommand,
    'command': kCGEventFlagMaskCommand,
    'shift': kCGEventFlagMaskShift,
    'alt': kCGEventFlagMaskAlternate,
    'option': kCGEventFlagMaskAlternate,
    'ctrl': kCGEventFlagMaskControl,
    'control': kCGEventFlagMaskControl,
}

# Modifier key codes (for double-tap detection)
MODIFIER_KEYCODES = {
    'shift': (56, 60),      # Left shift, Right shift
    'cmd': (55, 54),        # Left cmd, Right cmd
    'alt': (58, 61),        # Left alt, Right alt
    'ctrl': (59, 62),       # Left ctrl, Right ctrl
}


class DoubleTapShortcut:
    """Detect double-tap on a modifier key (e.g., shift+shift)"""

    # Modifier flag masks
    MODIFIER_FLAGS = {
        'shift': kCGEventFlagMaskShift,
        'cmd': kCGEventFlagMaskCommand,
        'alt': kCGEventFlagMaskAlternate,
        'ctrl': kCGEventFlagMaskControl,
    }

    def __init__(
        self,
        modifier: str = 'shift',
        callback: Optional[Callable] = None,
        tap_interval: float = 0.4  # Max time between taps
    ):
        self.modifier = modifier.lower()
        self.callback = callback
        self.tap_interval = tap_interval

        # Get keycodes and flag for this modifier
        if self.modifier not in MODIFIER_KEYCODES:
            raise ValueError(f"Unknown modifier: {modifier}")
        self.target_keycodes = MODIFIER_KEYCODES[self.modifier]
        self.target_flag = self.MODIFIER_FLAGS.get(self.modifier, 0)

        # State
        self.is_running = False
        self._last_release_time = 0
        self._was_pressed = False

        # Threading
        self._tap = None
        self._run_loop = None
        self._thread = None

    def _event_callback(self, proxy, event_type, event, refcon):
        """CGEvent callback for double-tap detection"""
        import time

        try:
            # Modifier keys generate FlagsChanged events, not KeyDown/KeyUp
            if event_type == kCGEventFlagsChanged:
                keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                flags = CGEventGetFlags(event)

                # Check if it's our modifier key
                if keycode in self.target_keycodes:
                    # Check if modifier is now pressed or released by examining flags
                    is_pressed = bool(flags & self.target_flag)

                    if is_pressed:
                        # Modifier pressed
                        self._was_pressed = True
                    else:
                        # Modifier released
                        if self._was_pressed:
                            self._was_pressed = False

                            # Check no other modifiers are held
                            other_modifiers = (
                                kCGEventFlagMaskCommand |
                                kCGEventFlagMaskAlternate |
                                kCGEventFlagMaskControl |
                                kCGEventFlagMaskShift
                            ) & ~self.target_flag

                            if not (flags & other_modifiers):
                                now = time.time()
                                if now - self._last_release_time < self.tap_interval:
                                    # Double tap detected!
                                    print("[SHORTCUT] Double-tap detected!")
                                    self._last_release_time = 0  # Reset
                                    if self.callback:
                                        threading.Thread(target=self.callback, daemon=True).start()
                                else:
                                    self._last_release_time = now

        except Exception as e:
            print(f"Error in double-tap callback: {e}")

        return event

    def _run_loop_thread(self):
        """Run the event tap"""
        try:
            # Listen for FlagsChanged (modifier keys) not KeyDown/KeyUp
            event_mask = CGEventMaskBit(kCGEventFlagsChanged)

            self._tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                1,  # Passive - don't suppress events
                event_mask,
                self._event_callback,
                None
            )

            if self._tap is None:
                print("ERROR: Failed to create event tap for double-tap!")
                print("Grant Accessibility permission in System Preferences")
                return

            run_loop_source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
            self._run_loop = CFRunLoopGetCurrent()
            CFRunLoopAddSource(self._run_loop, run_loop_source, kCFRunLoopCommonModes)
            CGEventTapEnable(self._tap, True)

            print(f"[SHORTCUTS] Listening for double-tap {self.modifier}")
            CFRunLoopRun()

        except Exception as e:
            print(f"Error in double-tap thread: {e}")

    def start(self) -> bool:
        """Start listening"""
        if self.is_running:
            return True

        self._thread = threading.Thread(target=self._run_loop_thread, daemon=True)
        self._thread.start()

        import time
        time.sleep(0.2)

        if self._tap is None:
            return False

        self.is_running = True
        return True

    def stop(self):
        """Stop listening"""
        if not self.is_running:
            return

        self.is_running = False

        if self._run_loop:
            CFRunLoopStop(self._run_loop)

        if self._tap:
            CGEventTapEnable(self._tap, False)

        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self._tap = None
        self._run_loop = None


class GlobalShortcuts:
    """Global hotkey listener using CGEvent tap"""

    def __init__(
        self,
        shortcut: str,
        callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None
    ):
        self.shortcut = shortcut
        self.callback = callback
        self.release_callback = release_callback

        # Parse shortcut
        self.target_modifiers = 0
        self.target_keycode = None
        self._parse_shortcut(shortcut)

        # State
        self.is_running = False
        self.combination_active = False
        self._current_modifiers = 0

        # Threading
        self._tap = None
        self._run_loop = None
        self._thread = None
        self._stop_event = threading.Event()

    def _parse_shortcut(self, shortcut: str):
        """Parse shortcut string like 'cmd+shift+d' into modifiers and keycode"""
        parts = shortcut.lower().replace(' ', '').split('+')

        for part in parts:
            if part in MODIFIERS:
                self.target_modifiers |= MODIFIERS[part]
            elif part in KEY_CODES:
                self.target_keycode = KEY_CODES[part]
            else:
                print(f"Warning: Unknown key '{part}' in shortcut")

        if self.target_keycode is None:
            print(f"Warning: No key found in shortcut '{shortcut}', defaulting to 'd'")
            self.target_keycode = KEY_CODES['d']

    def _event_callback(self, proxy, event_type, event, refcon):
        """CGEvent tap callback"""
        try:
            if event_type in (kCGEventKeyDown, kCGEventKeyUp):
                keycode = CGEventGetIntegerValueField(event, kCGKeyboardEventKeycode)
                flags = CGEventGetFlags(event)

                # Mask out non-modifier bits
                modifier_mask = (
                    kCGEventFlagMaskCommand |
                    kCGEventFlagMaskShift |
                    kCGEventFlagMaskAlternate |
                    kCGEventFlagMaskControl
                )
                current_modifiers = flags & modifier_mask

                if event_type == kCGEventKeyDown:
                    # Check if this completes our shortcut
                    if (keycode == self.target_keycode and
                            current_modifiers == self.target_modifiers):
                        if not self.combination_active:
                            self.combination_active = True
                            self._trigger_callback()
                        # Suppress the event (don't pass to other apps)
                        return None

                elif event_type == kCGEventKeyUp:
                    if keycode == self.target_keycode and self.combination_active:
                        self.combination_active = False
                        self._trigger_release_callback()
                        return None

            elif event_type == kCGEventFlagsChanged:
                # Track modifier changes
                flags = CGEventGetFlags(event)
                modifier_mask = (
                    kCGEventFlagMaskCommand |
                    kCGEventFlagMaskShift |
                    kCGEventFlagMaskAlternate |
                    kCGEventFlagMaskControl
                )
                self._current_modifiers = flags & modifier_mask

                # If modifiers released while combination active, trigger release
                if self.combination_active:
                    if (self._current_modifiers & self.target_modifiers) != self.target_modifiers:
                        self.combination_active = False
                        self._trigger_release_callback()

        except Exception as e:
            print(f"Error in event callback: {e}")

        return event

    def _trigger_callback(self):
        """Trigger the press callback in a separate thread"""
        if self.callback:
            threading.Thread(target=self.callback, daemon=True).start()

    def _trigger_release_callback(self):
        """Trigger the release callback in a separate thread"""
        if self.release_callback:
            threading.Thread(target=self.release_callback, daemon=True).start()

    def _run_loop_thread(self):
        """Run the event tap in a dedicated thread"""
        try:
            # Create event tap
            event_mask = (
                CGEventMaskBit(kCGEventKeyDown) |
                CGEventMaskBit(kCGEventKeyUp) |
                CGEventMaskBit(kCGEventFlagsChanged)
            )

            self._tap = CGEventTapCreate(
                kCGSessionEventTap,
                kCGHeadInsertEventTap,
                0,  # Not passive - we may suppress events
                event_mask,
                self._event_callback,
                None
            )

            if self._tap is None:
                print("ERROR: Failed to create event tap!")
                print("Please grant Accessibility permission:")
                print("  System Preferences -> Privacy & Security -> Accessibility")
                return

            # Create run loop source
            run_loop_source = CFMachPortCreateRunLoopSource(None, self._tap, 0)
            self._run_loop = CFRunLoopGetCurrent()
            CFRunLoopAddSource(self._run_loop, run_loop_source, kCFRunLoopCommonModes)

            # Enable the tap
            CGEventTapEnable(self._tap, True)

            print(f"[SHORTCUTS] Listening for {self.shortcut}")

            # Run the loop
            CFRunLoopRun()

        except Exception as e:
            print(f"Error in event tap thread: {e}")

    def start(self) -> bool:
        """Start listening for shortcuts"""
        if self.is_running:
            return True

        self._stop_event.clear()
        self._thread = threading.Thread(target=self._run_loop_thread, daemon=True)
        self._thread.start()

        # Give it a moment to initialize
        import time
        time.sleep(0.2)

        if self._tap is None:
            return False

        self.is_running = True
        return True

    def stop(self):
        """Stop listening for shortcuts"""
        if not self.is_running:
            return

        self.is_running = False

        # Stop the run loop
        if self._run_loop:
            CFRunLoopStop(self._run_loop)

        # Disable the tap
        if self._tap:
            CGEventTapEnable(self._tap, False)

        # Wait for thread
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)

        self._tap = None
        self._run_loop = None

    def is_active(self) -> bool:
        """Check if shortcuts are active"""
        return self.is_running and self._tap is not None
