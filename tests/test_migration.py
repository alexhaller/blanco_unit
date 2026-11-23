"""Migration of entries left under the pre-v3 domain blanco_unit."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import MockConfigEntry

from custom_components.blanco_unit_ha import _async_adopt_legacy_entry
from custom_components.blanco_unit_ha.const import (
    CONF_DEV_ID,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
    LEGACY_DOMAIN,
)

MAC = "AA:BB:CC:DD:EE:FF"
DATA = {CONF_MAC: MAC, CONF_NAME: "Kitchen", CONF_PIN: "01234", CONF_DEV_ID: "dev"}
ENTITY_ID = "sensor.kitchen_filter_capacity_remaining"


def _legacy_install(
    hass: HomeAssistant, unique_id: str | None = MAC
) -> MockConfigEntry:
    """Register an entry, device and entity the way v2 left them behind."""
    legacy = MockConfigEntry(
        domain=LEGACY_DOMAIN, title="Kitchen", unique_id=unique_id, data=DATA
    )
    legacy.add_to_hass(hass)
    device = dr.async_get(hass).async_get_or_create(
        config_entry_id=legacy.entry_id,
        identifiers={(LEGACY_DOMAIN, MAC)},
        name="Kitchen",
    )
    er.async_get(hass).async_get_or_create(
        "sensor",
        LEGACY_DOMAIN,
        "filter_remaining",
        config_entry=legacy,
        device_id=device.id,
        suggested_object_id="kitchen_filter_capacity_remaining",
    )
    return legacy


async def test_old_entry_is_imported(hass: HomeAssistant) -> None:
    """An entry of the old domain becomes an entry of the new one, as it was."""
    _legacy_install(hass)

    with patch("custom_components.blanco_unit_ha.async_setup_entry", return_value=True):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    (entry,) = hass.config_entries.async_entries(DOMAIN)
    assert entry.unique_id == MAC
    assert entry.title == "Kitchen"
    assert entry.data == DATA


async def test_device_and_entity_move_and_keep_their_entity_id(
    hass: HomeAssistant,
) -> None:
    legacy = _legacy_install(hass)
    entry = MockConfigEntry(domain=DOMAIN, title="Kitchen", unique_id=MAC, data=DATA)
    entry.add_to_hass(hass)

    await _async_adopt_legacy_entry(hass, entry)

    assert hass.config_entries.async_get_entry(legacy.entry_id) is None
    device = dr.async_get(hass).async_get_device_by_identifier(
        (DOMAIN, MAC), entry.entry_id
    )
    assert device is not None
    assert device.identifiers == {(DOMAIN, MAC)}
    entity = er.async_get(hass).async_get(ENTITY_ID)
    assert entity is not None
    assert entity.platform == DOMAIN
    assert entity.config_entry_id == entry.entry_id
    assert entity.device_id == device.id


async def test_unrelated_old_entry_is_left_alone(hass: HomeAssistant) -> None:
    legacy = _legacy_install(hass, unique_id="11:22:33:44:55:66")
    entry = MockConfigEntry(domain=DOMAIN, unique_id=MAC, data=DATA)
    entry.add_to_hass(hass)

    await _async_adopt_legacy_entry(hass, entry)

    assert hass.config_entries.async_get_entry(legacy.entry_id) is not None
    assert er.async_get(hass).async_get(ENTITY_ID).platform == LEGACY_DOMAIN


async def test_nothing_moves_while_the_old_folder_is_installed(
    hass: HomeAssistant, caplog: pytest.LogCaptureFixture
) -> None:
    """Both installed would drive the same unit; entities of a loaded one cannot move."""
    _legacy_install(hass)

    with patch(
        "custom_components.blanco_unit_ha.async_get_integration",
        return_value=MagicMock(),
    ):
        assert await async_setup_component(hass, DOMAIN, {})
        await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == []
    assert "Remove the old custom_components/blanco_unit folder" in caplog.text


async def test_adding_the_integration_takes_over_the_old_entry(
    hass: HomeAssistant,
) -> None:
    """Without an entry Home Assistant never loads the integration at startup.

    Adding it is what starts the migration, and needs no input.
    """
    legacy = _legacy_install(hass)

    with patch("custom_components.blanco_unit_ha.async_setup_entry", return_value=True):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen"
    assert result["data"] == DATA
    assert result["result"].unique_id == MAC
    # The old entry goes once the new one has been set up
    assert hass.config_entries.async_get_entry(legacy.entry_id) is not None


async def test_adding_shows_the_form_when_nothing_is_left_to_migrate(
    hass: HomeAssistant,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_adding_waits_while_the_old_folder_is_installed(
    hass: HomeAssistant,
) -> None:
    _legacy_install(hass)

    with patch(
        "custom_components.blanco_unit_ha.config_flow.async_get_integration",
        return_value=MagicMock(),
    ):
        result = await hass.config_entries.flow.async_init(
            DOMAIN, context={"source": SOURCE_USER}
        )

    assert result["type"] is FlowResultType.FORM
