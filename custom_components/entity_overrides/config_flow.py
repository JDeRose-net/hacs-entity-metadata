import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback

from .const import DOMAIN

class EntityOverridesConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        if self._async_current_entries():
            return self.async_abort(reason="already_configured")
        return self.async_create_entry(title="Entity Overrides", data={})

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return EntityOverridesOptionsFlowHandler(config_entry)


class EntityOverridesOptionsFlowHandler(config_entries.OptionsFlow):
    def __init__(self, config_entry):
        self.config_entry = config_entry

    async def async_step_init(self, user_input=None):
        if user_input is not None:
            if user_input.get("export_now"):
                await self.hass.services.async_call(DOMAIN, "export_overrides", {}, blocking=True)
                user_input["export_now"] = False
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema({
                vol.Required("max_backups", default=self.config_entry.options.get("max_backups", 5)): int,
                vol.Required("enable_on_boot", default=self.config_entry.options.get("enable_on_boot", True)): bool,
                vol.Optional("export_now", default=False): bool
            })
        )

