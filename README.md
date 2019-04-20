# hassio_ngrok
This custom-component allows to create automatically a ngrok tunnel. So, if your Home Assistant server is behind a CGNAT (no way to have a public IPv4), this custom-component helps to get access to the Home Assistant web interface.

Install
============

1. **Copy all the ".py" files into your "/config/custom_components/ngrok" folder.**
- Your configuration should look like:
```
config
  custom_components
    ngrok
      __init__.py
      
```
2. **Remember to reboot Hassio (or Home Assistant)**

Configuration
============

**Add your Ngrok details to configuration.yaml**
- auth_token [Mandatory] copy here the auth token assigned by [ngrok](https://ngrok.com/) 
- os_version [Mandatory] you can choose from:
  1. Linux (ARM) [Default, Raspberry Pi]
  2. Mac OS X
  3. Linux
  4. Mac (32-Bit)
  5. Windows (32-Bit)   
  6. Linux (32-Bit)
  7. FreeBSD (64-Bit)
  8. FreeBSD (32-Bit)  
- ip_address [Mandatory] the local ip addreess (e.g. 192.168.x.y)
- port: [Mandatory] the local port (e.g. 8123)
- protocol: [Mandatory] http or https
- scan_interval: [Optional] seconds between two consecutive checks of ngrok configuration. Default is 60 seconds.
- install_dir: [Optional] directory where ngrok will be installed. Default is '.ngrock'
 
**Your configuration should look like:**
```
ngrok:
  auth_token: !secret ngrok_auth_token
  os_version: 'Linux (ARM)'
  ip_address: !secret ngrok_ip_address
  port: !secret ngrok_port
  protocol: 'http'
```

State
============

**If everything work, you should see under "/lovelace/hass-unused-entities" a new state like this:**

![ngrok.public_url](res/ngrok.public_url.png)

Automation
============

**How to be informed once your Home Assistant get a public url?**
- The best way is to create an automation that sends a Telegram message, as soon as Home Assistant gets a public url 
or when it changes. 
- To enable it, you need first to activate the [Telegram component](https://www.home-assistant.io/components/telegram/);
- Then, edit your automations.yaml file:
```
- alias: "Ngrok Public URL"
  initial_state: 'on'
  trigger:
    platform: state
    entity_id: ngrok.public_url
  action:
  - service: notify.telegram
    data:
      title: '*Server*'
      message: 'Current public url: {{ ngrok.public_url.state }}'
```

Debug
============

**To enable debug diagnostics, add this to your configuration.yaml:**
```
logger:
  default: WARNING
  logs:
    ngrok: DEBUG
```
