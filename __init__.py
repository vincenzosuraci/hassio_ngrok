from datetime import timedelta
import logging
import voluptuous as vol
from os.path import dirname, basename
import urllib.request
import zipfile
import os
import subprocess
import stat
import threading
import json

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
OBJECT_ID_PUBLIC_URL = 'public_url'

""" NGRok authentication token """
CONF_NGROK_AUTH_TOKEN = 'auth_token'
CONF_NGROK_INSTALL_DIR = 'install_dir'
CONF_NGROK_OS_VERSION = 'os_version'

""" NGrok authentication token """
CONF_HA_LOCAL_PROTOCOL = 'protocol'
CONF_HA_LOCAL_IP_ADDRESS = 'ip_address'
CONF_HA_LOCAL_PORT = 'port'

""" Optional parameters """
DEFAULT_SCAN_INTERVAL = timedelta(seconds=5)
DEFAULT_NGROK_INSTALL_DIR = '.ngrock'
DEFAULT_NGROK_OS_VERSION = 'Linux (ARM)'
DEFAULT_HA_LOCAL_PROTOCOL = 'http'

CONFIG_SCHEMA = vol.Schema({
    DOMAIN: vol.Schema({
        vol.Required(CONF_NGROK_AUTH_TOKEN): cv.string,
        vol.Required(CONF_HA_LOCAL_IP_ADDRESS): cv.string,
        vol.Required(CONF_HA_LOCAL_PORT): cv.port,
        vol.Required(CONF_HA_LOCAL_PROTOCOL, default=DEFAULT_HA_LOCAL_PROTOCOL): cv.string,
        vol.Required(CONF_NGROK_OS_VERSION, default=DEFAULT_NGROK_OS_VERSION): cv.string,

        vol.Optional(CONF_NGROK_INSTALL_DIR, default=DEFAULT_NGROK_INSTALL_DIR): cv.string,
        vol.Optional(CONF_SCAN_INTERVAL, default=DEFAULT_SCAN_INTERVAL): cv.time_period,
    })
}, extra=vol.ALLOW_EXTRA)

NGROK_EXECUTABLE_URL_MAP = {
    'Mac OS X': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-amd64.zip', 'ext': '', 'prefix': './'},
    'Linux': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-amd64.zip', 'ext': '', 'prefix': './'},
    'Mac (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-darwin-386.zip', 'ext': '', 'prefix': './'},
    'Windows (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-windows-386.zip', 'ext': '.exe', 'prefix': ''},
    'Linux (ARM)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-arm.zip', 'ext': '', 'prefix': './'},
    'Linux (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-linux-386.zip', 'ext': '', 'prefix': './'},
    'FreeBSD (64-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-freebsd-amd64.zip', 'ext': '', 'prefix': './'},
    'FreeBSD (32-Bit)': {'url': 'https://bin.equinox.io/c/4VmDzA7iaHb/ngrok-stable-freebsd-386.zip', 'ext': '', 'prefix': './'},
}

async def async_setup(hass, config):

    _LOGGER.debug('async_setup()')

    """Get Meross Component configuration"""
    ngrok_auth_token = config[DOMAIN][CONF_NGROK_AUTH_TOKEN]
    ngrok_install_dir = config[DOMAIN][CONF_NGROK_INSTALL_DIR]
    ha_local_ip_address = config[DOMAIN][CONF_HA_LOCAL_IP_ADDRESS]
    ha_local_port = config[DOMAIN][CONF_HA_LOCAL_PORT]
    ha_local_protocol = config[DOMAIN][CONF_HA_LOCAL_PROTOCOL]
    scan_interval = config[DOMAIN][CONF_SCAN_INTERVAL]
    ngrok_os_version = config[DOMAIN][CONF_NGROK_OS_VERSION]

    hass.data[DOMAIN] = {
        'thread': None,
        'public_url': None,
    }

    def thread_run_ngrok(command_line):
        try:
            _LOGGER.debug('Executing: ' + str(command_line))
            output_bytes = subprocess.run(command_line, capture_output=True)
            output_str = output_bytes.stdout.decode()
            _LOGGER.debug(output_str)
        except subprocess.CalledProcessError as CPE:
            _LOGGER.error('ERROR: ' + str(CPE))
        pass

    """ Check if NGRok is installed """
    async def async_ngrok_installation():

        if ngrok_os_version in NGROK_EXECUTABLE_URL_MAP:

            # get the prefix for the executable file
            prefix = NGROK_EXECUTABLE_URL_MAP[ngrok_os_version]['prefix']

            # get the executable ngrok file extension (e.g. ".exe" in windows, "" in linux)
            ext = NGROK_EXECUTABLE_URL_MAP[ngrok_os_version]['ext']

            # get the current ngrok custom-component folder
            ngrok_custom_component_dir = os.path.dirname(os.path.realpath(__file__))

            # get up of 2 folders >>> up to homeassistant config directory
            homeassitant_dir = dirname(dirname(ngrok_custom_component_dir))

            # Check if homeassistant config dir exists...
            if os.path.isdir(homeassitant_dir):
                _LOGGER.debug(homeassitant_dir + ' dir exists')

                # ngrok installation dir
                ngrok_dir = os.path.join(homeassitant_dir, ngrok_install_dir)

                # Check if ngrok dir exists
                if not os.path.isdir(ngrok_dir):
                    # ngrok dir does not exists >>> create it!
                    _LOGGER.debug(ngrok_dir + ' dir does not exist')
                    try:
                        # trying to create ngrok dir
                        os.mkdir(ngrok_dir)
                    except OSError:
                        _LOGGER.error("Creation of the ngrok directory %s failed" % ngrok_dir)
                    else:
                        # ngrok dir created!
                        _LOGGER.debug(ngrok_dir + ' dir created')

                # Check if ngrok dir exists
                if os.path.isdir(ngrok_dir):

                    # Create path to ngrok execution file
                    ngrok_file = os.path.join(ngrok_dir, 'ngrok')
                    ngrok_file_ext = ngrok_file + ext

                    # Check if ngrok execution file exists
                    if not os.path.isfile(ngrok_file_ext):
                        # ngrok execution file does not exist >>> try to get it
                        _LOGGER.debug(ngrok_file + ext + ' file not found >>> downloading it...')

                        # get url to download ngrok zip file on the basis of OS version
                        url = NGROK_EXECUTABLE_URL_MAP[ngrok_os_version]['url']

                        # get zip filename and related file
                        ngrok_zip_filename = basename(url)
                        ngrok_zip_file = os.path.join(ngrok_dir, ngrok_zip_filename)

                        # downloading ngrok zip filename
                        _LOGGER.debug('Downloading ngrok zip file...')
                        urllib.request.urlretrieve(url, ngrok_zip_file)

                        # check if download succeeded
                        if os.path.isfile(ngrok_zip_file):
                            # ngork download succeessfully
                            _LOGGER.debug('ngrok zip file downloaded')
                            # unzip ngork downloaded zip file...
                            zip_ref = zipfile.ZipFile(ngrok_zip_file, 'r')
                            _LOGGER.debug('Extracting ngrok zip file...')
                            zip_ref.extractall(ngrok_dir)
                            zip_ref.close()
                        else:
                            _LOGGER.error('ngrok zip file download failed')

                    # Check if ngrok execution file exists
                    if os.path.isfile(ngrok_file_ext):
                        # ngrok execution file exists!
                        _LOGGER.debug(ngrok_file_ext + ' file found.')
                        _LOGGER.debug('Changing working directory to: ' + ngrok_dir)
                        # make ngrok file executable
                        if not os.access(ngrok_file + ext, os.X_OK):
                            os.chmod(ngrok_file_ext, stat.S_IEXEC)
                        # changing working directory to ngrok directory
                        os.chdir(ngrok_dir)
                        _LOGGER.debug('working directory is: ' + os.getcwd())
                        # create command line to generate authentication token
                        ngrok_exec = prefix + 'ngrok' + ext
                        # command_line = [ngrok_exec, 'authtoken', ngrok_auth_token]
                        command_line = [ngrok_exec , 'authtoken' , ngrok_auth_token]
                        _LOGGER.debug('Executing: ' + str(command_line))
                        try:
                            output_bytes = subprocess.run(command_line, capture_output=True)
                            output_str = output_bytes.stdout.decode()
                            needle = 'Authtoken saved to configuration file'
                            if output_str[0:len(needle)] == needle:
                                _LOGGER.debug(output_str)
                                # command_line = [ngrok_exec, 'tcp', ha_local_ip_address + ':' + str(ha_local_port)]
                                command_line = [ngrok_exec , 'tcp' , ha_local_ip_address + ':' + str(ha_local_port)]
                                # create thread and starts it
                                hass.data[DOMAIN]['thread'] = threading.Thread(target=thread_run_ngrok, args=[command_line])
                                hass.data[DOMAIN]['thread'].start()
                            else:
                                _LOGGER.error('saving ngrok authentication token failed')
                                _LOGGER.error(output_str)
                        except (subprocess.CalledProcessError, PermissionError) as E:
                            _LOGGER.error('Permission error')
                            _LOGGER.debug(str(E))
                            _LOGGER.debug(oct(stat.S_IMODE(os.lstat(ngrok_file + ext).st_mode)))
                            _LOGGER.debug(oct(stat.S_IMODE(os.stat(ngrok_file + ext).st_mode)))
                            _LOGGER.debug(os.access(ngrok_file + ext, os.X_OK))
                            pass
                    else:
                        # ngrok installation dir does not exists!
                        _LOGGER.error('ngrok execution file not found: '+ngrok_file_ext)
                else:
                    # ngrok installation dir does not exists!
                    _LOGGER.error(ngrok_install_dir + ' dir does not exist')
            else:
                # homeassistant config dir does not exists!
                _LOGGER.error(homeassitant_dir + ' dir does not exist')

        else:
            # os version not supported...
            _LOGGER.error('ngrok os version ' + ngrok_os_version + ' is not supported')

        pass

    await async_ngrok_installation()

    """ Called at the very beginning and periodically, each 5 seconds """
    async def async_update_ngrok_status():
        _LOGGER.debug('async_update_devices_status()')

        public_url = None

        url = 'http://localhost:4040/api/tunnels'
        _LOGGER.debug('Connecting to ' + url)
        try:
            resource = urllib.request.urlopen(url)
            charset = resource.headers.get_content_charset()
            if charset is None:
                charset = 'utf8'
            json_str = resource.read().decode(charset)
            json_dict = json.loads(json_str)
            if 'tunnels' in json_dict:
                if len(json_dict['tunnels']) > 0:
                    if 'public_url' in json_dict['tunnels'][0]:
                        public_url = json_dict['tunnels'][0]['public_url']
        except (ConnectionRefusedError, urllib.error.URLError) as E:
            _LOGGER.error(str(E))
            pass

        if public_url is not None:
            if public_url[0:5] == 'https':
                public_url = ha_local_protocol + public_url[4:]
            else:
                public_url = ha_local_protocol + public_url[3:]

        if public_url != hass.data[DOMAIN]['public_url']:
            _LOGGER.debug('public url changed in ' + str(public_url))
            hass.data[DOMAIN]['public_url'] = public_url
            attributes = {"icon": "mdi:transit-connection-variant"}
            hass.states.async_set(DOMAIN + "." + OBJECT_ID_PUBLIC_URL, str(public_url), attributes)
            if public_url is None:
                # since the public url has become None, restart ngrok
                hass.async_create_task(async_ngrok_installation())
        pass

    await async_update_ngrok_status()

    """ Called at the very beginning and periodically, each 5 seconds """
    async def async_periodic_update_ngrok_status(event_time):
        _LOGGER.debug('async_periodic_update_ngrok_status()')
        hass.async_create_task(async_update_ngrok_status())
        pass

    """ This is used to update the Meross Devices status periodically """
    async_track_time_interval(hass, async_periodic_update_ngrok_status, scan_interval)

    return True
