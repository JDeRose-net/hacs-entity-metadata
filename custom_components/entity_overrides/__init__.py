import logging
import os
import yaml
from datetime import datetime

from homeassistant.core import HomeAssistant, callback, ServiceCall
from homeassistant.helpers.entity_registry import async_get as async_get_entity_registry
from homeassistant.helpers.entity_component import async_update_entity
from homeassistant.config_entries import ConfigEntry

DOMAIN = "entity_overrides"

_LOGGER = logging.getLogger(__name__)

CONF_FILE = "entity_overrides/settings.yaml"
EXPORT_FILE = "entity_overrides/overrides.yaml"
BACKUP_DIR = "entity_overrides/backups"
DEFAULT_MAX_BACKUPS = 5

async def async_setup(hass: HomeAssistant, config: dict):
    return True

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry):
    config_path = hass.config.path(CONF_FILE)
    export_path = hass.config.path(EXPORT_FILE)
    backup_path = hass.config.path(BACKUP_DIR)
    max_backups = entry.options.get("max_backups", DEFAULT_MAX_BACKUPS)
    enable_on_boot = entry.options.get("enable_on_boot", True)

    os.makedirs(backup_path, exist_ok=True)

    async def apply_overrides(ignore_toggle=False):
        if not ignore_toggle and not enable_on_boot:
            _LOGGER.info("Entity overrides disabled via options. Skipping.")
            return

        if not os.path.exists(export_path):
            _LOGGER.warning("%s not found, skipping overrides", EXPORT_FILE)
            return

        try:
            with open(export_path, "r") as f:
                overrides = yaml.safe_load(f)

            if not overrides:
                _LOGGER.info("No overrides defined in %s", EXPORT_FILE)
                return

            entity_registry = async_get_entity_registry(hass)

            for entity_id, props in overrides.get(DOMAIN, {}).items():
                entry = entity_registry.async_get(entity_id)
                if not entry:
                    _LOGGER.warning("Entity not found: %s", entity_id)
                    continue

                updates = {}
                if "friendly_name" in props:
                    updates["name"] = props["friendly_name"]
                if "hidden" in props:
                    updates["hidden_by"] = None if not props["hidden"] else "user"
                if "enabled" in props:
                    updates["disabled_by"] = None if props["enabled"] else "user"

                if updates:
                    entity_registry.async_update_entity(entity_id, **updates)
                    _LOGGER.info("Updated %s: %s", entity_id, updates)

        except Exception as e:
            _LOGGER.exception("Failed to apply entity overrides: %s", e)

    async def handle_export(call: ServiceCall):
        await export_overrides()

    async def export_overrides():
        entity_registry = async_get_entity_registry(hass)
        data = {}

        for entry in entity_registry.entities.values():
            overrides = {}
            if entry.name and entry.original_name and entry.name != entry.original_name:
                overrides["friendly_name"] = entry.name
            if entry.hidden_by is not None:
                overrides["hidden"] = True
            if entry.disabled_by is not None:
                overrides["enabled"] = False

            if overrides:
                data[entry.entity_id] = overrides

        if os.path.exists(export_path):
            timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
            rotated_file = os.path.join(backup_path, f"overrides.{timestamp}.yaml")
            os.rename(export_path, rotated_file)
            _LOGGER.info("Backed up existing overrides to %s", rotated_file)

            backups = sorted([
                f for f in os.listdir(backup_path)
                if f.startswith("overrides.") and f.endswith(".yaml")
            ])
            while len(backups) > max_backups:
                to_remove = backups.pop(0)
                try:
                    os.remove(os.path.join(backup_path, to_remove))
                    _LOGGER.info("Deleted old backup: %s", to_remove)
                except Exception as e:
                    _LOGGER.warning("Failed to delete old backup %s: %s", to_remove, e)

        if data:
            with open(export_path, "w") as f:
                yaml.dump({DOMAIN: data}, f)
            _LOGGER.info("Exported %d overrides to %s", len(data), export_path)
        else:
            _LOGGER.info("No overridden entities found to export")

    async def handle_apply(call: ServiceCall):
        await apply_overrides(ignore_toggle=True)
        _LOGGER.info("Manual reapply triggered via service call")

    hass.bus.async_listen_once("homeassistant_started", lambda event: hass.async_create_task(apply_overrides()))
    hass.services.async_register(DOMAIN, "export_overrides", handle_export)
    hass.services.async_register(DOMAIN, "apply_overrides", handle_apply)

    return True

