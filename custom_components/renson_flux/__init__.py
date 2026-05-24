import logging
import asyncio
import requests
import urllib3
from homeassistant.core import HomeAssistant
from homeassistant.config_entries import ConfigEntry

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

DOMAIN = "renson_flux"
_LOGGER = logging.getLogger(__name__)

# Keep track of running sleep loops so we can cancel them if another mode is triggered
active_tasks = {}

def send_ventilation_command(base_url, headers, payload):
    requests.put(f"{base_url}/ventilation", headers=headers, json=payload, verify=False, timeout=5)

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = entry.data

    host = entry.data["host"]
    api_key = entry.data["api_key"]
    base_url = f"https://{host}/api/v1/thirdparty"
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}

    # Helper function to cancel an active sleep loop if the user changes the mode
    def cancel_sleep_loop():
        task = active_tasks.get(entry.entry_id)
        if task and not task.done():
            task.cancel()
            active_tasks[entry.entry_id] = None

    async def async_handle_set_boost(call):
        cancel_sleep_loop()
        speed = call.data.get("speed", 100)
        timer = call.data.get("timer", 30)
        payload = {"mode": "manual", "percent": speed, "timer": timer}
        try:
            await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
            _LOGGER.info(f"Boost sent: {speed}% for {timer} mins")
            await asyncio.sleep(3)
            await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ["sensor.renson_active_mode", "sensor.renson_co2_level", "sensor.renson_voc_level", "sensor.renson_humidity_level", "sensor.renson_breeze_status"]}, blocking=False)
        except Exception as e:
            _LOGGER.error(f"Failed to send boost: {e}")

    async def async_handle_set_minimum(call):
        cancel_sleep_loop()
        timer = call.data.get("timer", 60)
        payload = {"mode": "manual", "preset": "minimum", "timer": timer}
        try:
            await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
            _LOGGER.info(f"Renson set to Minimum for {timer} mins.")
            await asyncio.sleep(3)
            await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ["sensor.renson_active_mode", "sensor.renson_breeze_status"]}, blocking=False)
        except Exception as e:
            _LOGGER.error(f"Failed to set minimum: {e}")

    async def async_handle_set_auto(call):
        cancel_sleep_loop()
        payload = {"mode": "automatic"}
        try:
            await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
            _LOGGER.info("Renson set back to Auto mode.")
            await asyncio.sleep(3)
            await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ["sensor.renson_active_mode", "sensor.renson_breeze_status"]}, blocking=False)
        except Exception as e:
            _LOGGER.error(f"Failed to set auto: {e}")

    async def async_handle_set_sleep(call):
        cancel_sleep_loop()
        
        # Force these to be integers so the math doesn't crash if passed as strings
        speed = int(call.data.get("speed", 20))
        total_timer = int(call.data.get("timer", 480))

        async def sleep_loop():
            try:
                loops = total_timer // 120
                remainder = total_timer % 120
                
                # Send the 120-minute chunks
                for i in range(loops):
                    payload = {"mode": "manual", "percent": speed, "timer": 120}
                    await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
                    _LOGGER.info(f"Sleep loop chunk {i+1}/{loops} sent: {speed}% for 120 mins")
                    
                    # Tell the dashboard to update instantly so you see it working
                    await asyncio.sleep(3)
                    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ["sensor.renson_active_mode", "sensor.renson_breeze_status"]}, blocking=False)
                    
                    # Wait 2 hours before firing the next command (minus the 3 seconds we just waited)
                    await asyncio.sleep((120 * 60) - 3)
                    
                # Send any remaining minutes (e.g. if you set a 300 minute timer, this handles the final 60)
                if remainder > 0:
                    payload = {"mode": "manual", "percent": speed, "timer": remainder}
                    await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
                    
                    # Tell dashboard to update
                    await asyncio.sleep(3)
                    await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ["sensor.renson_active_mode", "sensor.renson_breeze_status"]}, blocking=False)
                    
                    await asyncio.sleep((remainder * 60) - 3)
                    
                # Finally, revert to auto when all loops are done
                payload = {"mode": "automatic"}
                await hass.async_add_executor_job(send_ventilation_command, base_url, headers, payload)
                _LOGGER.info("Sleep sequence completed. Returned to Auto.")
                
                # Tell dashboard to update one last time
                await asyncio.sleep(3)
                await hass.services.async_call("homeassistant", "update_entity", {"entity_id": ["sensor.renson_active_mode", "sensor.renson_breeze_status"]}, blocking=False)
                
            except asyncio.CancelledError:
                # This safely catches when the user clicks 'Auto' or 'Boost' mid-sleep
                _LOGGER.info("Sleep loop was manually overridden and cancelled.")
                raise

        # Start the background task and store it so it can be cancelled later
        task = hass.async_create_task(sleep_loop())
        active_tasks[entry.entry_id] = task

    # Register all services
    hass.services.async_register(DOMAIN, "set_boost", async_handle_set_boost)
    hass.services.async_register(DOMAIN, "set_minimum", async_handle_set_minimum)
    hass.services.async_register(DOMAIN, "set_auto", async_handle_set_auto)
    hass.services.async_register(DOMAIN, "set_sleep", async_handle_set_sleep)

    await hass.config_entries.async_forward_entry_setups(entry, ["sensor"])
    return True

async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    # Cancel any active timers before unloading
    task = active_tasks.get(entry.entry_id)
    if task and not task.done():
        task.cancel()
    
    unload_ok = await hass.config_entries.async_unload_platforms(entry, ["sensor"])
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok