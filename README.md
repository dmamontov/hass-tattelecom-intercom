# Seafile for Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![CodeQL](https://img.shields.io/badge/CODEQL-Passing-30C854.svg?style=for-the-badge)](https://github.com/dmamontov/hass-seafile/actions?query=CodeQL)
[![Telegram](https://img.shields.io/badge/Telegram-channel-34ABDF.svg?style=for-the-badge)](https://t.me/hass_mamontov_tech)

The component is designed to integrate the [Seafile](https://www.seafile.com/en/home/) file storage, editing and synchronization service into [Home Assistant](https://www.home-assistant.io/).

The component adds the ability to view `media files` directly from HASS and also configure automation for the amount of data occupied for each user.

## Requirements
* Seafile >= [7.1.3](https://manual.seafile.com/changelog/server-changelog/#713-20200326)

## More info

- [Install](https://github.com/dmamontov/hass-seafile/wiki/Install)
- [Config](https://github.com/dmamontov/hass-seafile/wiki/Config)
- [Entities](https://github.com/dmamontov/hass-seafile/wiki/Entities)
- [Diagnostics](https://github.com/dmamontov/hass-seafile/wiki/Diagnostics)
- [Preview](https://github.com/dmamontov/hass-seafile/wiki/Preview)

## Install
The easiest way to set up integration with Seafile is to use [HACS](https://hacs.xyz/). Install [HACS](https://hacs.xyz/) first if you don't already have it. After installation, you need to add this repository as a custom one, and then you can find this integration in the [HACS](https://hacs.xyz/)store in the integration section.

Alternatively, you can install it manually. Just copy and paste the content of the hass-seafile/custom_components folder in your config/custom_components directory. As example, you will get the sensor.py file in the following path: /config/custom_components/seafile/sensor.py. The disadvantage of a manual installation is that you won’t be notified about updates.

## Config
**Via GUI**

`Settings` > `Integrations` > `Plus` > `Seafile`

To connect, enter the ip address and port. And also if you use basic auth, enter the user and password.

❗ Via YAML (legacy way) not supported

## Preview

![](images/media.png)
