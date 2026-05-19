import logging
import requests
import urllib3
from datetime import timedelta
from homeassistant.components.sensor import SensorEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
_LOGGER = logging.getLogger(__name__)
SCAN_INTERVAL = timedelta(minutes=15)
DOMAIN = "renson_flux"

async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, async_add_entities):
    """Set up the Renson sensors from config entry."""
    config = hass.data[DOMAIN][entry.entry_id]
    host = config["host"]
    api_key = config["api_key"]
    
    async_add_entities([
        RensonSensor(host, api_key, "co2", "Renson CO2 Level", "mdi:molecule-co2"),
        RensonSensor(host, api_key, "voc", "Renson VOC Level", "mdi:air-filter"),
        RensonSensor(host, api_key, "humidity", "Renson Humidity Level", "mdi:water-percent")
    ], True)

class RensonSensor(SensorEntity):
    def __init__(self, host, api_key, sensor_type, name, icon):
        self._host = host
        self._api_key = api_key
        self._sensor_type = sensor_type
        self._attr_name = name
        self._attr_icon = icon
        self._attr_state = None
        self._attr_unique_id = f"renson_flux_{host}_{sensor_type}"

    @property
    def state(self):
        return self._attr_state

    def update(self):
        """Fetch new state data."""
        url = f"https://{self._host}/api/v1/thirdparty/sensors"
        headers = {"X-API-Key": self._api_key, "Accept": "application/json"}
        try:
            response = requests.get(url, headers=headers, verify=False, timeout=5)
            if response.status_code == 200:
                data = response.json()
                raw_level = data.get("data", {}).get(self._sensor_type, {}).get("level", "unknown")
                self._attr_state = raw_level.title()
        except Exception as e:
            _LOGGER.error(f"Error communicating with Renson: {e}")