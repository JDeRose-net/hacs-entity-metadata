"""
Entity Metadata (HACS) - export/import user overrides.

Default storage:
  - /config/etc/entity_metadata/overrides.yaml
  - /config/etc/entity_metadata/backups/overrides-YYYYMMDD-HHMMSS.yaml

Services:
  - entity_metadata.export_overrides
  - entity_metadata.import_overrides
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Iterable, Tuple

import voluptuous as vol
import yaml

from homeassistant.const import EVENT_HOMEASSISTANT_STARTED
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import area_registry as ar
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    OVERRIDES_FILENAME,
    BACKUPS_DIRNAME,
    base_dir,
    overrides_path,
    backups_dir,
)

_LOGGER = logging.getLogger(__name__)

# ----------------------------
# Keys in hass.data
# ----------------------------
DATA_SERVICES = "services_registered"
DATA_ENTRY_IDS = "entry_ids"
DATA_LISTENERS = "listeners"

# ----------------------------
# Service names & schemas
# ----------------------------
SERVICE_EXPORT = "export_overrides"
SERVICE_IMPORT = "import_overrides"

EXPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("write_overrides", default=True): cv.boolean,
        vol.Optional("write_backup", default=True): cv.boolean,
        vol.Optional("include_all", default=False): cv.boolean,
        vol.Optional("path"): cv.string,  # custom output path (abs or relative to /config)
        vol.Optional("include_domains", default=[]): [cv.string],
    }
)

IMPORT_SCHEMA = vol.Schema(
    {
        vol.Optional("path"): cv.string,        # custom input path (abs or relative to /config)
        vol.Optional("merge", default=True): cv.boolean,
        vol.Optional("strict_entities", default=False): cv.boolean,
    }
)

# ----------------------------
# HA bootstrap
# ----------------------------

async def async_setup(hass: HomeAssistant, _config: dict) -> bool:
    """Set up integration from YAML (services) and prepare data bucket."""
    _ensure_domain_bucket(hass)
    await _ensure_dirs(hass)
    _register_services_once(hass)
    hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, lambda evt: None)
    _LOGGER.info("%s: initialized (storage base: %s)", DOMAIN, base_dir(hass))
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up a config entry (UI flow)."""
    _ensure_domain_bucket(hass)
    await _ensure_dirs(hass)
    _register_services_once(hass)

    hass.data[DOMAIN][DATA_ENTRY_IDS].add(entry.entry_id)

    # Options change listener (noop today, but ready for future options)
    remove_listener = entry.add_update_listener(_reload_on_options_change)
    hass.data[DOMAIN][DATA_LISTENERS][entry.entry_id] = remove_listener
    _LOGGER.debug("%s: setup_entry id=%s", DOMAIN, entry.entry_id)

    # Auto-import on startup if enabled
    if entry.options.get("auto_import_on_startup", False):
        async def _on_started(_):
            await hass.services.async_call(
                DOMAIN, SERVICE_IMPORT, {"merge": True}, blocking=True
            )
        hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STARTED, _on_started)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry (we have no platforms to unload)."""
    remove = hass.data.get(DOMAIN, {}).get(DATA_LISTENERS, {}).pop(entry.entry_id, None)
    if remove:
        remove()

    hass.data.get(DOMAIN, {}).get(DATA_ENTRY_IDS, set()).discard(entry.entry_id)
    _LOGGER.debug("%s: unload_entry id=%s", DOMAIN, entry.entry_id)
    return True


async def _reload_on_options_change(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload entry on options change."""
    await hass.config_entries.async_reload(entry.entry_id)

# ----------------------------
# hass.data & FS helpers
# ----------------------------

def _ensure_domain_bucket(hass: HomeAssistant) -> None:
    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {
            DATA_SERVICES: False,
            DATA_ENTRY_IDS: set(),
            DATA_LISTENERS: {},
        }

async def _ensure_dirs(hass: HomeAssistant) -> None:
    """Create /config/etc/entity_metadata and backups/ if missing."""
    def _mk():
        base = base_dir(hass)
        (base / BACKUPS_DIRNAME).mkdir(parents=True, exist_ok=True)
    await hass.async_add_executor_job(_mk)

def _resolve_path(hass: HomeAssistant, maybe_path: str | None, *, default: Path) -> Path:
    """Return an absolute path; relative paths resolved under /config."""
    if not maybe_path:
        return default
    p = Path(maybe_path)
    if not p.is_absolute():
        p = Path(hass.config.path(str(p)))
    return p

async def _prune_backups(hass: HomeAssistant, keep: int) -> None:
    """Keep only the newest N backup files; delete older ones."""
    if keep <= 0:
        return

    def _do():
        files = sorted(backups_dir(hass).glob("overrides-*.yaml"), reverse=True)
        for old in files[keep:]:
            try:
                old.unlink()
            except Exception:
                pass

    await hass.async_add_executor_job(_do)

# ----------------------------
# YAML read/write
# ----------------------------

async def _read_yaml(hass: HomeAssistant, path: Path) -> Dict[str, Any]:
    def _read():
        if not path.exists():
            return {}
        with path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
            if not isinstance(data, dict):
                raise ValueError(f"YAML at {path} must be a mapping at top level.")
            return data
    return await hass.async_add_executor_job(_read)

async def _write_yaml(hass: HomeAssistant, path: Path, data: Dict[str, Any]) -> None:
    def _write():
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as f:
            # Keep insertion order so 'version' and 'generated_at' stay at the top
            yaml.safe_dump(data, f, sort_keys=False, allow_unicode=True)
    await hass.async_add_executor_job(_write)

# ----------------------------
# Registry <-> YAML conversion
# ----------------------------

def _serialize_registry(
    ent_reg: er.EntityRegistry, include_domains: Iterable[str] | None, include_all: bool
) -> Dict[str, Any]:
    """
    Build a {entity_id: {name/icon/disabled/hidden}} mapping.

    Only entities with explicit user overrides (name/icon) or user-disabled/hidden
    are included by default. Set include_all=True to dump every entity.
    """
    payload: Dict[str, Any] = {}
    domains = set(d.lower() for d in (include_domains or []))

    for entry in list(ent_reg.entities.values()):
        # derive domain from entity_id for broad HA compatibility
        entry_domain = entry.entity_id.partition(".")[0].lower()
        if domains and entry_domain not in domains:
            continue

        data: Dict[str, Any] = {}

        if entry.name:
            data["name"] = entry.name
        if entry.icon:
            data["icon"] = entry.icon

        if entry.hidden_by is not None:
            data["hidden"] = True
        if entry.disabled_by is not None:
            data["disabled"] = True

        if include_all or data:
            payload[entry.entity_id] = data

    # Optional: make entity order stable (alphabetical). Uncomment if desired.
    # payload = dict(sorted(payload.items()))

    # RFC3339-ish UTC timestamp with trailing 'Z' (avoid '+00:00Z')
    ts = dt_util.utcnow().isoformat(timespec="seconds")
    if ts.endswith("+00:00"):
        ts = ts[:-6] + "Z"
    elif not ts.endswith("Z"):
        ts += "Z"

    # Build in desired top-level order
    return {
        "version": 1,
        "generated_at": ts,
        "entities": payload,
    }

def _normalize_entities_block(blob: Dict[str, Any]) -> Dict[str, Dict[str, Any]]:
    """
    Accept either of:
      {entities: {...}}  or  {<entity_id>: {...}}
    Return the inner {entity_id: {props}} mapping.
    """
    if "entities" in blob and isinstance(blob["entities"], dict):
        return blob["entities"]
    return {k: v for k, v in blob.items() if isinstance(v, dict) and k.count(".") == 1}

# ----------------------------
# Apply overrides
# ----------------------------

async def _apply_overrides(
    hass: HomeAssistant,
    entities_map: Dict[str, Dict[str, Any]],
    *,
    merge: bool,
    strict_entities: bool,
) -> Tuple[int, int]:
    """
    Apply overrides to the entity registry.

    Returns (updated_count, skipped_count).
    """
    ent_reg = er.async_get(hass)
    area_reg = ar.async_get(hass)

    updated = 0
    skipped = 0

    for entity_id, props in entities_map.items():
        entry = ent_reg.async_get(entity_id)
        if entry is None:
            skipped += 1
            msg = f"{DOMAIN}: import: entity not found: {entity_id}"
            if strict_entities:
                raise ValueError(msg)
            _LOGGER.warning(msg)
            continue

        updates: Dict[str, Any] = {}

        if "name" in props:
            name = props.get("name")
            updates["name"] = name if name else None

        if "icon" in props:
            icon = props.get("icon")
            updates["icon"] = icon if icon else None

        if "hidden" in props:
            hidden = bool(props.get("hidden"))
            updates["hidden_by"] = er.RegistryEntryHider.USER if hidden else None

        if "disabled" in props:
            disabled = bool(props.get("disabled"))
            updates["disabled_by"] = er.RegistryEntryDisabler.USER if disabled else None

        if "area" in props:
            area_val = props.get("area")
            area_id = None
            if area_val:
                # Accept direct area_id, else resolve by name
                if isinstance(area_val, str) and area_reg.async_get_area(area_val):
                    area_id = area_val
                else:
                    area = area_reg.async_get_area_by_name(str(area_val))
                    area_id = area.id if area else None
            updates["area_id"] = area_id

        if not merge:
            if "name" not in props:
                updates["name"] = None
            if "icon" not in props:
                updates["icon"] = None
            if "hidden" not in props:
                updates["hidden_by"] = None
            if "disabled" not in props:
                updates["disabled_by"] = None
            if "area" not in props:
                updates["area_id"] = entry.area_id  # leave as-is explicitly

        ent_reg.async_update_entity(entity_id, **updates)
        updated += 1

    return updated, skipped

# ----------------------------
# Services (export/import)
# ----------------------------

def _register_services_once(hass: HomeAssistant) -> None:
    """Register services only once per HA instance."""
    if hass.data[DOMAIN][DATA_SERVICES]:
        return

    hass.services.async_register(
        DOMAIN, SERVICE_EXPORT, _handle_export_service, schema=EXPORT_SCHEMA
    )
    hass.services.async_register(
        DOMAIN, SERVICE_IMPORT, _handle_import_service, schema=IMPORT_SCHEMA
    )
    hass.data[DOMAIN][DATA_SERVICES] = True
    _LOGGER.debug("%s: services registered", DOMAIN)

async def _handle_export_service(call: ServiceCall) -> None:
    hass: HomeAssistant = call.hass
    params = call.data or {}

    write_overrides: bool = params["write_overrides"]
    write_backup: bool = params["write_backup"]
    include_all: bool = params["include_all"]
    include_domains = params.get("include_domains", [])

    ent_reg = er.async_get(hass)
    blob = _serialize_registry(ent_reg, include_domains, include_all)

    # Write main overrides.yaml (optional)
    if write_overrides:
        out_path = _resolve_path(hass, params.get("path"), default=overrides_path(hass))
        await _write_yaml(hass, out_path, blob)
        _LOGGER.info("%s: exported overrides -> %s", DOMAIN, out_path)

    # Write timestamped backup (optional)
    if write_backup:
        stamp = dt_util.utcnow().strftime("%Y%m%d-%H%M%S")
        backup_path = backups_dir(hass) / f"overrides-{stamp}.yaml"
        await _write_yaml(hass, backup_path, blob)
        _LOGGER.info("%s: wrote backup -> %s", DOMAIN, backup_path)

        # Honor backup_retention from the (single) config entry
        entries = hass.config_entries.async_entries(DOMAIN)
        keep = int(entries[0].options.get("backup_retention", 7)) if entries else 7
        await _prune_backups(hass, keep)

async def _handle_import_service(call: ServiceCall) -> None:
    hass: HomeAssistant = call.hass
    params = call.data or {}

    in_path = _resolve_path(hass, params.get("path"), default=overrides_path(hass))
    merge: bool = params["merge"]
    strict_entities: bool = params["strict_entities"]

    blob = await _read_yaml(hass, in_path)
    entities_map = _normalize_entities_block(blob)

    updated, skipped = await _apply_overrides(
        hass, entities_map, merge=merge, strict_entities=strict_entities
    )

    _LOGGER.info(
        "%s: import complete from %s (updated=%d, skipped=%d)",
        DOMAIN,
        in_path,
        updated,
        skipped,
    )

