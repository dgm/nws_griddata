import logging
from datetime import timedelta
import aiohttp
import voluptuous as vol
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
from homeassistant.const import CONF_LATITUDE, CONF_LONGITUDE
from homeassistant.helpers.aiohttp_client import async_get_clientsession
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import async_track_time_interval
from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_LATITUDE): cv.latitude,
    vol.Required(CONF_LONGITUDE): cv.longitude,
})

async def async_setup_platform(hass, config, async_add_entities, discovery_info=None):
    lat = config[CONF_LATITUDE]
    lon = config[CONF_LONGITUDE]
    session = async_get_clientsession(hass)
    coordinator = NWSDataCoordinator(hass, session, lat, lon)
    await coordinator.async_update()
    async_add_entities([
        NWSWindSpeedSensor(coordinator, lat, lon),
        NWSWindDirectionSensor(coordinator, lat, lon),
        NWSTemperatureSensor(coordinator, lat, lon),
    ], True)

class NWSDataCoordinator:
    def __init__(self, hass, session, lat, lon):
        self._hass = hass
        self._session = session
        self._lat = lat
        self._lon = lon
        self._grid_id = None
        self._grid_x = None
        self._grid_y = None
        self.data = {}
        self._listeners = []
        async_track_time_interval(hass, self._async_update_wrapper, timedelta(seconds=UPDATE_INTERVAL))

    def async_add_listener(self, update_callback):
        self._listeners.append(update_callback)

    async def _async_update_wrapper(self, _=None):
        await self.async_update()
        for listener in self._listeners:
            listener()

    async def async_update(self):
        try:
            if not self._grid_id:
                await self._fetch_grid_coordinates()
            if self._grid_id:
                await self._fetch_gridpoint_data()
        except Exception as e:
            _LOGGER.error(f"Error updating NWS grid data: {e}")

    async def _fetch_grid_coordinates(self):
        url = f"https://api.weather.gov/points/{self._lat},{self._lon}"
        headers = {"User-Agent": "HomeAssistant"}
        try:
            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    props = data.get("properties", {})
                    self._grid_id = props.get("gridId")
                    self._grid_x = props.get("gridX")
                    self._grid_y = props.get("gridY")
                    _LOGGER.info(f"Fetched grid coordinates: {self._grid_id}/{self._grid_x},{self._grid_y}")
        except Exception as e:
            _LOGGER.error(f"Error fetching grid coordinates: {e}")

    async def _fetch_gridpoint_data(self):
        url = f"https://api.weather.gov/gridpoints/{self._grid_id}/{self._grid_x},{self._grid_y}"
        headers = {"User-Agent": "HomeAssistant"}
        try:
            async with self._session.get(url, headers=headers, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    props = data.get("properties", {})
                    new_grid_id = props.get("gridId")
                    if new_grid_id and new_grid_id != self._grid_id:
                        _LOGGER.info(f"Grid coordinates changed, refetching...")
                        self._grid_id = None
                        await self._fetch_grid_coordinates()
                        return
                    self.data = {
                        "updateTime": props.get("updateTime"),
                        "windSpeed": props.get("windSpeed", {}).get("values", []),
                        "windSpeedUom": props.get("windSpeed", {}).get("uom"),
                        "windDirection": props.get("windDirection", {}).get("values", []),
                        "windDirectionUom": props.get("windDirection", {}).get("uom"),
                        "temperature": props.get("temperature", {}).get("values", []),
                        "temperatureUom": props.get("temperature", {}).get("uom"),
                        "gridId": self._grid_id,
                        "gridX": self._grid_x,
                        "gridY": self._grid_y,
                    }
                elif resp.status == 404:
                    _LOGGER.warning("Grid coordinates invalid, refetching...")
                    self._grid_id = None
                    await self._fetch_grid_coordinates()
        except Exception as e:
            _LOGGER.error(f"Error fetching gridpoint data: {e}")

class NWSBaseSensor(SensorEntity):
    def __init__(self, coordinator, lat, lon, sensor_type):
        self._coordinator = coordinator
        self._lat = lat
        self._lon = lon
        self._sensor_type = sensor_type
        coordinator.async_add_listener(self._update_callback)

    def _update_callback(self):
        self.async_write_ha_state()

    @property
    def should_poll(self):
        return False

    @property
    def extra_state_attributes(self):
        return {
            "gridId": self._coordinator.data.get("gridId"),
            "gridX": self._coordinator.data.get("gridX"),
            "gridY": self._coordinator.data.get("gridY"),
            "updateTime": self._coordinator.data.get("updateTime"),
        }

class NWSWindSpeedSensor(NWSBaseSensor):
    def __init__(self, coordinator, lat, lon):
        super().__init__(coordinator, lat, lon, "windSpeed")

    @property
    def name(self):
        return f"NWS Wind Speed {self._lat},{self._lon}"

    @property
    def unique_id(self):
        return f"nws_wind_speed_{self._lat}_{self._lon}"

    @property
    def state(self):
        values = self._coordinator.data.get("windSpeed", [])
        return len(values)

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        attrs["values"] = self._coordinator.data.get("windSpeed", [])
        attrs["uom"] = self._coordinator.data.get("windSpeedUom")
        return attrs

class NWSWindDirectionSensor(NWSBaseSensor):
    def __init__(self, coordinator, lat, lon):
        super().__init__(coordinator, lat, lon, "windDirection")

    @property
    def name(self):
        return f"NWS Wind Direction {self._lat},{self._lon}"

    @property
    def unique_id(self):
        return f"nws_wind_direction_{self._lat}_{self._lon}"

    @property
    def state(self):
        values = self._coordinator.data.get("windDirection", [])
        return len(values)

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        attrs["values"] = self._coordinator.data.get("windDirection", [])
        attrs["uom"] = self._coordinator.data.get("windDirectionUom")
        return attrs

class NWSTemperatureSensor(NWSBaseSensor):
    def __init__(self, coordinator, lat, lon):
        super().__init__(coordinator, lat, lon, "temperature")

    @property
    def name(self):
        return f"NWS Temperature {self._lat},{self._lon}"

    @property
    def unique_id(self):
        return f"nws_temperature_{self._lat}_{self._lon}"

    @property
    def state(self):
        values = self._coordinator.data.get("temperature", [])
        return len(values)

    @property
    def extra_state_attributes(self):
        attrs = super().extra_state_attributes
        attrs["values"] = self._coordinator.data.get("temperature", [])
        attrs["uom"] = self._coordinator.data.get("temperatureUom")
        return attrs
