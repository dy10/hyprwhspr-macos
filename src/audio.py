"""
Audio capture for macOS using sounddevice (PortAudio)
Supports VAD-based streaming for live transcription
"""

import threading
import time
from datetime import datetime
from typing import Optional, Callable, List

import numpy as np
import sounddevice as sd


def _log(msg: str) -> None:
    """Print log message with timestamp"""
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"{ts} {msg}")


class AudioCapture:
    """Handles audio recording with optional VAD streaming"""

    def __init__(self, device_id: Optional[int] = None):
        # Audio config (Whisper prefers 16kHz mono)
        self.sample_rate = 16000
        self.channels = 1
        self.dtype = np.float32
        self.chunk_size = 1024

        # State
        self.is_recording = False
        self.audio_data = []
        self.current_level = 0.0

        # Device
        self.device_id = device_id

        # Threading
        self._stream = None
        self._lock = threading.Lock()

        # VAD settings
        self.vad_enabled = False
        self.silence_threshold = 0.01      # RMS level below this = silence
        self.silence_duration = 0.7        # Seconds of silence to trigger chunk
        self.min_chunk_duration = 0.3      # Minimum audio to transcribe
        self._vad_callback = None
        self._silence_start = None
        self._chunk_buffer = []

        # Initialize
        self._init_device()

    def _init_device(self):
        """Initialize audio device"""
        try:
            sd.default.samplerate = self.sample_rate
            sd.default.channels = self.channels
            sd.default.dtype = self.dtype

            if self.device_id is not None:
                sd.default.device = (self.device_id, None)

            # Test device
            device_info = sd.query_devices(kind='input')
            _log(f"[AUDIO] Using: {device_info['name']}")

        except Exception as e:
            _log(f"[AUDIO] Init error: {e}")

    @staticmethod
    def list_devices():
        """List available input devices"""
        devices = []
        for i, dev in enumerate(sd.query_devices()):
            if dev['max_input_channels'] > 0:
                devices.append({
                    'id': i,
                    'name': dev['name'],
                    'channels': dev['max_input_channels'],
                })
        return devices

    def is_available(self) -> bool:
        """Check if audio capture is available"""
        try:
            sd.query_devices(kind='input')
            return True
        except:
            return False

    def start_recording(
        self,
        streaming_callback: Optional[Callable] = None,
        vad_callback: Optional[Callable[[np.ndarray], None]] = None
    ) -> bool:
        """
        Start recording audio

        Args:
            streaming_callback: Called with each audio chunk (for raw streaming)
            vad_callback: Called with audio when silence detected (for VAD mode)
        """
        if self.is_recording:
            return True

        if not self.is_available():
            _log("[AUDIO] No input device available")
            return False

        try:
            with self._lock:
                self.audio_data = []
                self._chunk_buffer = []
                self._silence_start = None
                self.is_recording = True
                self.vad_enabled = vad_callback is not None
                self._vad_callback = vad_callback

            def callback(indata, frames, time_info, status):
                if status:
                    _log(f"[AUDIO] Status: {status}")

                with self._lock:
                    if not self.is_recording:
                        return

                    chunk = indata[:, 0].copy()
                    self.audio_data.append(chunk)

                    # Calculate RMS level
                    rms = np.sqrt(np.mean(chunk ** 2))
                    self.current_level = rms

                    # VAD processing
                    if self.vad_enabled and self._vad_callback:
                        self._chunk_buffer.append(chunk)

                        if rms < self.silence_threshold:
                            # Silence detected
                            if self._silence_start is None:
                                self._silence_start = time.time()
                            elif time.time() - self._silence_start >= self.silence_duration:
                                # Enough silence - trigger callback with buffered audio
                                self._flush_vad_buffer()
                        else:
                            # Speech detected - reset silence timer
                            self._silence_start = None

                    # Raw streaming callback
                    if streaming_callback:
                        try:
                            streaming_callback(chunk)
                        except Exception as e:
                            _log(f"[AUDIO] Streaming callback error: {e}")

            self._stream = sd.InputStream(
                samplerate=self.sample_rate,
                channels=self.channels,
                dtype=self.dtype,
                blocksize=self.chunk_size,
                callback=callback
            )
            self._stream.start()

            return True

        except Exception as e:
            _log(f"[AUDIO] Start error: {e}")
            self.is_recording = False
            return False

    def _flush_vad_buffer(self):
        """Flush VAD buffer and call callback"""
        if not self._chunk_buffer:
            return

        # Concatenate buffered audio
        audio = np.concatenate(self._chunk_buffer)
        duration = len(audio) / self.sample_rate

        # Clear buffer and reset silence
        self._chunk_buffer = []
        self._silence_start = None

        # Only transcribe if long enough
        if duration >= self.min_chunk_duration:
            if self._vad_callback:
                try:
                    # Run callback in separate thread to not block audio
                    threading.Thread(
                        target=self._vad_callback,
                        args=(audio,),
                        daemon=True
                    ).start()
                except Exception as e:
                    _log(f"[AUDIO] VAD callback error: {e}")

    def stop_recording(self) -> Optional[np.ndarray]:
        """Stop recording and return audio data"""
        if not self.is_recording:
            return None

        # Flush any remaining VAD buffer
        with self._lock:
            if self.vad_enabled and self._chunk_buffer:
                self._flush_vad_buffer()
            self.is_recording = False
            self.vad_enabled = False

        # Stop stream
        if self._stream:
            try:
                self._stream.stop()
                self._stream.close()
            except:
                pass
            self._stream = None

        # Return concatenated audio
        with self._lock:
            if self.audio_data:
                audio = np.concatenate(self.audio_data)
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)
                return audio

        return None

    def get_level(self) -> float:
        """Get current audio level (0.0 to 1.0)"""
        return min(1.0, self.current_level * 10)
