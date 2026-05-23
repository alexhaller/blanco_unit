# CLAUDE.md — Blanco Unit

## Project overview

Home Assistant custom integration for Blanco water dispensers communicating over BLE (Bluetooth Low Energy, characteristic UUID `3b531d4d-ed58-4677-b2fa-1c72a86082cf`). Do not switch the transport — the protocol is BLE-only.

- GitHub: https://github.com/Nailik/blanco_unit

Key files:
- `custom_components/blanco_unit/client.py` — `BlancoUnitBluetoothClient`; BLE request/response flow uses notifications, not read
- `custom_components/blanco_unit/coordinator.py` — `BlancoUnitCoordinator`; poll interval: 1 minute
- `custom_components/blanco_unit/config_flow.py` — required user inputs: MAC address, device name, PIN
- `custom_components/blanco_unit/const.py` — `DOMAIN = "blanco_unit"`
- Platforms: `sensor.py`, `binary_sensor.py`, `number.py`, `select.py`, `button.py`

## Project-specific notes

- **Domain**: `blanco_unit`; pip-audit packages: `bleak>=0.21.1`
- **Random MAC support**: devices with randomized MAC are tracked by service UUID instead of address — `RANDOM_MAC_PLACEHOLDER` sentinel in config entry data signals this path
- **`.releaserc.json`** `prepareCmd` path: `custom_components/blanco_unit/manifest.json`
