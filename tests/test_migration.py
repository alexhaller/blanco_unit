"""Taking over entries left under the pre-v3 domain blanco_unit."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from homeassistant.config_entries import SOURCE_BLUETOOTH, SOURCE_USER
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers import entity_registry as er
from homeassistant.setup import async_setup_component
from pytest_homeassistant.common import MockConfigEntry

from custom_components.blanco_unit_ha import (
    _async_adopt_legacy_entry,
    _async_migrate_unique_ids,
)
from custom_components.blanco_unit_ha.const import (
    CONF_DEV_ID,
    CONF_LEGACY_ENTRY_ID,
    CONF_MAC,
    CONF_NAME,
    CONF_PIN,
    DOMAIN,
    LEGACY_DOMAIN,
)

MAC = "AA:BB:CC:DD:EE:FF"
DATA = {CONF_MAC: MAC, CONF_NAME: "Kitchen", CONF_PIN: "01234", CONF_DEV_ID: "dev"}
ENTITY_ID = "sensor.kitchen_filter_capacity_remaining"
SETUP_ENTRY = "custom_components.blanco_unit_ha.async_setup_entry"


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


def _discovery(address: str = MAC) -> AsyncMock:
    discovery = AsyncMock()
    discovery.address = address
    discovery.name = "Kitchen"
    return discovery


# -------------------------------
# Setup of an entry created from an old one
# -------------------------------


async def test_device_and_entity_move_and_keep_their_entity_id(
    hass: HomeAssistant,
) -> None:
    legacy = _legacy_install(hass)
    entry = MockConfigEntry(
        domain=DOMAIN,
        title="Kitchen",
        unique_id=MAC,
        data={**DATA, CONF_LEGACY_ENTRY_ID: legacy.entry_id},
    )
    entry.add_to_hass(hass)

    await _async_adopt_legacy_entry(hass, entry)

    assert hass.config_entries.async_get_entry(legacy.entry_id) is None
    assert entry.data == DATA
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


async def test_an_entry_set_up_from_scratch_takes_nothing_over(
    hass: HomeAssistant,
) -> None:
    """Only an entry the user created from the old one moves it, not a match."""
    legacy = _legacy_install(hass)
    entry = MockConfigEntry(domain=DOMAIN, unique_id=MAC, data=DATA)
    entry.add_to_hass(hass)

    await _async_adopt_legacy_entry(hass, entry)

    assert hass.config_entries.async_get_entry(legacy.entry_id) is not None
    assert er.async_get(hass).async_get(ENTITY_ID).platform == LEGACY_DOMAIN


async def test_a_vanished_old_entry_only_drops_the_reference(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(
        domain=DOMAIN, unique_id=MAC, data={**DATA, CONF_LEGACY_ENTRY_ID: "gone"}
    )
    entry.add_to_hass(hass)

    await _async_adopt_legacy_entry(hass, entry)

    assert entry.data == DATA


async def test_startup_asks_to_remove_the_old_folder(
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


async def test_startup_takes_nothing_over_on_its_own(hass: HomeAssistant) -> None:
    legacy = _legacy_install(hass)

    assert await async_setup_component(hass, DOMAIN, {})
    await hass.async_block_till_done()

    assert hass.config_entries.async_entries(DOMAIN) == []
    assert hass.config_entries.async_get_entry(legacy.entry_id) is not None


# -------------------------------
# Unique IDs from before v3.1
# -------------------------------


async def test_unique_ids_get_the_unit_prefix_and_keep_their_entity_id(
    hass: HomeAssistant,
) -> None:
    entry = MockConfigEntry(domain=DOMAIN, unique_id=MAC, data=DATA)
    entry.add_to_hass(hass)
    registry = er.async_get(hass)
    registry.async_get_or_create(
        "sensor",
        DOMAIN,
        "filter_remaining",
        config_entry=entry,
        suggested_object_id="kitchen_filter_capacity_remaining",
    )

    await _async_migrate_unique_ids(hass, entry)
    await _async_migrate_unique_ids(hass, entry)

    entity = registry.async_get(ENTITY_ID)
    assert entity is not None
    assert entity.unique_id == f"{MAC}_filter_remaining"


# -------------------------------
# Adding the integration
# -------------------------------


async def test_adding_offers_to_take_over_an_old_entry(hass: HomeAssistant) -> None:
    _legacy_install(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.MENU
    assert result["step_id"] == "choose"
    assert result["menu_options"] == ["migrate", "manual"]


async def test_taking_over_the_chosen_entry(hass: HomeAssistant) -> None:
    legacy = _legacy_install(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "migrate"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "migrate"

    with patch(SETUP_ENTRY, return_value=True):
        result = await hass.config_entries.flow.async_configure(
            result["flow_id"], {CONF_LEGACY_ENTRY_ID: legacy.entry_id}
        )
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Kitchen"
    assert result["data"] == {**DATA, CONF_LEGACY_ENTRY_ID: legacy.entry_id}
    assert result["result"].unique_id == MAC


async def test_setting_up_a_new_unit_instead(hass: HomeAssistant) -> None:
    _legacy_install(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {"next_step_id": "manual"}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_adding_shows_the_form_when_nothing_is_left_to_migrate(
    hass: HomeAssistant,
) -> None:
    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_USER}
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"


async def test_adding_offers_nothing_while_the_old_folder_is_installed(
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
    assert result["step_id"] == "user"


# -------------------------------
# Bluetooth discovery
# -------------------------------


async def test_discovery_asks_before_taking_over_that_units_entry(
    hass: HomeAssistant,
) -> None:
    legacy = _legacy_install(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN, context={"source": SOURCE_BLUETOOTH}, data=_discovery()
    )
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "migrate_confirm"
    assert result["description_placeholders"] == {"name": "Kitchen", "mac": MAC}

    with patch(SETUP_ENTRY, return_value=True):
        result = await hass.config_entries.flow.async_configure(result["flow_id"], {})
        await hass.async_block_till_done()

    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["data"] == {**DATA, CONF_LEGACY_ENTRY_ID: legacy.entry_id}


async def test_discovery_of_another_unit_leaves_the_old_entry_alone(
    hass: HomeAssistant,
) -> None:
    _legacy_install(hass)

    result = await hass.config_entries.flow.async_init(
        DOMAIN,
        context={"source": SOURCE_BLUETOOTH},
        data=_discovery("11:22:33:44:55:66"),
    )

    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "user"
