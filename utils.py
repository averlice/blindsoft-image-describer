import json
import os

SETTINGS_FILE = "settings.json"

DEFAULT_SETTINGS = {
    "prefix": "alii!",
    "error_log_channel_id": None,
    "error_log_dm": False,
    "auto_update": True
}

def load_settings():
    """Loads settings from the JSON file. Returns defaults if file is missing/corrupt."""
    if not os.path.exists(SETTINGS_FILE):
        save_settings(DEFAULT_SETTINGS)
        return DEFAULT_SETTINGS
    
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
            # Ensure all keys exist (merge with defaults)
            for key, value in DEFAULT_SETTINGS.items():
                if key not in data:
                    data[key] = value
            return data
    except Exception as e:
        print(f"Error loading settings: {e}")
        return DEFAULT_SETTINGS

def save_settings(settings):
    """Saves the settings dictionary to the JSON file."""
    try:
        with open(SETTINGS_FILE, 'w') as f:
            json.dump(settings, f, indent=4)
    except Exception as e:
        print(f"Error saving settings: {e}")

def get_setting(key):
    """Helper to get a single setting."""
    settings = load_settings()
    return settings.get(key, DEFAULT_SETTINGS.get(key))

def update_setting(key, value):
    """Helper to update a single setting."""
    settings = load_settings()
    settings[key] = value
    save_settings(settings)
