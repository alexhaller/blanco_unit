"""Config flow and options flow for Blanco Unit BLE integration."""

from __future__ import annotations

import logging
import re
from dataclasses import dataclass
from typing import Any

import probatio
from bleak.backends.device import BLEDevice
from bleak.exc import BleakError
from bleak_retry_connector import (
    BleakConnectionError,
    BleakNotFoundError,
    BleakOutOfConnectionSlotsError,
)
from homeassistant.components import bluetooth
from homeassistant.components.bluetooth import BluetoothServiceInfoBleak
from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult
from homeassistant.helpers.selector import (
    SelectOptionDict,
    SelectSelector,
    SelectSelectorConfig,
    SelectSelectorMode,
    TextSelector,
    TextSelectorConfig,
    TextSelectorType,
)
from homeassistant.loader import IntegrationNotFound, async_get_integration
from probatio import UNDEFINED

from .client import (
    BlancoUnitAuthenticationError,
    BlancoUnitConnectionError,
    BlancoUnitGattTimeoutError,
    establish_validated_connection,
    validate_pin,
)
from .const import (
    CONF_DEV_ID,
    CONF_ERROR,
    CONF_LEGACY_ENTRY_ID,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
    LEGACY_DOMAIN,
    RANDOM_MAC_PLACEHOLDER,
)

_LOGGER = logging.getLogger(__name__)


def _loggable(data: dict[str, Any] | None) -> dict[str, Any] | None:
    """Return the flow data with the PIN redacted."""
    if data is None or CONF_PIN not in data:
        return data
    return {**data, CONF_PIN: "**REDACTED**"}


@dataclass
class ValidationResult:
    """Result of the validation, errors is empty if successful."""

    errors: dict[str, str]
    dev_id: str | None = None
    mac_address: str | None = None
    description_placeholders: dict[str, Any] | None = None


class BlancoUnitConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle the config flow for Blanco Unit Integration."""

    VERSION = 1

    _discovery_info: BluetoothServiceInfoBleak | None = None
    _legacy_entry: ConfigEntry | None = None

    def prefilledForm(
        self,
        data: dict[str, Any] | None = None,
        mac_editable: bool = True,
        name_editable: bool = True,
    ) -> probatio.Schema:
        """Return a form schema with prefilled values from data."""
        _LOGGER.debug(
            "Load prefilled form with: %s and info %s",
            _loggable(data),
            self._discovery_info,
        )
        # Setup Values
        mac: Any = UNDEFINED
        name: Any = UNDEFINED
        pin: Any = UNDEFINED

        # Read values from data if provided
        if data is not None:
            mac = data.get(CONF_MAC, UNDEFINED)
            name = data.get(CONF_NAME, f"Blanco Unit ({mac})")
            pin = data.get(CONF_PIN, UNDEFINED)

        # If discovery_info is set, use its address as the MAC and for the name if not provided
        if self._discovery_info is not None:
            _LOGGER.debug("Set mac not editable")
            mac_editable = False
            mac = self._discovery_info.address
            name = self._discovery_info.name

        # Provide Schema
        return probatio.Schema(
            {
                probatio.Required(CONF_MAC, default=mac): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=False,
                        read_only=not mac_editable,
                    )
                ),
                probatio.Required(CONF_NAME, default=name): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=False,
                        read_only=not name_editable,
                    )
                ),
                probatio.Required(CONF_PIN, default=pin): TextSelector(
                    TextSelectorConfig(
                        type=TextSelectorType.TEXT,
                        multiline=False,
                        read_only=False,
                    )
                ),
            },
        )

    async def validate_input(self, user_input: dict[str, Any]) -> ValidationResult:
        """Set up the entry from user data."""
        _LOGGER.debug("validate_input %s", _loggable(user_input))

        # Validate MAC address format
        if not bool(
            re.match(
                r"^([0-9A-Fa-f]{2}([-:])){5}([0-9A-Fa-f]{2})$", user_input[CONF_MAC]
            )
        ):
            _LOGGER.error("Invalid MAC code: %s", user_input[CONF_MAC])
            return ValidationResult({CONF_ERROR: "invalid_mac_code"})

        # Validate PIN format (5 digits)
        pin_str = str(user_input[CONF_PIN])
        if len(pin_str) != 5 or not pin_str.isdigit():
            _LOGGER.error("Invalid PIN: must be exactly 5 digits")
            return ValidationResult({CONF_ERROR: "invalid_pin_format"})

        client = None
        try:
            # Use device from discovery_info if available
            device: BLEDevice | None
            if self._discovery_info is not None:
                _LOGGER.debug("Using device from discovery_info")
                device = self._discovery_info.device
            else:
                _LOGGER.debug("await async_ble_device_from_address")
                device = bluetooth.async_ble_device_from_address(
                    hass=self.hass,
                    address=user_input[CONF_MAC],
                    connectable=True,
                )

            if device is None:
                return ValidationResult({CONF_ERROR: "error_device_not_found"})

            # Check if device has randomized MAC address
            # BLEDevice.address can be random if device uses BLE privacy
            address_type = getattr(device.details, "address_type", "").lower()
            has_random_mac = address_type in (
                "random",
                "random_static",
                "random_resolvable",
            )
            mac_to_store = RANDOM_MAC_PLACEHOLDER if has_random_mac else device.address

            _LOGGER.debug(
                "Device name %s, address_type %s, MAC: %s, Random: %s, Storing as: %s",
                device.name,
                address_type,
                device.address,
                has_random_mac,
                mac_to_store,
            )

            _LOGGER.debug("await establish_validated_connection")
            client, validation = await establish_validated_connection(
                device, lambda client: validate_pin(client, pin_str), timeout=120
            )
            _LOGGER.debug(
                "validate_pin returned %s, dev_id: %s, dev_type: %s",
                validation.is_valid,
                validation.dev_id,
                validation.dev_type,
            )

            if not validation.is_valid:
                return ValidationResult({CONF_ERROR: "error_invalid_authentication"})

            if validation.dev_id is None or validation.dev_type is None:
                return ValidationResult({CONF_ERROR: "error_device_not_found"})

            _LOGGER.debug(
                "Successfully tested connection to %s (dev_id: %s, dev_type: %s)",
                mac_to_store,
                validation.dev_id,
                validation.dev_type,
            )
            return ValidationResult(
                {}, dev_id=validation.dev_id, mac_address=mac_to_store
            )
        except ValueError as err:
            _LOGGER.error("Validation error: %s", err)
            return ValidationResult({CONF_ERROR: "invalid_pin_format"})
        except BlancoUnitAuthenticationError as err:
            _LOGGER.warning("Authentication failed during validation: %s", err)
            return ValidationResult({CONF_ERROR: "error_invalid_authentication"})
        except BleakOutOfConnectionSlotsError as err:
            _LOGGER.error("No free Bluetooth connection slot: %s", err)
            return ValidationResult({CONF_ERROR: "error_no_connection_slot"})
        except BlancoUnitGattTimeoutError as err:
            # still stuck after reconnecting once
            _LOGGER.error("Device did not respond: %s", err)
            return ValidationResult({CONF_ERROR: "error_device_not_responding"})
        except BleakNotFoundError as err:
            _LOGGER.error("Device not found / unreachable: %s", err)
            return ValidationResult(
                errors={CONF_ERROR: "error_device_unreachable"},
                description_placeholders={"error": str(err)},
            )
        except (
            BlancoUnitConnectionError,
            BleakConnectionError,
            BleakError,
            TimeoutError,
        ) as err:
            _LOGGER.error(
                "Communication error during validation: %s: %s",
                type(err).__name__,
                err,
            )
            return ValidationResult(
                errors={CONF_ERROR: "error_connection"},
                description_placeholders={"error": f"{type(err).__name__}: {err}"},
            )
        except Exception as err:
            _LOGGER.exception("Unexpected error during validation")
            return ValidationResult(
                errors={CONF_ERROR: "error_unknown"},
                description_placeholders={"error": f"{type(err).__name__}: {err}"},
            )
        finally:
            # Always disconnect the client
            if client is not None and client.is_connected:
                await client.disconnect()

    async def _async_legacy_candidates(self) -> list[ConfigEntry]:
        """Return the entries under the old domain that can be taken over.

        That domain is also the one of Nailik/blanco_unit, so its entries are
        offered as well. Nothing is offered while either is still installed: it
        would drive the same unit, and entities of a loaded integration cannot
        move.
        """
        try:
            await async_get_integration(self.hass, LEGACY_DOMAIN)
        except IntegrationNotFound:
            pass
        else:
            return []
        configured = {entry.unique_id for entry in self._async_current_entries()}
        return [
            legacy
            for legacy in self.hass.config_entries.async_entries(LEGACY_DOMAIN)
            if legacy.unique_id is not None and legacy.unique_id not in configured
        ]

    def _async_create_from_legacy(self, legacy: ConfigEntry) -> ConfigFlowResult:
        """Create the entry from an old one; its setup moves the old one over."""
        return self.async_create_entry(
            title=legacy.title,
            data={**legacy.data, CONF_LEGACY_ENTRY_ID: legacy.entry_id},
        )

    async def async_step_migrate(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Let the user pick the old entry to take over."""
        candidates = {
            legacy.entry_id: legacy for legacy in await self._async_legacy_candidates()
        }
        if user_input is not None:
            legacy = candidates.get(user_input[CONF_LEGACY_ENTRY_ID])
            if legacy is None:
                return self.async_abort(reason="no_legacy_entries")
            await self.async_set_unique_id(legacy.unique_id)
            self._abort_if_unique_id_configured()
            return self._async_create_from_legacy(legacy)
        if not candidates:
            return self.async_abort(reason="no_legacy_entries")
        return self.async_show_form(
            step_id="migrate",
            data_schema=probatio.Schema(
                {
                    probatio.Required(CONF_LEGACY_ENTRY_ID): SelectSelector(
                        SelectSelectorConfig(
                            options=[
                                SelectOptionDict(
                                    value=legacy.entry_id,
                                    label=f"{legacy.title} ({legacy.unique_id})",
                                )
                                for legacy in candidates.values()
                            ],
                            mode=SelectSelectorMode.LIST,
                        )
                    )
                }
            ),
        )

    async def async_step_migrate_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Ask before taking over the old entry of a discovered unit."""
        if (legacy := self._legacy_entry) is None:
            return self.async_abort(reason="no_legacy_entries")
        if user_input is not None:
            return self._async_create_from_legacy(legacy)
        self._set_confirm_only()
        return self.async_show_form(
            step_id="migrate_confirm",
            description_placeholders={
                "name": legacy.title,
                "mac": legacy.unique_id or "",
            },
        )

    async def async_step_choose(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Offer to take over an old entry or to set up a new unit."""
        return self.async_show_menu(
            step_id="choose", menu_options=["migrate", "manual"]
        )

    async def async_step_manual(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Set up a new unit although old entries could be taken over."""
        return self.async_show_form(step_id="user", data_schema=self.prefilledForm())

    async def async_step_bluetooth(
        self, discovery_info: BluetoothServiceInfoBleak
    ) -> ConfigFlowResult:
        """Handle a bluetooth device being discovered."""
        # Offer to take over the old entry of exactly this unit, if there is one
        address = discovery_info.address.upper()
        for legacy in await self._async_legacy_candidates():
            if legacy.unique_id is not None and legacy.unique_id.upper() == address:
                await self.async_set_unique_id(legacy.unique_id)
                self._abort_if_unique_id_configured()
                self._legacy_entry = legacy
                return await self.async_step_migrate_confirm()
        _LOGGER.debug(
            "async_step_bluetooth called with %s and advertisement %s",
            discovery_info,
            discovery_info.advertisement,
        )
        # Check if the device already exists.
        await self._async_handle_discovery_without_unique_id()
        self._abort_if_unique_id_configured()

        _LOGGER.debug("async_step_bluetooth %s", discovery_info)
        self._discovery_info = discovery_info

        return self.async_show_form(
            step_id="user",
            data_schema=self.prefilledForm(),
        )

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Create the entry with unique id if not already configured."""
        _LOGGER.debug("async_step_user %s", _loggable(user_input))
        if user_input is None and await self._async_legacy_candidates():
            return await self.async_step_choose()
        result = ValidationResult(errors={})
        if user_input is not None:
            result = await self.validate_input(user_input)
            if not result.errors:
                # Validation was successful, create a unique id and create the config entry.
                # Use MAC as unique_id for static MAC, dev_id for random MAC
                if result.mac_address == RANDOM_MAC_PLACEHOLDER:
                    await self.async_set_unique_id(result.dev_id)
                else:
                    await self.async_set_unique_id(result.mac_address)
                self._abort_if_unique_id_configured()

                # Store MAC address and dev_id in config
                config_data = user_input.copy()
                config_data[CONF_MAC] = result.mac_address
                config_data[CONF_DEV_ID] = result.dev_id

                _LOGGER.debug("Create entry with %s", _loggable(config_data))
                # Clean up discovery_info after successful validation
                self._discovery_info = None
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=config_data,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=self.prefilledForm(data=user_input),
            errors=result.errors,
            description_placeholders=result.description_placeholders,
        )

    async def async_step_reauth(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
        _LOGGER.debug("async_step_reauth %s", _loggable(user_input))
        result = ValidationResult(errors={})
        config_entry = self._get_reauth_entry()
        if user_input is not None:
            result = await self.validate_input(user_input)
            if not result.errors:
                # Verify this is the same device
                if result.mac_address == RANDOM_MAC_PLACEHOLDER:
                    await self.async_set_unique_id(result.dev_id)
                else:
                    await self.async_set_unique_id(result.mac_address)
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                # Update config with new PIN and potentially updated MAC
                data_updates = user_input.copy()
                data_updates[CONF_MAC] = result.mac_address
                data_updates[CONF_DEV_ID] = result.dev_id

                # Clean up discovery_info after successful validation
                self._discovery_info = None
                return self.async_update_reload_and_abort(
                    entry=self._get_reauth_entry(),
                    data_updates=data_updates,
                )
        return self.async_show_form(
            step_id="reauth",
            data_schema=self.prefilledForm(
                data=dict(config_entry.data),
                mac_editable=False,
                name_editable=False,
            ),
            errors=result.errors,
            description_placeholders=result.description_placeholders,
        )

    async def async_step_reconfigure(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle re-configuration."""
        _LOGGER.debug("async_step_reconfigure %s", _loggable(user_input))
        result = ValidationResult(errors={})
        config_entry = self._get_reconfigure_entry()
        if user_input is not None:
            result = await self.validate_input(user_input)
            if not result.errors:
                # Verify this is the same device
                if result.mac_address == RANDOM_MAC_PLACEHOLDER:
                    await self.async_set_unique_id(result.dev_id)
                else:
                    await self.async_set_unique_id(result.mac_address)
                self._abort_if_unique_id_mismatch(reason="wrong_device")

                # Update config with potentially updated MAC and dev_id
                data_updates = user_input.copy()
                data_updates[CONF_MAC] = result.mac_address
                data_updates[CONF_DEV_ID] = result.dev_id

                # Clean up discovery_info after successful validation
                self._discovery_info = None
                return self.async_update_reload_and_abort(
                    entry=self._get_reconfigure_entry(),
                    data_updates=data_updates,
                )
        return self.async_show_form(
            step_id="reconfigure",
            data_schema=self.prefilledForm(
                data=dict(config_entry.data),
                mac_editable=False,
            ),
            errors=result.errors,
            description_placeholders=result.description_placeholders,
        )
