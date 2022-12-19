"""Tests for the tattelecom_intercom component."""

# pylint: disable=no-member,too-many-statements,protected-access,too-many-lines

from __future__ import annotations

import logging
from unittest.mock import AsyncMock, patch

import pytest
from homeassistant import config_entries, data_entry_flow, setup
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_TIMEOUT, CONF_TOKEN
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tattelecom_intercom.const import (
    CONF_LOGIN,
    CONF_PHONE,
    CONF_SMS_CODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
)
from custom_components.tattelecom_intercom.exceptions import (
    IntercomConnectionError,
    IntercomNotFoundError,
    IntercomUnauthorizedError,
)
from tests.setup import MOCK_CODE, MOCK_LOGIN, MOCK_PHONE, MOCK_TOKEN, async_mock_client

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Enable custom integrations"""

    yield


@pytest.mark.asyncio
async def test_config_flow(hass: HomeAssistant) -> None:
    """Test config flow.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"

        assert len(mock_client.mock_calls) == 2

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["title"] == str(MOCK_PHONE)
        assert result_configure["data"][CONF_PHONE] == MOCK_PHONE
        assert result_configure["data"][CONF_SMS_CODE] == MOCK_CODE
        assert result_configure["data"][CONF_TOKEN] == MOCK_TOKEN

        assert len(mock_client.mock_calls) == 4
        assert len(mock_async_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_config_flow_with_register(hass: HomeAssistant) -> None:
    """Test config flow with register.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.signin = AsyncMock(side_effect=IntercomNotFoundError)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "register"

        assert len(mock_client.mock_calls) == 2

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_LOGIN: MOCK_LOGIN,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"

        assert len(mock_client.mock_calls) == 3

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["title"] == str(MOCK_PHONE)
        assert result_configure["data"][CONF_PHONE] == MOCK_PHONE
        assert result_configure["data"][CONF_SMS_CODE] == MOCK_CODE
        assert result_configure["data"][CONF_TOKEN] == MOCK_TOKEN
        assert result_configure["data"][CONF_LOGIN] == MOCK_LOGIN

        assert len(mock_client.mock_calls) == 5
        assert len(mock_async_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_config_flow_step_phone_connection_error(hass: HomeAssistant) -> None:
    """Test config flow step phone connection error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.signin = AsyncMock(side_effect=IntercomConnectionError)

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "phone"
        assert result_configure["errors"]["base"] == "connection.error"

        assert len(mock_client.mock_calls) == 2
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_phone_other_error(hass: HomeAssistant) -> None:
    """Test config flow step phone other error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.signin = AsyncMock(
            side_effect=IntercomUnauthorizedError("error")
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "phone"
        assert result_configure["errors"]["base"] == "error"

        assert len(mock_client.mock_calls) == 2
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_register_unauthorized_error(
    hass: HomeAssistant,
) -> None:
    """Test config flow step register unauthorized error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.signin = AsyncMock(side_effect=IntercomNotFoundError)
        mock_client.return_value.register = AsyncMock(
            side_effect=IntercomUnauthorizedError
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "register"

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_LOGIN: MOCK_LOGIN,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "phone"
        assert result_configure["errors"]["base"] == "unauthorized.error"

        assert len(mock_client.mock_calls) == 3
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_register_connection_error(hass: HomeAssistant) -> None:
    """Test config flow step register connection error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.signin = AsyncMock(side_effect=IntercomNotFoundError)
        mock_client.return_value.register = AsyncMock(
            side_effect=IntercomConnectionError
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "register"

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_LOGIN: MOCK_LOGIN,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "register"
        assert result_configure["errors"]["base"] == "connection.error"

        assert len(mock_client.mock_calls) == 3
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_register_other_error(hass: HomeAssistant) -> None:
    """Test config flow step register other error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.signin = AsyncMock(side_effect=IntercomNotFoundError)
        mock_client.return_value.register = AsyncMock(
            side_effect=IntercomNotFoundError("error")
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "register"

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_LOGIN: MOCK_LOGIN,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "register"
        assert result_configure["errors"]["base"] == "error"

        assert len(mock_client.mock_calls) == 3
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_confirm_unauthorized_error(hass: HomeAssistant) -> None:
    """Test config flow step confirm unauthorized error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.sms_confirm = AsyncMock(
            side_effect=IntercomUnauthorizedError
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "phone"
        assert result_configure["errors"]["base"] == "unauthorized.error"

        assert len(mock_client.mock_calls) == 3
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_confirm_connection_error(hass: HomeAssistant) -> None:
    """Test config flow step confirm connection error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.sms_confirm = AsyncMock(
            side_effect=IntercomConnectionError
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"
        assert result_configure["errors"]["base"] == "connection.error"

        assert len(mock_client.mock_calls) == 3
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_config_flow_step_confirm_other_error(hass: HomeAssistant) -> None:
    """Test config flow step confirm other error.

    :param hass: HomeAssistant
    """

    await setup.async_setup_component(hass, "http", {})
    result_init = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": config_entries.SOURCE_USER}
    )

    assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
    assert result_init["handler"] == DOMAIN
    assert result_init["step_id"] == "phone"

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        mock_client.return_value.sms_confirm = AsyncMock(
            side_effect=IntercomNotFoundError("error")
        )

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_PHONE: MOCK_PHONE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"

        result_configure = await hass.config_entries.flow.async_configure(
            result_init["flow_id"],
            {
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_configure["flow_id"] == result_init["flow_id"]
        assert result_configure["step_id"] == "confirm"
        assert result_configure["errors"]["base"] == "error"

        assert len(mock_client.mock_calls) == 3
        assert len(mock_async_setup_entry.mock_calls) == 0


@pytest.mark.asyncio
async def test_options_flow(hass: HomeAssistant) -> None:
    """Test options flow.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE: MOCK_PHONE,
            CONF_LOGIN: MOCK_LOGIN,
            CONF_SMS_CODE: MOCK_CODE,
            CONF_TOKEN: MOCK_TOKEN,
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "phone"

        assert CONF_TIMEOUT not in config_entry.options
        assert CONF_SCAN_INTERVAL not in config_entry.options

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_PHONE: MOCK_PHONE,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        assert config_entry.options[CONF_PHONE] == MOCK_PHONE
        assert config_entry.options[CONF_LOGIN] == MOCK_LOGIN
        assert config_entry.options[CONF_SMS_CODE] == MOCK_CODE
        assert config_entry.options[CONF_TOKEN] == MOCK_TOKEN

        assert config_entry.options[CONF_TIMEOUT] == DEFAULT_TIMEOUT
        assert config_entry.options[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL

        assert len(mock_async_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_options_flow_change_phone(hass: HomeAssistant) -> None:
    """Test options flow change phone.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE: 71110006655,
            CONF_LOGIN: "test",
            CONF_SMS_CODE: "001002",
            CONF_TOKEN: "0000000010101010101010101010101010101010101010",
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "phone"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_PHONE: MOCK_PHONE,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_save["step_id"] == "confirm"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        assert config_entry.options[CONF_PHONE] == MOCK_PHONE
        assert CONF_LOGIN not in config_entry.options
        assert config_entry.options[CONF_SMS_CODE] == MOCK_CODE
        assert config_entry.options[CONF_TOKEN] == MOCK_TOKEN
        assert config_entry.options[CONF_TIMEOUT] == DEFAULT_TIMEOUT
        assert config_entry.options[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL

        assert len(mock_async_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_options_flow_change_phone_with_register(hass: HomeAssistant) -> None:
    """Test options flow change phone with register.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE: 71110006655,
            CONF_LOGIN: "test",
            CONF_SMS_CODE: "001002",
            CONF_TOKEN: "0000000010101010101010101010101010101010101010",
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ) as mock_async_setup_entry, patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)
        mock_client.return_value.signin = AsyncMock(side_effect=IntercomNotFoundError)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "phone"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_PHONE: MOCK_PHONE,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_save["step_id"] == "register"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_LOGIN: MOCK_LOGIN,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_save["step_id"] == "confirm"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_SMS_CODE: MOCK_CODE,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_CREATE_ENTRY

        assert config_entry.options[CONF_PHONE] == MOCK_PHONE
        assert config_entry.options[CONF_LOGIN] == MOCK_LOGIN
        assert config_entry.options[CONF_SMS_CODE] == MOCK_CODE
        assert config_entry.options[CONF_TOKEN] == MOCK_TOKEN
        assert config_entry.options[CONF_TIMEOUT] == DEFAULT_TIMEOUT
        assert config_entry.options[CONF_SCAN_INTERVAL] == DEFAULT_SCAN_INTERVAL

        assert len(mock_async_setup_entry.mock_calls) == 1


@pytest.mark.asyncio
async def test_options_flow_change_phone_connection_error(hass: HomeAssistant) -> None:
    """Test options flow change phone connection error.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE: 71110006655,
            CONF_LOGIN: "test",
            CONF_SMS_CODE: "001002",
            CONF_TOKEN: "0000000010101010101010101010101010101010101010",
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ), patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)
        mock_client.return_value.signin = AsyncMock(side_effect=IntercomConnectionError)

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "phone"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_PHONE: MOCK_PHONE,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_save["step_id"] == "phone"
        assert result_save["errors"]["base"] == "connection.error"


@pytest.mark.asyncio
async def test_options_flow_change_phone_other_error(hass: HomeAssistant) -> None:
    """Test options flow change phone other error.

    :param hass: HomeAssistant
    """

    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={
            CONF_PHONE: 71110006655,
            CONF_LOGIN: "test",
            CONF_SMS_CODE: "001002",
            CONF_TOKEN: "0000000010101010101010101010101010101010101010",
        },
        options={},
    )
    config_entry.add_to_hass(hass)

    await setup.async_setup_component(hass, "http", {})

    with patch(
        "custom_components.tattelecom_intercom.async_setup_entry",
        return_value=True,
    ), patch(
        "custom_components.tattelecom_intercom.config_flow.IntercomClient"
    ) as mock_client:
        await async_mock_client(mock_client)
        mock_client.return_value.signin = AsyncMock(
            side_effect=IntercomUnauthorizedError("error")
        )

        await hass.config_entries.async_setup(config_entry.entry_id)
        await hass.async_block_till_done()

        result_init = await hass.config_entries.options.async_init(
            config_entry.entry_id
        )

        assert result_init["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_init["step_id"] == "phone"

        result_save = await hass.config_entries.options.async_configure(
            result_init["flow_id"],
            user_input={
                CONF_PHONE: MOCK_PHONE,
                CONF_TIMEOUT: DEFAULT_TIMEOUT,
                CONF_SCAN_INTERVAL: DEFAULT_SCAN_INTERVAL,
            },
        )
        await hass.async_block_till_done()

        assert result_save["type"] == data_entry_flow.RESULT_TYPE_FORM
        assert result_save["step_id"] == "phone"
        assert result_save["errors"]["base"] == "error"
