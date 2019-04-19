from datetime import timedelta
import logging
import voluptuous as vol
from os.path import dirname, basename
import urllib.request
import zipfile
import os
import subprocess
import stat

from homeassistant.const import (CONF_SCAN_INTERVAL)
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_track_time_interval


""" NGRok for Hassio: https://community.home-assistant.io/t/ngrok-and-hass-io/33953/2 """


""" Setting log """
_LOGGER = logging.getLogger('ngrok_init')
_LOGGER.setLevel(logging.DEBUG)

""" This is needed, it impact on the name to be called in configurations.yaml """
""" Ref: https://developers.home-assistant.io/docs/en/creating_integration_manifest.html"""
DOMAIN = 'ngrok'

""" NGRok authentication token """
CONF_NGROK_AUTH_TOKEN = 'ngrok_auth_token'
CONF_NGROK_INSTALL_DIR = 'ngrok_install_dir'
CONF_NGROK_OS_VERSION = 'ngrok_os_version'

""" NGrok authentication token """
CONF_HA_LOCAL_IP_ADDRESS = 'ha_local_ip_address'
CONF_HA_LOCAL_PORT = 'ha_local_port'

""" Optional parameters """
DEFAULT_SCAN_INTERVAL = timedelta(seconds=600)
DEFAULT_NGROK_INSTALL_DIR = '/.ngrock'
DEFAULT_NGROK_OS_VERSION = 'Linux (ARM)'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_NGROK_AUTH_TOKEN): cv.string,
        vol.Required(CONF_HA_LOCAL_IP_ADDRESS): cv.string,
        vol.Required(CONF_HA_LOCAL_PORT): cv.port,
        vol.Required(CONF_NGROK_OS_VERSION): cv.string,

        vol.Optional(CONF_NGROK_INSTALL_DIR, default=DEFAULT_NGROK_INSTALL_DIR): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    })
}, extra=vol.ALLOW_EXTRA)

NGROK_EXECUTABLE_URL_MAP = {
    'Mac OS X': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-amd64.zip', 'ext': ''},
    'Linux': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip', 'ext': ''},
    'Mac (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-386.zip', 'ext': ''},
    'Windows (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-386.zip', 'ext': '.exe'},
    'Linux (ARM)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip', 'ext': ''},
    'Linux (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-386.zip', 'ext': ''},
    'FreeBSD (64-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-freebsd-amd64.zip', 'ext': ''},
    'FreeBSD (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-freebsd-386.zip', 'ext': ''},
}

async def async_setup(hass, config):

    _LOGGER.debug('async_setup()')

    """Get Meross Component configuration"""
    ngrok_auth_token = config[DOMAIN][CONF_NGROK_AUTH_TOKEN]
    ngrok_install_dir = config[DOMAIN][CONF_NGROK_INSTALL_DIR]
    ha_local_ip_address = config[DOMAIN][CONF_HA_LOCAL_IP_ADDRESS]
    ha_local_port = config[DOMAIN][CONF_HA_LOCAL_PORT]
    scan_interval = config[DOMAIN][CONF_SCAN_INTERVAL]
    ngrok_os_version = config[DOMAIN][CONF_NGROK_OS_VERSION]

    hass.data[DOMAIN] = {
    }

    """ Add a state """
    hass.states.async_set('hello_state.world', 'Paulus')

    async def async_run_ngrok(command_line):
        _LOGGER.debug('Executing: ' + str(command_line))
        output_bytes = subprocess.check_output(command_line, shell=True)
        output_str = output_bytes.decode('utf8')
        _LOGGER.debug('output: ' + output_str)
        pass

    """ Check if NGRok is installed """
    async def async_ngrok_installation():

        if ngrok_os_version in NGROK_EXECUTABLE_URL_MAP:

            ext = NGROK_EXECUTABLE_URL_MAP[ngrok_os_version]['ext']

            # get the current custom component foldder
            ngrok_custom_component_dir = os.path.dirname(os.path.realpath(__file__))

            # get up of 2 folders
            homeassitant_dir = dirname(dirname(ngrok_custom_component_dir))

            # Check if ngrok_install_dir exists
            if os.path.isdir(homeassitant_dir):
                _LOGGER.debug(homeassitant_dir + ' dir exists')

                # Check if ngrok dir exists
                ngrok_dir = homeassitant_dir + ngrok_install_dir
                if not os.path.isdir(ngrok_dir):
                    _LOGGER.debug(ngrok_dir + ' dir does not exist')
                    try:
                        os.mkdir(ngrok_dir)
                    except OSError:
                        _LOGGER.warning("Creation of the directory %s failed" % ngrok_dir)
                        return
                    else:
                        _LOGGER.debug("Successfully created the directory %s " % ngrok_dir)

                if os.path.isdir(ngrok_dir):
                    # Check if ngrok exists
                    ngrok_file = ngrok_dir + '/ngrok'
                    if not os.path.isfile(ngrok_file + ext):
                        _LOGGER.debug(ngrok_file + ext + ' file not found >>> downloading it...')
                        url = NGROK_EXECUTABLE_URL_MAP[ngrok_os_version]['url']
                        ngrok_zip_filename = basename(url)
                        ngrok_zip_file = ngrok_dir + '/' + ngrok_zip_filename
                        _LOGGER.debug('Downloading ngrok zip file...')
                        urllib.request.urlretrieve(url, ngrok_zip_file)

                        if os.path.isfile(ngrok_zip_file):
                            _LOGGER.debug('ngrok zip file downloaded')
                            zip_ref = zipfile.ZipFile(ngrok_zip_file, 'r')
                            _LOGGER.debug('Extracting ngrok zip file...')
                            zip_ref.extractall(ngrok_dir)
                            zip_ref.close()
                        else:
                            _LOGGER.warning('ngrok zip file download FAILED')

                    if os.path.isfile(ngrok_file + ext):
                        _LOGGER.debug(ngrok_file + ext + ' file found.')
                        _LOGGER.debug('Changing working directory to: ' + ngrok_dir)
                        os.chdir(ngrok_dir)
                        _LOGGER.debug('working directory is: ' + os.getcwd())
                        command_line = ['ngrok' + ext, 'authtoken', ngrok_auth_token]
                        _LOGGER.debug('Executing: ' + str(command_line))
                        try:
                            output_bytes = subprocess.check_output(command_line, shell=True)
                            output_str = output_bytes.decode('utf8')
                            _LOGGER.debug('output: ' + output_str)

                            command_line = ['ngrok' + ext, 'tcp', ha_local_ip_address + ':' + str(ha_local_port)]
                            hass.async_create_task(async_run_ngrok(command_line))

                        except PermissionError as PE:
                            _LOGGER.debug('Permission error')
                            _LOGGER.debug(str(PE))
                            _LOGGER.debug(oct(stat.S_IMODE(os.lstat(ngrok_file + ext).st_mode)))
                            _LOGGER.debug(oct(stat.S_IMODE(os.stat(ngrok_file + ext).st_mode)))
                            _LOGGER.debug(os.access(ngrok_file + ext, os.X_OK))
                            pass

            else:
                _LOGGER.warning(ngrok_install_dir + ' dir does not exist')

        else:
            _LOGGER.warning('ngrok os version ' + ngrok_os_version + ' is not supported')

        pass

    await async_ngrok_installation()

    """ Called at the very beginning and periodically, each 5 seconds """
    async def async_update_ngrok_status():
        _LOGGER.debug('async_update_devices_status()')

    await async_update_ngrok_status()

    """ Called at the very beginning and periodically, each 5 seconds """
    async def async_periodic_update_ngrok_status(event_time):
        #await async_update_devices_status()
        hass.async_create_task(async_update_ngrok_status())

    """ This is used to update the Meross Devices status periodically """
    async_track_time_interval(hass, async_periodic_update_ngrok_status, scan_interval)

    return True


