"""Analyzing Clairy sensor data.

Clairy is a smart device that can clean your room's air as well as measure indoor air quality levels, humidity and temperature.
"""
from configparser import ConfigParser
import datetime
import json
import requests

class Clairy:
    """Access your Clairy.
    
    See https://vitesy.com/
    """
    def __init__(self):
        self.url = 'http://api.clairy.co'
        self.__token = None
        self.__serial = None
        
    @property
    def _serial(self):
        """Get the Clairy serial number."""
        # External config file, so serial is hidden from Github
        # Create a config.ini file with the following content to use the script
        # [auth]  
        # serial = yourSerial123
        if self.__serial is None:
            config = ConfigParser()
            config.read('config.ini')
            self.__serial = config.get('auth', 'serial')
        return self.__serial
    
    @property
    def _userId(self):
        """Get the user ID of the owner of Clairy."""
        if self.__userId is None:
            config = ConfigParser()
            config.read('config.ini')
            self.__userId = config.get('auth', 'userId')
        return self.__userId

    @property
    def _token(self):
        """Get the access_token to get device info."""
        if self.__token is None:
            try:
                with open('.token') as json_file:
                    self.__token = json.load(json_file)
                    print('token loaded from file')
            except FileNotFoundError:
                pass
        if self.__token is not None:
            # TODO: when moving to python 3.7, use fromisoformat()
            expires = datetime.datetime.strptime(self.__token['expires'], "%Y-%m-%dT%H:%M:%S")
            if expires < (datetime.datetime.now() - datetime.timedelta(seconds=10)):
                # token is expired (or will expire within 10 seconds)
                self.__token = None
                print('token expired')
        if self.__token is None:
            now = datetime.datetime.now()
            token = requests.post(f'{self.url}/token', data=dict(grant_type = "password",
                                                                 username = "appClairy",
                                                                 Password = "$2UcLVmwC#x6")).json()
            expires = now + datetime.timedelta(seconds=token['expires_in'])
            self.__token = dict(access_token = token['access_token'],
                                expires = expires.isoformat().split('.')[0])  # remove microseconds
            with open('.token', 'w') as outfile:
                json.dump(self.__token, outfile)
            print('new token retrieved')
        return self.__token['access_token']

    @property
    def _headers(self):
        return dict(Authorization = f'Bearer {self._token}')
    def GetVersion(self):
        return requests.get(f'{self.url}/api/GetBaseUrl/Init?Version=1').json()
    def GetFirmwareVersion(self):
        return requests.get(f'{self.url}/api/Device/GetLastFirmware', headers=self._headers).json()
    def GetFile(self):
        # TODO: what's this?
        return requests.get(f'{self.url}/api/Files/F091601_beta48_0x4E63819F.BIN')
    def GetPorfile(self):
        # TODO: move userId to config.ini
        return requests.get(f'{self.url}/api/User/profile?UserID=self._userId').json()
    def GetInstantData(self):
        return requests.get(f'{self.url}/api/Device/GetInstantData?Serial={self._serial}', headers=self._headers).json()
    def GetAllData(self, startDate=datetime.datetime.utcnow()-datetime.timedelta(hours=1)):
        return requests.get(f'{self.url}/api/Device/GetAllData?Serial={self._serial}&StartDate={startDate.isoformat()}', headers=self._headers).json()
