# Таттелеком Домофон для Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![CodeQL](https://img.shields.io/badge/CODEQL-Passing-30C854.svg?style=for-the-badge)](https://github.com/dmamontov/hass-seafile/actions?query=CodeQL)
[![Telegram](https://img.shields.io/badge/Telegram-channel-34ABDF.svg?style=for-the-badge)](https://t.me/hass_mamontov_tech)

Компонент предназначен для интеграции [Таттелеком Домофон](https://tattelecom.ru/domofon/) в [Home Assistant](https://www.home-assistant.io/).

## Требования
* Включенная интеграция: [ffmpeg](https://www.home-assistant.io/integrations/ffmpeg/)
* Установлен пакет: [httpx\[http2\]](https://pypi.org/project/httpx/)
* Для [SIP](https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%BE%D1%82%D0%BE%D0%BA%D0%BE%D0%BB_%D1%83%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F_%D1%81%D0%B5%D0%B0%D0%BD%D1%81%D0%B0) окрыт UDP порт: **60266**
* Для [RTP](https://ru.wikipedia.org/wiki/Real-time_Transport_Protocol) окрыты UDP порты: **10000-20000**

## Больше информации