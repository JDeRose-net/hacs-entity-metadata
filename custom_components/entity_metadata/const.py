from __future__ import annotations
from pathlib import Path
from homeassistant.core import HomeAssistant

DOMAIN = "entity_metadata"

# New default location under /config/etc/
REL_BASE = Path("etc") / DOMAIN
OVERRIDES_FILENAME = "overrides.yaml"
BACKUPS_DIRNAME = "backups"

def base_dir(hass: HomeAssistant) -> Path:
    return Path(hass.config.path(REL_BASE))

def overrides_path(hass: HomeAssistant) -> Path:
    return base_dir(hass) / OVERRIDES_FILENAME

def backups_dir(hass: HomeAssistant) -> Path:
    return base_dir(hass) / BACKUPS_DIRNAME

