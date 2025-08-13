"""Config flow for Entity Metadata (HACS)."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers import entity_registry as er

from .const import DOMAIN

SERVICE_EXPORT = "export_overrides"  # service name registered in __init__.py


class EntityMetadataConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle the config flow (single instance)."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        # Only one instance allowed.
        if self._async_current_entries():
            return self.async_abort(reason="single_instance_allowed")

        if user_input is None:
            # No fields needed at creation time.
            return self.async_show_form(step_id="user", data_schema=vol.Schema({}))

        return self.async_create_entry(
            title="Entity Metadata Persistence",
            data={},  # keep configurable values in options
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        _entry: config_entries.ConfigEntry,
    ) -> config_entries.OptionsFlow:
        """Return the options flow (HA injects self.config_entry automatically)."""
        return OptionsFlowHandler()


class OptionsFlowHandler(config_entries.OptionsFlow):
    """Handle options for Entity Metadata."""

    def __init__(self) -> None:
        # Do NOT assign self.config_entry here; HA injects it.
        pass

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options, with a one-shot 'Export now' action."""
        current = dict(self.config_entry.options)

        if user_input is not None:
            # Pop non-persistent action flag
            export_now = bool(user_input.pop("export_now", False))

            # Persisted options
            new_options: dict[str, Any] = {
                "auto_import_on_startup": bool(
                    user_input.get(
                        "auto_import_on_startup",
                        current.get("auto_import_on_startup", False),
                    )
                ),
                "backup_retention": int(
                    user_input.get("backup_retention", current.get("backup_retention", 7))
                ),
                "export_all_entities": bool(
                    user_input.get(
                        "export_all_entities", current.get("export_all_entities", False)
                    )
                ),
                "export_domains": list(
                    user_input.get("export_domains", current.get("export_domains", []))
                ),
            }

            # Optional immediate export
            if export_now:
                include_all = new_options.get("export_all_entities", False)
                include_domains = new_options.get("export_domains", [])
                try:
                    await self.hass.services.async_call(
                        DOMAIN,
                        SERVICE_EXPORT,
                        {
                            "write_overrides": True,
                            "write_backup": True,
                            "include_all": include_all,
                            "include_domains": include_domains,
                        },
                        blocking=True,
                    )
                    # Notify via service (works in flows)
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "Entity Metadata",
                            "message": (
                                "Manual export completed. Files are under "
                                "<code>/config/etc/entity_metadata</code>."
                            ),
                            "notification_id": f"{DOMAIN}_export_done",
                        },
                        blocking=False,
                    )
                except Exception as exc:  # pragma: no cover
                    await self.hass.services.async_call(
                        "persistent_notification",
                        "create",
                        {
                            "title": "Entity Metadata",
                            "message": f"Manual export failed: {exc}",
                            "notification_id": f"{DOMAIN}_export_failed",
                        },
                        blocking=False,
                    )

            return self.async_create_entry(title="", data=new_options)

        # Build domain choices for multi-select (safe for HA UI serializer)
        ent_reg = er.async_get(self.hass)
        domains = sorted({eid.split(".", 1)[0] for eid in ent_reg.entities.keys()})
        domain_choices = {d: d for d in domains}

        schema = vol.Schema(
            {
                vol.Optional(
                    "auto_import_on_startup",
                    default=current.get("auto_import_on_startup", False),
                ): bool,
                vol.Optional(
                    "backup_retention",
                    default=current.get("backup_retention", 7),
                ): vol.Coerce(int),
                vol.Optional(
                    "export_all_entities",
                    default=current.get("export_all_entities", False),
                ): bool,
                vol.Optional(
                    "export_domains",
                    default=current.get("export_domains", []),
                ): cv.multi_select(domain_choices),
                # Non-persistent, one-shot action
                vol.Optional("export_now", default=False): bool,
            }
        )

        return self.async_show_form(step_id="init", data_schema=schema)

