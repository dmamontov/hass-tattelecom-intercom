"""Configuration flows."""

from __future__ import annotations

import logging

import voluptuous as vol
from homeassistant import config_entries
from homeassistant.const import CONF_SCAN_INTERVAL, CONF_TIMEOUT, CONF_TOKEN
from homeassistant.core import callback
from homeassistant.data_entry_flow import FlowHandler, FlowResult
from homeassistant.helpers.httpx_client import get_async_client
from homeassistant.helpers.typing import ConfigType

from .client import IntercomClient
from .const import (
    CONF_LOGIN,
    CONF_PHONE,
    CONF_SMS_CODE,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_TIMEOUT,
    DOMAIN,
    MIN_SCAN_INTERVAL,
    OPTION_IS_FROM_FLOW,
    PHONE_MAX,
    PHONE_MIN,
    SMS_CODE_LENGTH,
)
from .exceptions import (
    IntercomConnectionError,
    IntercomError,
    IntercomNotFoundError,
    IntercomUnauthorizedError,
)
from .helper import get_config_value

_LOGGER = logging.getLogger(__name__)


class IntercomFlow(FlowHandler):
    """Default flow"""

    _config_entry: config_entries.ConfigEntry | None = None

    _client: IntercomClient | None = None
    _entry_data: ConfigType | None = None

    async def async_step_phone(
        self, user_input: ConfigType, errors: dict | None = None
    ) -> FlowResult:
        """Handle a flow phone number.

        :param user_input: ConfigType: User data
        :param errors: dict | None: Errors list
        :return FlowResult: Result object
        """

        if user_input.get(CONF_PHONE):
            self._entry_data = user_input

            self._client = IntercomClient(
                get_async_client(self.hass, False), int(user_input[CONF_PHONE])
            )

            try:
                await self._client.signin()
            except IntercomNotFoundError:
                return await self.async_step_register(user_input)
            except IntercomConnectionError:
                errors = {"base": "connection.error"}
            except IntercomError as err:
                errors = {"base": str(err)}
            else:
                return await self.async_step_confirm(user_input)

        return self.async_show_form(
            step_id="phone",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PHONE,
                        default=user_input.get(
                            CONF_PHONE,
                            get_config_value(
                                self._config_entry, CONF_PHONE, vol.UNDEFINED
                            ),
                        ),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=PHONE_MIN, max=PHONE_MAX)
                    ),
                }
            ),
            errors=errors,
        )

    async def async_step_register(
        self, user_input: ConfigType, errors: dict | None = None
    ) -> FlowResult:
        """Handle a flow register.

        :param user_input: ConfigType: User data
        :param errors: dict | None: Errors list
        :return FlowResult: Result object
        """

        if user_input.get(CONF_LOGIN):
            self._entry_data |= user_input

            try:
                await self._client.register(user_input.get(CONF_LOGIN))  # type: ignore
            except IntercomUnauthorizedError:
                return await self.async_step_phone({}, {"base": "unauthorized.error"})
            except IntercomConnectionError:
                errors = {"base": "connection.error"}
            except IntercomError as err:
                errors = {"base": str(err)}
            else:
                return await self.async_step_confirm(user_input)

        return self.async_show_form(
            step_id="register",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_LOGIN,
                        default=user_input.get(
                            CONF_LOGIN,
                            get_config_value(
                                self._config_entry, CONF_LOGIN, vol.UNDEFINED
                            ),
                        ),
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_confirm(
        self, user_input: ConfigType, errors: dict | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the signin or register.

        :param user_input: ConfigType: User data
        :param errors: dict | None: Errors list
        :return FlowResult: Result object
        """

        if user_input.get(CONF_SMS_CODE):
            self._entry_data |= user_input

            try:
                result: dict = await self._client.sms_confirm(  # type: ignore
                    user_input.get(CONF_SMS_CODE)
                )

                await self._client.update_push_token(result["access_token"])  # type: ignore
            except IntercomUnauthorizedError:
                return await self.async_step_phone({}, {"base": "unauthorized.error"})
            except IntercomConnectionError:
                errors = {"base": "connection.error"}
            except IntercomError as err:
                errors = {"base": str(err)}
            else:
                return await self.async_finish(
                    self._entry_data | {CONF_TOKEN: result["access_token"]},
                    {OPTION_IS_FROM_FLOW: True},
                )

        return self.async_show_form(
            step_id="confirm",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_SMS_CODE,
                        default=user_input.get(
                            CONF_SMS_CODE,
                            get_config_value(
                                self._config_entry, CONF_SMS_CODE, vol.UNDEFINED
                            ),
                        ),
                    ): vol.All(
                        vol.Coerce(str),
                        vol.Length(min=SMS_CODE_LENGTH, max=SMS_CODE_LENGTH),
                    ),
                }
            ),
            errors=errors,
        )

    async def async_finish(
        self, data: ConfigType, options: ConfigType | None = None
    ) -> FlowResult:  # pragma: no cover
        """Finish flow.

        :param data: ConfigType | None : User data
        :param options: ConfigType | None : Options data
        :return FlowResult: Result object
        """

        raise NotImplementedError()


class IntercomConfigFlow(IntercomFlow, config_entries.ConfigFlow, domain=DOMAIN):  # type: ignore
    """First time set up flow."""

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> IntercomOptionsFlow:
        """Get the options flow for this handler.

        :param config_entry: config_entries.ConfigEntry: Config Entry object
        :return IntercomOptionsFlow: Options Flow object
        """

        return IntercomOptionsFlow(config_entry)

    async def async_step_user(
        self, user_input: ConfigType | None = None, errors: dict | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user.

        :param user_input: ConfigType: User data
        :param errors: dict: Errors list
        :return FlowResult: Result object
        """

        if self._async_current_entries():  # pragma: no cover
            return self.async_abort(reason="single_instance_allowed")

        return await self.async_step_phone(user_input or {})

    async def async_step_reauth(
        self, user_input: ConfigType | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the reauth.

        :param user_input: ConfigType: User data
        :return FlowResult: Result object
        """

        return await self.async_step_phone(user_input or {})

    async def async_finish(
        self, data: ConfigType, options: ConfigType | None = None
    ) -> FlowResult:
        """Finish flow.

        :param data: ConfigType: User data
        :param options: ConfigType | None: Options data
        :return FlowResult: Result object
        """

        unique_id: str = str(data.get(CONF_PHONE))

        await self.async_set_unique_id(unique_id)
        self._abort_if_unique_id_configured()

        # pylint: disable=unexpected-keyword-arg
        return self.async_create_entry(
            title=unique_id,
            data=data,
            options=options,
        )


class IntercomOptionsFlow(IntercomFlow, config_entries.OptionsFlow):
    """Changing options flow."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow.

        :param config_entry: config_entries.ConfigEntry: Config Entry object
        """

        self._config_entry = config_entry

    async def async_step_init(
        self, user_input: ConfigType | None = None, errors: dict | None = None
    ) -> FlowResult:
        """Handle a flow initialized by the user.

        :param user_input: ConfigType: User data
        :param errors: dict: Errors list
        :return FlowResult: Result object
        """

        self._entry_data = dict(self._config_entry.data)  # type: ignore

        return await self.async_step_phone(user_input or {})

    async def async_step_phone(
        self, user_input: ConfigType, errors: dict | None = None
    ) -> FlowResult:
        """Manage the options.

        :param user_input: ConfigType: User data
        :param errors: dict | None: Errors list
        :return FlowResult: Result object
        """

        if len(user_input) > 0 and not errors:
            _is_change_phone: bool = get_config_value(
                self._config_entry, CONF_PHONE
            ) != user_input.get(CONF_PHONE)

            if _is_change_phone:
                self._entry_data = user_input
            else:
                self._entry_data |= user_input

            self._client = IntercomClient(
                get_async_client(self.hass, False),
                int(user_input[CONF_PHONE]),
                None
                if _is_change_phone
                else get_config_value(self._config_entry, CONF_TOKEN),
            )

            try:
                await (
                    self._client.signin()
                    if _is_change_phone
                    else self._client.sip_settings()
                )
            except IntercomNotFoundError:
                return await self.async_step_register(user_input)
            except IntercomConnectionError:
                errors = {"base": "connection.error"}
            except IntercomError as err:
                errors = {"base": str(err)}
            else:
                return await (
                    self.async_step_confirm(user_input)
                    if _is_change_phone
                    else self.async_finish(self._entry_data)
                )

        return self.async_show_form(
            step_id="phone",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_PHONE,
                        default=user_input.get(
                            CONF_PHONE,
                            get_config_value(
                                self._config_entry, CONF_PHONE, vol.UNDEFINED
                            ),
                        ),
                    ): vol.All(
                        vol.Coerce(int), vol.Range(min=PHONE_MIN, max=PHONE_MAX)
                    ),
                    vol.Required(
                        CONF_SCAN_INTERVAL,
                        default=user_input.get(
                            CONF_SCAN_INTERVAL,
                            get_config_value(
                                self._config_entry,
                                CONF_SCAN_INTERVAL,
                                DEFAULT_SCAN_INTERVAL,
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=MIN_SCAN_INTERVAL)),
                    vol.Required(
                        CONF_TIMEOUT,
                        default=user_input.get(
                            CONF_TIMEOUT,
                            get_config_value(
                                self._config_entry, CONF_TIMEOUT, DEFAULT_TIMEOUT
                            ),
                        ),
                    ): vol.All(vol.Coerce(int), vol.Range(min=DEFAULT_TIMEOUT)),
                }
            ),
            errors=errors,
        )

    async def async_finish(
        self, data: ConfigType, options: ConfigType | None = None
    ) -> FlowResult:
        """Finish flow.

        :param data: ConfigType | None : User data
        :param options: ConfigType | None : Options data
        :return FlowResult: Result object
        """

        unique_id: str = str(data.get(CONF_PHONE))

        await self.async_update_unique_id(unique_id)

        return self.async_create_entry(
            title=unique_id,
            data=data,
        )

    async def async_update_unique_id(self, unique_id: str) -> None:  # pragma: no cover
        """Async update unique_id

        :param unique_id:
        """

        if self._config_entry.unique_id == unique_id:  # type: ignore
            return

        for flow in self.hass.config_entries.flow.async_progress(True):
            if (
                flow["flow_id"] != self.flow_id
                and flow["context"].get("unique_id") == unique_id
            ):
                self.hass.config_entries.flow.async_abort(flow["flow_id"])

        self.hass.config_entries.async_update_entry(
            self._config_entry, unique_id=unique_id
        )
