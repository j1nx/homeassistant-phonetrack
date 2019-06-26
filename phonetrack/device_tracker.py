"""Support for PhoneTrack device tracking."""
import logging
import urllib.parse
from datetime import timedelta

import requests
import voluptuous as vol

from homeassistant.components.device_tracker import (
    PLATFORM_SCHEMA, SOURCE_TYPE_GPS)
from homeassistant.const import (
    CONF_DEVICES, CONF_TOKEN, CONF_URL)
import homeassistant.helpers.config_validation as cv
from homeassistant.helpers.event import track_time_interval
from homeassistant.helpers.typing import ConfigType
from homeassistant.util import slugify, Throttle

_LOGGER = logging.getLogger(__name__)

CONF_MAX_GPS_ACCURACY = 'max_gps_accuracy'
UPDATE_INTERVAL = timedelta(minutes=5)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(CONF_DEVICES): vol.All(cv.ensure_list, [cv.string]),
    vol.Required(CONF_TOKEN): cv.string,
	vol.Required(CONF_URL): cv.string,
    vol.Optional(CONF_MAX_GPS_ACCURACY, default=100000): vol.Coerce(float),
})


def setup_scanner(hass, config: ConfigType, see, discovery_info=None):
    """Set up the PhoneTrack scanner."""
    PhoneTrackDeviceTracker(hass, config, see)
    return True


class PhoneTrackDeviceTracker(object):
    """
    A device tracker fetching last position from the PhoneTrack Nextcloud
    app.
    """
    def __init__(self, hass, config: ConfigType, see) -> None:
        """Initialize the PhoneTrack tracking."""
        self.hass = hass
        self.url = config[CONF_URL]
        self.token = config[CONF_TOKEN]
        self.devices = config[CONF_DEVICES]
        self.max_gps_accuracy = config[CONF_MAX_GPS_ACCURACY]
        self.see = see
        self._update_info()

        track_time_interval(
            hass, self._update_info, UPDATE_INTERVAL
        )

    @Throttle(UPDATE_INTERVAL)
    def _update_info(self, now=None):
        """Update the device info."""
        _LOGGER.debug("Updating devices %s", now)
        data = requests.get(urllib.parse.urljoin(self.url, self.token)).json()
        data = data[self.token]
        for device in self.devices:
            if device not in data.keys():
                _LOGGER.info('Device %s is not available.', device)
                continue
            lat, lon = data[device]['lat'], data[device]['lon']
            accuracy = data[device]['accuracy']
            battery = data[device]['batterylevel']
            if self.max_gps_accuracy is not None and \
                data[device]['accuracy'] > self.max_gps_accuracy:
                _LOGGER.info("Ignoring %s update because expected GPS "
                             "accuracy is not met", device)
                continue

            self.see(
                dev_id=slugify(device),
                gps=(lat, lon),
                source_type=SOURCE_TYPE_GPS,
                gps_accuracy=accuracy,
                battery=battery
            )
        return True