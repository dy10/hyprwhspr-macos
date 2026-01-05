"""
Configuration manager for mac-hyprwhspr
"""

import json
from pathlib import Path
from typing import Any, Dict


class Config:
    """Manages application configuration"""

    # Default configuration
    DEFAULTS = {
        'shortcut': 'cmd+shift+d',  # Global hotkey
        'recording_mode': 'toggle',  # 'toggle' or 'push_to_talk'
        'model': 'base.en',          # Whisper model
        'language': None,            # Auto-detect
        'paste_mode': 'cmd',         # 'cmd' for Cmd+V
        'auto_submit': False,        # Send Enter after paste
        'word_overrides': {},        # Word replacements
        'whisper_prompt': 'Transcribe with proper capitalization.',
        # REST API settings (optional)
        'transcription_backend': 'local',  # 'local' or 'rest-api'
        'rest_endpoint_url': None,
        'rest_api_key': None,
        'rest_timeout': 30,
    }

    def __init__(self):
        # Config paths (macOS standard locations)
        self.config_dir = Path.home() / '.config' / 'whisper-dictate'
        self.config_file = self.config_dir / 'config.json'
        self.data_dir = Path.home() / '.local' / 'share' / 'whisper-dictate'

        # Current config
        self.config = self.DEFAULTS.copy()

        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.data_dir.mkdir(parents=True, exist_ok=True)

        # Load existing config
        self._load()

    def _load(self):
        """Load configuration from file"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    loaded = json.load(f)
                    self.config.update(loaded)
                print(f"Config loaded from {self.config_file}")
            else:
                print("Using default configuration")
                self.save()
        except Exception as e:
            print(f"Error loading config: {e}")

    def save(self) -> bool:
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving config: {e}")
            return False

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)

    def set(self, key: str, value: Any):
        """Set a configuration value"""
        self.config[key] = value

    def get_models_dir(self) -> Path:
        """Get the directory for Whisper models (macOS location)"""
        models_dir = Path.home() / 'Library' / 'Application Support' / 'pywhispercpp' / 'models'
        models_dir.mkdir(parents=True, exist_ok=True)
        return models_dir
