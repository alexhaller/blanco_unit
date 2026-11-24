# CLAUDE.md — Blanco Unit

## Project overview

Home Assistant custom integration for Blanco water dispensers communicating over BLE (Bluetooth Low Energy, characteristic UUID `3b531d4d-ed58-4677-b2fa-1c72a86082cf`). Do not switch the transport — the protocol is BLE-only.

- GitHub: https://github.com/alexhaller/blanco_unit
- Project forked from: https://github.com/Nailik/blanco_unit

Key files:
- `custom_components/blanco_unit_ha/client.py` — `BlancoUnitBluetoothClient`; BLE request/response flow polls the characteristic with reads (it does not support notify)
- `custom_components/blanco_unit_ha/coordinator.py` — `BlancoUnitCoordinator`; poll interval: 1 minute
- `custom_components/blanco_unit_ha/config_flow.py` — required user inputs: MAC address, device name, PIN
- `custom_components/blanco_unit_ha/const.py` — `DOMAIN = "blanco_unit_ha"`
- Platforms: `sensor.py`, `binary_sensor.py`, `number.py`, `select.py`, `button.py`

## Project-specific notes

- **Domain**: `blanco_unit_ha` since v3 (`LEGACY_DOMAIN = "blanco_unit"` up to v2). It differs from `Nailik/blanco_unit`, which is in the HACS default catalog, so both can be installed; entries left under the old domain (including Nailik's) are only taken over after the user confirms it in the config flow (`migrate` step from the `choose` menu, or `migrate_confirm` on Bluetooth discovery of that unit's MAC); the new entry carries `CONF_LEGACY_ENTRY_ID` and `_async_adopt_legacy_entry` moves exactly that entry's devices and entities (entities first, then the device), then drops the key. Entity unique IDs are `<entry unique_id>_<key>` since v3.1 (`BlancoUnitBaseEntity.__init__`); `_async_migrate_unique_ids` rewrites older ones on setup. Keep the migration until no user can still be on v2; `requirements: []` — `bleak` and `bleak-retry-connector` are pinned by HA core and provided by the `bluetooth` dependency, so they are deliberately not listed
- **Random MAC support**: devices with randomized MAC are tracked by service UUID instead of address — `RANDOM_MAC_PLACEHOLDER` sentinel in config entry data signals this path
- **`.releaserc.json`** `prepareCmd` path: `custom_components/blanco_unit_ha/manifest.json`
