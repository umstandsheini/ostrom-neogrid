"""Config flow: e-mail + password of the Ostrom account."""
from __future__ import annotations

import voluptuous as vol

from homeassistant.config_entries import ConfigFlow
from homeassistant.const import CONF_EMAIL, CONF_PASSWORD
from homeassistant.helpers.aiohttp_client import async_create_clientsession

from .api import OstromApi, OstromApiError, OstromAuthError
from .const import DOMAIN


class OstromConfigFlow(ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            await self.async_set_unique_id(user_input[CONF_EMAIL].lower())
            self._abort_if_unique_id_configured()
            api = OstromApi(async_create_clientsession(self.hass), user_input[CONF_EMAIL], user_input[CONF_PASSWORD])
            try:
                await api.login()
            except OstromAuthError:
                errors["base"] = "invalid_auth"
            except (OstromApiError, Exception):  # noqa: BLE001 - surface anything as cannot_connect
                errors["base"] = "cannot_connect"
            else:
                return self.async_create_entry(title=user_input[CONF_EMAIL], data=user_input)
        schema = vol.Schema({vol.Required(CONF_EMAIL): str, vol.Required(CONF_PASSWORD): str})
        return self.async_show_form(step_id="user", data_schema=schema, errors=errors)

    async def _validated_password_form(self, step_id, entry, user_input):
        """Shared by reauth and reconfigure: check the new password, then store it and reload the entry."""
        errors = {}
        if user_input is not None:
            api = OstromApi(async_create_clientsession(self.hass), entry.data[CONF_EMAIL], user_input[CONF_PASSWORD])
            try:
                await api.login()
            except OstromAuthError:
                errors["base"] = "invalid_auth"
            except Exception:  # noqa: BLE001
                errors["base"] = "cannot_connect"
            else:
                return self.async_update_reload_and_abort(
                    entry, data_updates={CONF_PASSWORD: user_input[CONF_PASSWORD]})
        return self.async_show_form(
            step_id=step_id,
            data_schema=vol.Schema({vol.Required(CONF_PASSWORD): str}),
            errors=errors,
            description_placeholders={"email": entry.data[CONF_EMAIL]},
        )

    async def async_step_reconfigure(self, user_input=None):
        """Menu entry "Neu konfigurieren": change the stored password without removing the integration."""
        return await self._validated_password_form("reconfigure", self._get_reconfigure_entry(), user_input)

    async def async_step_reauth(self, entry_data):
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(self, user_input=None):
        """Password changed at Ostrom (or login rejected): ask for the new one."""
        return await self._validated_password_form("reauth_confirm", self._get_reauth_entry(), user_input)
