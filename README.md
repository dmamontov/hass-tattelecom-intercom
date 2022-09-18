# Таттелеком Домофон для Home Assistant
[![hacs_badge](https://img.shields.io/badge/HACS-Custom-41BDF5.svg?style=for-the-badge)](https://github.com/hacs/integration)
[![CodeQL](https://img.shields.io/badge/CODEQL-Passing-30C854.svg?style=for-the-badge)](https://github.com/dmamontov/hass-seafile/actions?query=CodeQL)
[![Telegram](https://img.shields.io/badge/Telegram-channel-34ABDF.svg?style=for-the-badge)](https://t.me/hass_mamontov_tech)

Компонент предназначен для интеграции [Таттелеком Домофон](https://tattelecom.ru/domofon/) в [Home Assistant](https://www.home-assistant.io/).

❗ Производитель домофонов использует для видео HLS стрим, что приводит к задержке видео около 5-10 секунд.

## Требования
* Включенная интеграция: [ffmpeg](https://www.home-assistant.io/integrations/ffmpeg/)
* Установлен пакет: [httpx\[http2\]](https://pypi.org/project/httpx/)
* Для [SIP](https://ru.wikipedia.org/wiki/%D0%9F%D1%80%D0%BE%D1%82%D0%BE%D0%BA%D0%BE%D0%BB_%D1%83%D1%81%D1%82%D0%B0%D0%BD%D0%BE%D0%B2%D0%BB%D0%B5%D0%BD%D0%B8%D1%8F_%D1%81%D0%B5%D0%B0%D0%BD%D1%81%D0%B0) открыт UDP порт: **60266**
* Для [RTP](https://ru.wikipedia.org/wiki/Real-time_Transport_Protocol) окрыты UDP порты: **10000-20000**

## Больше информации
- [Установка](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Установка)
- [Конфигурация](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Конфигурация)
- [Сущности](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Сущности)
- [Примеры автоматизаций](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Примеры-автоматизаций)
  - [Автоматическое открытие](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Примеры-автоматизаций#Автоматическое-открытие)
  - [Автоответчик](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Примеры-автоматизаций#Автоответчик)
- [Диагностика](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Диагностика)
- [Отказ от ответственности](https://github.com/dmamontov/hass-tattelecom-intercom/wiki/Отказ-от-ответственности)

## Установка
Самый простой способ настроить интеграцию с Таттелеком Домофон — использовать [HACS](https://hacs.xyz/). Сначала установите [HACS](https://hacs.xyz/), если он у вас еще не установлен. После установки вам нужно добавить этот репозиторий как пользовательский, после чего вы сможете найти эту интеграцию в магазине HACS в разделе интеграции.

Кроме того, вы можете установить его вручную. Просто скопируйте и вставьте содержимое папки hass-tattelecom-intercom/custom_components в каталог config/custom_components. Например, вы получите файл sensor.py по следующему пути: /config/custom_components/tattelecom_intercom/sensor.py. Недостатком ручной установки является то, что вы не будете получать уведомления об обновлениях.

## Конфигурация
**Через графический интерфейс**

`Настройки` > `Интеграции` > `Плюс` > `Таттелеком Домофон`

❗ Если вы введете свой номер телефона, это приведет к де авторизации на вам телефоне. Для интеграции рекомендую пригласить пользователя(у которого не будет приложения) в вашем профиле и настроить интеграцию на его телефон.

❗ Через YAML (устаревший способ) не поддерживается

## Отказ от ответственности
Данное программное обеспечение никак не связано и не одобрено ПАО «ТАТТЕЛЕКОМ», владельца торговой марки «Домофон Летай». Используйте его на свой страх и риск. Автор ни при каких обстоятельствах не несёт ответственности за порчу или утрату вашего имущества и возможного вреда в отношении третьих лиц.

Все названия брендов и продуктов принадлежат их законным владельцам.



