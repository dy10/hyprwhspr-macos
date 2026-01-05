"""
Whisper transcription for macOS
Uses pywhispercpp for local inference
"""

import re
import threading
from datetime import datetime
from pathlib import Path
from typing import Optional

import numpy as np


def _log(msg: str) -> None:
    """Print log message with timestamp"""
    ts = datetime.now().strftime('%H:%M:%S')
    print(f"{ts} {msg}")

# Regex to match sound effects in brackets or parentheses
# Matches: (sighs), [whooshing], (coughing), [music], etc.
SOUND_EFFECT_PATTERN = re.compile(
    r'[\[\(]\s*'  # Opening bracket or paren
    r'[a-zA-Z\s\-]+'  # Words (letters, spaces, hyphens)
    r'\s*[\]\)]',  # Closing bracket or paren
    re.IGNORECASE
)


class Transcriber:
    """Whisper-based speech-to-text transcription"""

    def __init__(self, config=None):
        self.config = config
        self._model = None
        self._lock = threading.Lock()
        self.ready = False

        # Model settings
        self.model_name = config.get('model', 'base.en') if config else 'base.en'
        self.threads = 4

    def initialize(self) -> bool:
        """Initialize the Whisper model"""
        try:
            # Import pywhispercpp
            try:
                from pywhispercpp.model import Model
            except ImportError:
                from pywhispercpp import Model

            # Check model exists - try multiple locations
            # macOS: ~/Library/Application Support/pywhispercpp/models/
            # Linux: ~/.local/share/pywhispercpp/models/
            possible_dirs = [
                Path.home() / 'Library' / 'Application Support' / 'pywhispercpp' / 'models',
                Path.home() / '.local' / 'share' / 'pywhispercpp' / 'models',
            ]

            model_file = None
            for models_dir in possible_dirs:
                candidate = models_dir / f"ggml-{self.model_name}.bin"
                if candidate.exists():
                    model_file = candidate
                    break

            if model_file is None:
                _log(f"[TRANSCRIBER] Model not found in any of:")
                for d in possible_dirs:
                    _log(f"  - {d}/ggml-{self.model_name}.bin")
                _log(f"[TRANSCRIBER] Download with: python -c \"from pywhispercpp.model import Model; Model('{self.model_name}')\"")
                return False

            # Load model
            self._model = Model(
                model=self.model_name,
                n_threads=self.threads,
                redirect_whispercpp_logs_to=None
            )

            _log(f"[TRANSCRIBER] Loaded model: {self.model_name}")
            self.ready = True
            return True

        except ImportError:
            _log("[TRANSCRIBER] pywhispercpp not installed")
            _log("[TRANSCRIBER] Install with: pip install pywhispercpp")
            return False
        except Exception as e:
            _log(f"[TRANSCRIBER] Init error: {e}")
            return False

    def transcribe(self, audio: np.ndarray, sample_rate: int = 16000) -> str:
        """
        Transcribe audio data

        Args:
            audio: Float32 numpy array of audio samples
            sample_rate: Sample rate (should be 16000)

        Returns:
            Transcribed text
        """
        if not self.ready or self._model is None:
            _log("[TRANSCRIBER] Not initialized")
            return ""

        if audio is None or len(audio) == 0:
            return ""

        # Validate audio
        if audio.dtype != np.float32:
            audio = audio.astype(np.float32)

        if not audio.flags['C_CONTIGUOUS']:
            audio = np.ascontiguousarray(audio)

        # Check for silence
        rms = np.sqrt(np.mean(audio ** 2))
        if rms < 1e-6:
            _log("[TRANSCRIBER] Audio too quiet (silence)")
            return ""

        try:
            with self._lock:
                # Get language from config
                language = None
                if self.config:
                    language = self.config.get('language')

                # Transcribe
                if language:
                    segments = self._model.transcribe(audio, language=language)
                else:
                    segments = self._model.transcribe(audio)

                # Combine segments
                text = ' '.join(seg.text for seg in segments).strip()

                # Remove sound effects like (sighs), [whooshing], etc.
                text = SOUND_EFFECT_PATTERN.sub('', text)
                text = ' '.join(text.split())  # Normalize whitespace

                # Filter hallucination markers (if entire text is just this)
                normalized = text.lower().replace('_', ' ').strip('[]() ')
                hallucinations = ('blank audio', 'blank', 'music', 'music playing', '')
                if normalized in hallucinations:
                    if text:
                        _log(f"[TRANSCRIBER] Hallucination filtered: {text}")
                    return ""

                return text

        except Exception as e:
            _log(f"[TRANSCRIBER] Error: {e}")
            return ""

    def get_available_models(self) -> list:
        """List downloaded models"""
        possible_dirs = [
            Path.home() / 'Library' / 'Application Support' / 'pywhispercpp' / 'models',
            Path.home() / '.local' / 'share' / 'pywhispercpp' / 'models',
        ]
        models = set()

        for models_dir in possible_dirs:
            if models_dir.exists():
                for f in models_dir.glob('ggml-*.bin'):
                    name = f.stem.replace('ggml-', '')
                    models.add(name)

        return sorted(models)
