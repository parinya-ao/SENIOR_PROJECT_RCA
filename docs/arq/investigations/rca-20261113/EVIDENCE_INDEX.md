# Evidence index

OBSERVED retained bytes; DERIVED integrity/comparison results. No original file was written.

## 20261113T121506Z-reverse-raw

Original: [evidence directory](../../../../artifacts/arq/20261113T121506Z-reverse-raw/). Machine result: [20261113T121506Z-reverse-raw.json](20261113T121506Z-reverse-raw.json).

Integrity **PASS**; completeness **PASS**; classification `PHYSICAL_RF_FAILURE_UNISOLATED`. Root cause UNKNOWN.

- sender: serial `42032240221023150129012600000000`, signature `1e970a`, fuses `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`; allowed written pages `[0,31232)`; independent image/protected-memory comparison PASS.
  Image SHA256 `04bd175cdad9b07a53a5dbacc0fe14859d817be8d217d97e36f97c7aa01eab0b`.
- receiver: serial `42032240221092150158013400000000`, signature `1e970a`, fuses `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`; allowed written pages `[0,30720)`; independent image/protected-memory comparison PASS.
  Image SHA256 `c7e30c1cebfacaee527fdc3171bd659c7e43c60a601050738858a2d09e527bca`.

Firmware build/config IDs: see machine report `identity_checks`. Source hashes, where captured, are checked against archived source files; missing original source is not reconstructed from newer code.

## 20261113T123620Z-reverse-raw

Original: [evidence directory](../../../../artifacts/arq/20261113T123620Z-reverse-raw/). Machine result: [20261113T123620Z-reverse-raw.json](20261113T123620Z-reverse-raw.json).

Integrity **PASS**; completeness **INCOMPLETE**; classification `HOST_TRANSPORT_ERROR`. Root cause UNKNOWN.

- sender: serial `42032240221023150129012600000000`, signature `1e970a`, fuses `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`; allowed written pages `[0,32256)`; independent image/protected-memory comparison PASS.
  Image SHA256 `990677a142eac631b829f61cafdba411e51f6d0b17eb2ec82c198ba51c694e03`.
- receiver: serial `42032240221092150158013400000000`, signature `1e970a`, fuses `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`; allowed written pages `[0,30720)`; independent image/protected-memory comparison PASS.
  Image SHA256 `067330164a03e7e021730e8a5336ef005af87cd5fe013ebe565b2c050b4d833e`.

Firmware build/config IDs: see machine report `identity_checks`. Source hashes, where captured, are checked against archived source files; missing original source is not reconstructed from newer code.

## 20261113T123837Z-standby

Original: [evidence directory](../../../../artifacts/arq/20261113T123837Z-standby/). Machine result: [20261113T123837Z-standby.json](20261113T123837Z-standby.json).

Integrity **PASS**; completeness **NOT_APPLICABLE_TO_RF**; classification `STANDBY_RESTORE_OBSERVED`. Root cause UNKNOWN.

- sender: serial `42032240221023150129012600000000`, signature `1e970a`, fuses `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`; allowed written pages `[0,37376)`; independent image/protected-memory comparison PASS.
  Image SHA256 `23b76a9468dcb8fc24473d9827693e5cc68f6f3fac2e219234c669f7e2314a1a`.
- receiver: serial `42032240221092150158013400000000`, signature `1e970a`, fuses `0000f0ffffd2f80000ffffffffffffff`, lock `5cc5c55c`; allowed written pages `[0,36352)`; independent image/protected-memory comparison PASS.
  Image SHA256 `753cb22fa9bbf8761d1ed1dd0ec8da9b46bfb77e20f3d21fc5c41ceced2c88a3`.

Firmware build/config IDs: see machine report `identity_checks`. Source hashes, where captured, are checked against archived source files; missing original source is not reconstructed from newer code.

These application page ranges are the regions permitted to change, **not protected regions**. Protected Flash is outside those ranges; EEPROM/fuses/lock/identity are compared independently. A valid manifest cannot authenticate the capture hardware. Extra files unlisted in the original manifest are not silently treated as authenticated.
