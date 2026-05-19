import logging
import asyncio
import requests
import urllib3
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "renson_flux"
_LOGGER = logging.getLogger(__name__)

# A small helper function so we can push the blocking network request to a background thread
def send_ventilation_command(base_url, headers, payload):
    requests.put(f"{base_url}/ventilation", headers=headers, json=payload, verify=False, timeout=5)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Renson Flux from a UI config entry."""
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    host = entry.data["host"]
    api_key = entry.data["api_key"]
    base_url = f"https://{host}/api/v1/thirdparty"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    # --- THE NEW ASYNC BOOST HANDLER ---
    async def async_handle_set_boost(call):
        speed = call.data.get("speed", 100)
        timer = call.data.get("timer", 30)
        payload = {"mode": "manual", "percent": speed, "timer": timer}
        
        try:
            # 1. Send the HTTP command in a safe background thread
            await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
            _LOGGER.info(f"Boost sent: {speed}% for {timer} mins")

            # 2. Wait 3 seconds asynchronously (Does NOT freeze Home Assistant)
            await asyncio.sleep(3)

            # 3. Ask Home Assistant to forcefully update our specific sensors right now
            await hass.services.async_call(
                "homeassistant", "update_entity",
                {"entity_id": [
                    "sensor.renson_co2_level",
                    "sensor.renson_voc_level",
                    "sensor.renson_humidity_level"
                ]},
                blocking=False
            )
        except Exception as e:
            _LOGGER.error(f"Failed to send boost: {e}")

    # --- THE NEW ASYNC AUTO HANDLER ---
    async def async_handle_set_auto(call):
        payload = {"mode": "automatic"}
        try:
            await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
            _LOGGER.info("Renson set back to Auto mode.")
            
            await asyncio.sleep(3)
            
            await hass.services.async_call(
                "homeassistant", "update_entity",
                {"entity_id": [
                    "sensor.renson_co2_level",
                    "sensor.renson_voc_level",
                    "sensor.renson_humidity_level"
                ]},
                blocking=False
            )
        except Exception as e:
            _LOGGER.error(f"Failed to set auto: {e}")

    # Register our new Async services
    hass.services.async_register(DOMAIN, "set_boost", async_handle_set_boost)
    hass.services.async_register(DOMAIN, "set_auto", async_handle_set_auto)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok