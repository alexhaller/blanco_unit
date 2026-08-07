## [1.2.6](https://github.com/alexhaller/blanco_unit/compare/v1.2.5...v1.2.6) (2026-08-07)

## [1.2.5](https://github.com/alexhaller/blanco_unit/compare/v1.2.4...v1.2.5) (2026-08-06)

## [1.2.4](https://github.com/alexhaller/blanco_unit/compare/v1.2.3...v1.2.4) (2026-05-24)

### Bug Fixes

* ensure GATT service discovery completes before characteristic reads ([a614e76](https://github.com/alexhaller/blanco_unit/commit/a614e76c41de35f9531144429b436e7812dd06ea))

## [1.2.3](https://github.com/alexhaller/blanco_unit/compare/v1.2.2...v1.2.3) (2026-05-24)

### Bug Fixes

* explicitly trigger BlueZ ATT MTU negotiation ([2b0e4da](https://github.com/alexhaller/blanco_unit/commit/2b0e4dac987b6150be09314f91f2ce1cd8225733))

## [1.2.2](https://github.com/alexhaller/blanco_unit/compare/v1.2.1...v1.2.2) (2026-05-24)

### Bug Fixes

* map BleakNotFoundError and other bleak errors to clearer messages ([25c1ea6](https://github.com/alexhaller/blanco_unit/commit/25c1ea6cf80ea69889caf0b8f3016d07e91c609c))

## [1.2.1](https://github.com/alexhaller/blanco_unit/compare/v1.2.0...v1.2.1) (2026-05-24)

### Bug Fixes

* size protocol chunks to negotiated ATT MTU ([7839da4](https://github.com/alexhaller/blanco_unit/commit/7839da45b87d46154c6cb6c504da0f0a3d10f81d))

## [1.2.0](https://github.com/alexhaller/blanco_unit/compare/v1.1.3...v1.2.0) (2026-05-23)

### Features

* harden BLE error handling with detailed diagnostics ([03df58b](https://github.com/alexhaller/blanco_unit/commit/03df58b20a608afcab4217dcb224000d4190a97d))

## [1.1.3](https://github.com/alexhaller/blanco_unit/compare/v1.1.2...v1.1.3) (2026-05-23)

### Bug Fixes

* add delays in read_gatt_char polling loop ([4b65cfb](https://github.com/alexhaller/blanco_unit/commit/4b65cfb85376abab14dda35dca387b43922e2a76))

## [1.1.2](https://github.com/alexhaller/blanco_unit/compare/v1.1.1...v1.1.2) (2026-05-23)

### Bug Fixes

* revert to read_gatt_char polling — characteristic does not support NOTIFY ([b72af28](https://github.com/alexhaller/blanco_unit/commit/b72af28199499cdebde24d39075149f7a265ad7e))

## [1.1.1](https://github.com/alexhaller/blanco_unit/compare/v1.1.0...v1.1.1) (2026-05-23)

### Bug Fixes

* remove pair=True from BLE establish_connection ([010f101](https://github.com/alexhaller/blanco_unit/commit/010f1016bb289a636717290068d33d354cfc6ea3))

## [1.1.0](https://github.com/alexhaller/blanco_unit/compare/v1.0.0...v1.1.0) (2026-05-23)

### Features

* add brand icon for HACS validation ([1c4e708](https://github.com/alexhaller/blanco_unit/commit/1c4e7083f041160aa1fd34cce71887ccdb897e22))

## 1.0.0 (2026-05-23)

### Features

* Add full CHOICE.All device support ([0fd4f2d](https://github.com/alexhaller/blanco_unit/commit/0fd4f2d76ecfb5763d17119d7116e688448f9e3e)), closes [#6](https://github.com/alexhaller/blanco_unit/issues/6)
* Add heater/compressor binary sensors from status bitmask ([a9011b6](https://github.com/alexhaller/blanco_unit/commit/a9011b6ab4ebc2af30439c205cfa63358f76d224))

### Bug Fixes

* add CONFIG_SCHEMA and remove deleted UP038 ruff rule ([6849329](https://github.com/alexhaller/blanco_unit/commit/68493298c21a6b5b0daee20be1bab0a5ed9c5ac8))
* add pair=True to BLE establish_connection calls ([a48b26f](https://github.com/alexhaller/blanco_unit/commit/a48b26fe458edf7ce69b6b2b5ae8daa870ccb6c6))
* Rename cooling_temp to Compressor Temperature ([5f7762d](https://github.com/alexhaller/blanco_unit/commit/5f7762db6539a33ce1476b8e1dba0d79cd015d9b))
* use BLE notifications for response flow ([f252e35](https://github.com/alexhaller/blanco_unit/commit/f252e3574fd43d2933670a16330c262290e3d8e1))
