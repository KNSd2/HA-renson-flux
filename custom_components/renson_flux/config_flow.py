import voluptuous as vol
import requests
import urllib3
from homeassistant import config_entries
from homeassistant.core import HomeAssistant

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
DOMAIN = "renson_flux"

DATA_SCHEMA = vol.Schema({
    vol.Required("host", default="192.168.1.11"): str,
    vol.Required("api_key"): str,
})

def test_connection(host, api_key):
    url = f"https://{host}/api/v1/thirdparty/global"
    headers = {"X-API-Key": api_key, "Accept": "application/json"}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=5)
        return res.status_code == 200
    except Exception:
        return False

class RensonConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            valid = await self.hass.async_add_executor_job(
                test_connection, user_input["host"], user_input["api_key"]
            )
            
            if valid:
                return self.async_create_entry(title="Renson Flux", data=user_input)
            else:
                errors["base"] = "cannot_connect"

        return self.async_show_form(
            step_id="user", data_schema=DATA_SCHEMA, errors=errors
        )