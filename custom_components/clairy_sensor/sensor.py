"""Platform for sensor integration."""
import datetime
import json
import logging
import requests

import voluptuous as vol

from homeassistant.const import TEMP_CELSIUS
from homeassistant.helpers.entity import Entity
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA

_LOGGER = logging.getLogger(__name__)

CONF_SERIAL = 'serial'
CONF_USER_ID = 'user_id'

# Clairy data is stored in the cloud once every 10 minutes
SCAN_INTERVAL = datetime.timedelta(minutes=10)

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({vol.Required(CONF_SERIAL): cv.string,
                                          vol.Required(CONF_USER_ID): cv.string})


def setup_platform(_hass, config, add_entities, _discovery_info=None):
    """Set up the sensor platform."""
    serial = config.get(CONF_SERIAL)
    user_id = config.get(CONF_USER_ID)

    if serial is None:
        _LOGGER.error("'serial' missing in configuration")
    elif user_id is None:
        _LOGGER.error("'user_id' missing in configuration")
    else:
        add_entities([Clairy(serial, user_id)])


class Clairy(Entity):
    """Representation of a Sensor."""

    def __init__(self, serial, user_id):
        """Initialize the sensor."""
        self.url = 'http://api.clairy.co'
        self.__token = None
        self.__serial = serial
        self.__user_id = user_id
        self._data = None
        self._profile = None
        self._firmware_version = None

    @property
    def name(self):
        """Return the name of the sensor."""
        return 'Clairy Temperature'

    @property
    def state(self):
        """Return the state of the sensor."""
        if self._data is not None:
            return self._data['Temperature']
        return None

    @property
    def unit_of_measurement(self):
        """Return the unit of measurement."""
        return TEMP_CELSIUS

    def update(self):
        """Fetch new state data for the sensor.

        This is the only method that should fetch new data for Home Assistant.
        self._data is updated with: {'Device': None,
                                     'Serial': None,
                                     'Date': '2019-10-12T15:28:00',
                                     'Temperature': 22.3,
                                     'Humidity': 56.1,
                                     'FanIsOn': False,
                                     'Iaq': 1000.0},
        """
        if self._profile is None:
            self._profile = self._get_profile()
        if self._firmware_version is None:  # just retreive once at the start of hass
            self._firmware_version = self._get_firmware_version()
        try:
            self._data = self.get_all_data()[0]
        except IndexError:
            _LOGGER.error('failed to retrieve data', exc_info=True)

    @property
    def device_state_attributes(self):
        """Return other details about the sensor state."""
        if self._data:
            attributes = dict(humidity=self._data['Humidity'],
                              fan_is_on=self._data['FanIsOn'],
                              iaq=self._data['Iaq'],
                              # Clairy is up to date, if no one requires a firmware update
                              up_to_date=not [clairy for clairy in self._profile['clairy']
                                              if not clairy['FirmwareUpdated']])
            if not attributes['up_to_date']:
                attributes['change_log'] = self._firmware_version['Changelog']
            return attributes
        return None

    @property
    def _token(self):
        """Get the access_token to get device info."""
        if self.__token is None:
            try:
                with open('.token') as json_file:
                    self.__token = json.load(json_file)
                    _LOGGER.info('token loaded from file')
            except FileNotFoundError:
                pass
        if self.__token is not None:
            # When using python 3.6 (or older), use the following code instead of fromisoformat()
            # expires = datetime.datetime.strptime(self.__token['expires'], "%Y-%m-%dT%H:%M:%S")
            expires = datetime.datetime.fromisoformat(self.__token['expires'])
            if expires < (datetime.datetime.now() - datetime.timedelta(seconds=10)):
                # token is expired (or will expire within 10 seconds)
                self.__token = None
                _LOGGER.info('token expired')
        if self.__token is None:
            now = datetime.datetime.now()
            token = requests.post(
                f'{self.url}/token',
                data=dict(grant_type="password",
                          username="appClairy",
                          Password="$2UcLVmwC#x6")).json()
            expires = now + datetime.timedelta(seconds=token['expires_in'])
            self.__token = dict(access_token=token['access_token'],
                                expires=expires.isoformat().split('.')[0])  # remove microseconds
            with open('.token', 'w') as outfile:
                json.dump(self.__token, outfile)
            _LOGGER.info('new token retrieved')
        return self.__token['access_token']

    @property
    def _headers(self):
        return dict(Authorization=f'Bearer {self._token}')

    def _get_version(self):
        """Retrieve the version of the API.

        @return {'baseurl': 'api.clairy.co',
                 'version': 4}
        """
        return requests.get(f'{self.url}/api/GetBaseUrl/Init?Version=1').json()

    def _get_firmware_version(self):
        """Retrieve the firmware version.

        @return {'File': '/Files/F091601_beta48_0x4E63819F.BIN',
                 'Version': 'F091601_beta48',
                 'CRC': '4E63819F',
                 'Changelog': '- Clairy connection bug fixed'}
        """
        return requests.get(f'{self.url}/api/Device/GetLastFirmware',
                            headers=self._headers).json()['firmware']

    def _get_file(self):
        """Retrieve a new firmware image."""
        return requests.get(f'{self.url}/{self._firmware_version["File"]}')

    def _get_profile(self):
        """Retrieve the user and clairy device profile.

        @return {'user': {'Id': '<self.__user_id>',
                          'FullName': None,
                          'Gender': 0,
                          'BirthDate': '<yyyy-mm-ddT00:00:00>',
                          'Email': '<name>@<provider>'},
                 'clairy': [{'ID': '<self.__serial>',
                             'Label': 'Clairy',
                             'Latitude': 0.0,
                             'Longitude': 0.0,
                             'City': '<city>',
                             'TreeType': 3,
                             'Color': 3,
                             'Location': 3,
                             'IsDeviceOnline': False,
                             'Iaq': 1000.0,
                             'FirmwareUpdated': True,
                             'FirmwareVersion': 'F091601_beta48'}]}
        """
        profile = requests.get(f'{self.url}/api/User/profile?userId={self.__user_id}').json()
        _LOGGER.debug('profile=%s', profile)
        return profile


    def get_instant_data(self):
        """Get instant data.

        @return {'Timers': [],
                 'Device': None,
                 'Serial': '<self.__serial>',
                 'Date': '2019-10-12T13:20:17',
                 'Temperature': 22.7,
                 'Humidity': 56.4,
                 'FanIsOn': False,
                 'Iaq': 1000.0}
        """
        # TODO: what does this do? It seems to retrieve old data...
        return requests.get(f'{self.url}/api/Device/GetInstantData?Serial={self.__serial}',
                            headers=self._headers).json()['data']

    def get_all_data(self, start_date=None):
        """Retrieve all measured data for the specified period until now.

        @return [{'Device': None,
                  'Serial': None,
                  'Date': '2019-12-04T11:22:00',
                  'Temperature': 23.5,
                  'Humidity': 40.6,
                  'FanIsOn': False,
                  'Iaq': 1000.0}]
        """
        if start_date is None:
            start_date = datetime.datetime.utcnow() - datetime.timedelta(hours=1)
        if not isinstance(start_date, str):
            start_date = start_date.isoformat()
        url = f'{self.url}/api/Device/GetAllData?Serial={self.__serial}&StartDate={start_date}'
        _LOGGER.debug('url=%s', url)
        _LOGGER.debug('headers=%s', self._headers)
        return requests.get(url, headers=self._headers).json()
