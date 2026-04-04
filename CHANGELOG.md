# CHANGELOG


## [0.7.0](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.6.0...v0.7.0) (2026-04-04)


### Features

* support Renogy battery devices ([#121](https://github.com/IAmTheMitchell/renogy-ha/issues/121)) ([59ce938](https://github.com/IAmTheMitchell/renogy-ha/commit/59ce9384bb280ec46ba2b988148c494e87b5d358))


### Bug Fixes

* add raw_words to sustained shunt updates ([#123](https://github.com/IAmTheMitchell/renogy-ha/issues/123)) ([dd46ea7](https://github.com/IAmTheMitchell/renogy-ha/commit/dd46ea75eaf791a891faf9252b817a66e3ed25cd))
* restore Smart Shunt energy totals across Home Assistant restarts ([#124](https://github.com/IAmTheMitchell/renogy-ha/issues/124)) ([27ddbcc](https://github.com/IAmTheMitchell/renogy-ha/commit/27ddbccc7c99e113a80beeabc23ec14c4f13622f))

## [0.6.0](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.5.0...v0.6.0) (2026-03-26)


### ⚠ BREAKING CHANGES

* require Home Assistant 2026.3 and Python 3.14.2 ([#84](https://github.com/IAmTheMitchell/renogy-ha/issues/84))

### Features

* add optional non-shunt transport mode ([#106](https://github.com/IAmTheMitchell/renogy-ha/issues/106)) ([f3d9833](https://github.com/IAmTheMitchell/renogy-ha/commit/f3d98333c90dad0fdaa5f76626a4bc8fb2d53c39))
* add SHUNT300 troubleshooting attributes ([#98](https://github.com/IAmTheMitchell/renogy-ha/issues/98)) ([b7007bc](https://github.com/IAmTheMitchell/renogy-ha/commit/b7007bc4cecae4bf8886d9913480dd07a3afa523))
* add Smart Shunt connection modes ([#104](https://github.com/IAmTheMitchell/renogy-ha/issues/104)) ([76ad219](https://github.com/IAmTheMitchell/renogy-ha/commit/76ad219b3ac3717800c818f403cb9ec440eea9c7))
* require Home Assistant 2026.3 and Python 3.14.2 ([#84](https://github.com/IAmTheMitchell/renogy-ha/issues/84)) ([8dd7e98](https://github.com/IAmTheMitchell/renogy-ha/commit/8dd7e9857d785b9b0a7e7a6cd9d46a6e6c55f090))


### Bug Fixes

* bump renogy-ble to 2.2.2 ([b323b50](https://github.com/IAmTheMitchell/renogy-ha/commit/b323b50c17c08729048ac87f0ebdfa76e854dcba))
* harden smart shunt live packet parsing ([#100](https://github.com/IAmTheMitchell/renogy-ha/issues/100)) ([be765b8](https://github.com/IAmTheMitchell/renogy-ha/commit/be765b88ee46ffd5fe9df87b03da55baba04efba))
* harden sustained shunt reconnect recovery ([#112](https://github.com/IAmTheMitchell/renogy-ha/issues/112)) ([e8e3ab4](https://github.com/IAmTheMitchell/renogy-ha/commit/e8e3ab42821cd16be34b83ee389ebe7a3397e28f))
* remove blocking startup waits ([#101](https://github.com/IAmTheMitchell/renogy-ha/issues/101)) ([3be4ed1](https://github.com/IAmTheMitchell/renogy-ha/commit/3be4ed1a6fedcc6e24c3b476ae02078f26f23203))
* use github token for beta release workflow ([#86](https://github.com/IAmTheMitchell/renogy-ha/issues/86)) ([d8a3764](https://github.com/IAmTheMitchell/renogy-ha/commit/d8a3764d19608d25b4533bc082b976be16fd325f))


### Documentation

* explain connection modes introduced in 0.6.0 ([#115](https://github.com/IAmTheMitchell/renogy-ha/issues/115)) ([63b65a5](https://github.com/IAmTheMitchell/renogy-ha/commit/63b65a5ccc30a582293c99d5c823d28efb2dedc0))
* update readme to reflect that renogy-ha is now a default HACS repository ([#99](https://github.com/IAmTheMitchell/renogy-ha/issues/99)) ([91fc00e](https://github.com/IAmTheMitchell/renogy-ha/commit/91fc00eaac06eae8dfe8e16343d71fd554385da4))

## [0.5.0](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.4.1...v0.5.0) (2026-03-11)


### Features

* add support for Renogy Smart Shunt 300 ([#77](https://github.com/IAmTheMitchell/renogy-ha/issues/77)) ([123013a](https://github.com/IAmTheMitchell/renogy-ha/commit/123013ae5fdfe43e50a69c24686a413520e2331c))


### Documentation

* add contributing guidelines for the project ([#71](https://github.com/IAmTheMitchell/renogy-ha/issues/71)) ([4854c38](https://github.com/IAmTheMitchell/renogy-ha/commit/4854c38f5179004fde23677ba71c913bf2eaa691))

## [0.4.1](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.4.0...v0.4.1) (2026-02-11)


### Bug Fixes

* ensure proper client disconnection ([fe244ea](https://github.com/IAmTheMitchell/renogy-ha/commit/fe244eab80b1767146e960196c22ac76752ae989))
* update renogy-ble dependency version to 1.2.1a12 ([3f504b7](https://github.com/IAmTheMitchell/renogy-ha/commit/3f504b71722f6b4a55e8b944169ac0d05e4927f1))
* update renogy-ble dependency version to 1.2.1a13 ([e88c19b](https://github.com/IAmTheMitchell/renogy-ha/commit/e88c19be0908d3398b5e351999b47790f1eb364f))

## [0.4.0](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.3.0...v0.4.0) (2026-02-02)


### Features

* turn controller load on/off ([#57](https://github.com/IAmTheMitchell/renogy-ha/issues/57)) ([70e0a6c](https://github.com/IAmTheMitchell/renogy-ha/commit/70e0a6c891f7b63240b7d9b242806d7a3f02a5ef))

## [0.3.0](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.2.12...v0.3.0) (2026-01-18)


### Features

* add DC-DC charger (DCC) support with writable parameters ([#52](https://github.com/IAmTheMitchell/renogy-ha/issues/52)) ([946cf9c](https://github.com/IAmTheMitchell/renogy-ha/commit/946cf9c2fe7bebfe4a5375cbaf4afcbe2752ff8c))

## [0.3.0](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.2.12...v0.3.0) (2026-01-11)


### Features

* add DC-DC charger (DCC) support with writable parameters ([#12](https://github.com/IAmTheMitchell/renogy-ha/issues/12), [#20](https://github.com/IAmTheMitchell/renogy-ha/issues/20))
  - New DCC device type for DC-DC chargers (DCC30S, DCC50S, RBC20D1U, etc.)
  - DCC-specific sensors: alternator voltage/current/power, solar voltage/current/power, charging status, charging mode, ignition status, daily and lifetime statistics
  - Number entities for writable parameters: voltage thresholds (overvoltage, charging limit, equalization, boost, float, etc.), time settings (boost time, equalization time/interval), current limits
  - Select entity for battery type selection (Custom, Open, Sealed, Gel, Lithium)
  - Clear sensor naming to distinguish alternator vs solar inputs

### Dependencies

* use forked renogy-ble with DCC register map and write support


## [0.2.12](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.2.11...v0.2.12) (2026-01-11)


### Bug Fixes

* fix incorrect sensor values when temperatures below 0 degrees ([#48](https://github.com/IAmTheMitchell/renogy-ha/issues/48)) ([e2e308f](https://github.com/IAmTheMitchell/renogy-ha/commit/e2e308f2fa5e5cd8544337b2c976b8dc97c75954))

## [0.2.11](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.2.10...v0.2.11) (2026-01-08)


### Bug Fixes

* support bleak 2.0.0+ and Home Assistant Core 2026.1.0 ([#46](https://github.com/IAmTheMitchell/renogy-ha/issues/46)) ([8996d5c](https://github.com/IAmTheMitchell/renogy-ha/commit/8996d5c2bb1ac306fbe5310900ee18ffc0254f64))

## [0.2.10](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.2.9...v0.2.10) (2026-01-01)


### Bug Fixes

* manually bump version ([97130bb](https://github.com/IAmTheMitchell/renogy-ha/commit/97130bb2371a8294744355442c8d289d70a445fc))
* support signed integers for temperature values ([#25](https://github.com/IAmTheMitchell/renogy-ha/issues/25)) ([bbf7ad0](https://github.com/IAmTheMitchell/renogy-ha/commit/bbf7ad010deff632c06cf1133ea073958f9f5dd5))


### Documentation

* add AGENTS.md ([4bf216a](https://github.com/IAmTheMitchell/renogy-ha/commit/4bf216a5625d7fbe5709f5975bc22cab7e444bb0))
* add documentation on how to update to a test version ([e9da900](https://github.com/IAmTheMitchell/renogy-ha/commit/e9da90068530ec6e1e707041cf9a49aa4ba27746))
* add hardware section to README ([c3d4556](https://github.com/IAmTheMitchell/renogy-ha/commit/c3d4556e90dc007910bdec44e0396e220620bc2e))
* add workflow badges ([34b22c7](https://github.com/IAmTheMitchell/renogy-ha/commit/34b22c742d2989ec4a6f5879e2f92c250b1b7844))
* fix test_branch image reference ([81280de](https://github.com/IAmTheMitchell/renogy-ha/commit/81280def0553641bfe503fb54f6ac3934eb22232))
* move older planning files into folder ([e045436](https://github.com/IAmTheMitchell/renogy-ha/commit/e04543635f56a78f8056c8c838105619e96e5b25))

## v0.2.9 (2025-05-30)

### Bug Fixes

- Aggregate full Modbus frame before parsing
  ([`59cf4b6`](https://github.com/IAmTheMitchell/renogy-ha/commit/59cf4b68b3aca2916d01c5ac429ad180e5cf7e40))

- Report none when missing data for Power Generation Total sensor
  ([`2520523`](https://github.com/IAmTheMitchell/renogy-ha/commit/252052342cf57eb352e3c80caa000ecc6662ddcd))

### Build System

- Upgrade homeassistant dependency
  ([`94fec88`](https://github.com/IAmTheMitchell/renogy-ha/commit/94fec88957aa0966ca24fc451189f21ea14ac6ca))

### Chores

- Add repomix-output.xml to .gitignore
  ([`6a91c13`](https://github.com/IAmTheMitchell/renogy-ha/commit/6a91c132981ddaa110db0c96380ea9f7b71f82e6))


## v0.2.8 (2025-04-29)

### Bug Fixes

- Change log level for specific errors
  ([`b6c2e75`](https://github.com/IAmTheMitchell/renogy-ha/commit/b6c2e751f6d32019617c101d35fc8d37c176a72c))

- Improve log clarity when device fails to connect
  ([`eb789ce`](https://github.com/IAmTheMitchell/renogy-ha/commit/eb789cef17619b3ddc94bbfe8804cd75a11630a3))

- Reduce connection errors with bleak-retry-connector
  ([`763455f`](https://github.com/IAmTheMitchell/renogy-ha/commit/763455fc472fd1ab7f329020ed8c73c5bfd0ee01))

### Build System

- Upgrade homeassistant dependency
  ([`0e36bd1`](https://github.com/IAmTheMitchell/renogy-ha/commit/0e36bd1ce1d46806ca9c1e600d6eac65a86611fd))

### Chores

- Update copilot instructions for uv
  ([`353cecb`](https://github.com/IAmTheMitchell/renogy-ha/commit/353cecba086a8cb3dd94551a05ab731ce2163a3f))


## v0.2.7 (2025-04-25)

### Bug Fixes

- Divide Power Generation Total value by 1000
  ([`54545ca`](https://github.com/IAmTheMitchell/renogy-ha/commit/54545cafd59d97e81a36168c9e8c6ccd576f2371))

### Chores

- Add GitHub Copilot instructions
  ([`155660f`](https://github.com/IAmTheMitchell/renogy-ha/commit/155660f26c514403c17c169f9fde03ba34fdd876))

### Documentation

- Update README after testing with Wanderer
  ([`bf1478a`](https://github.com/IAmTheMitchell/renogy-ha/commit/bf1478a263f304fc8f9bd2282103482bfa296347))


## v0.2.6 (2025-04-09)

### Bug Fixes

- Add traceback to help debugging
  ([`03256fa`](https://github.com/IAmTheMitchell/renogy-ha/commit/03256fa7466477e4448cd16ff4a05f4da93b0fee))

- Change log severity to debug
  ([`432ba83`](https://github.com/IAmTheMitchell/renogy-ha/commit/432ba837b042f92a0b2a3dfc3aa37416295cf851))

- Configure log message severities
  ([`d7d3877`](https://github.com/IAmTheMitchell/renogy-ha/commit/d7d38778f403aac648d5fa947925c5b8d17aea00))

- Tweak log severities
  ([`d9a82e7`](https://github.com/IAmTheMitchell/renogy-ha/commit/d9a82e72b5bd4b0db514e35ab5f95c244fd52a0c))

### Code Style

- Commas in log formatting
  ([`8986068`](https://github.com/IAmTheMitchell/renogy-ha/commit/8986068efbd9f7d1a69c79873b329979cf5929fe))

- Update all logging to use percent style formatting, per Home Assistant guidelines
  ([`d380fa5`](https://github.com/IAmTheMitchell/renogy-ha/commit/d380fa5e6f89c0a46c411cafe83f02a358c48199))

### Documentation

- Update README with debug logging instructions
  ([`5c98be2`](https://github.com/IAmTheMitchell/renogy-ha/commit/5c98be22450c4106c664d5f08b0d6f6bd3915014))

### Refactoring

- Remove unused function
  ([`b11188f`](https://github.com/IAmTheMitchell/renogy-ha/commit/b11188f13635a68525c73ce54ae67681dc660f2f))


## v0.2.5 (2025-04-08)

### Bug Fixes

- Update name to match throughout code
  ([`a4cc088`](https://github.com/IAmTheMitchell/renogy-ha/commit/a4cc0889fd74536af240e8b69b6a76f54a02d890))

### Chores

- Update documented supported devices
  ([`d2b08cc`](https://github.com/IAmTheMitchell/renogy-ha/commit/d2b08cc10e5c4f303e70abcacce36b29f9218283))


## v0.2.4 (2025-04-08)

### Bug Fixes

- Remove invalid key from manifest
  ([`9d98ad3`](https://github.com/IAmTheMitchell/renogy-ha/commit/9d98ad3f3d33ae84d75b6ddd2d4772a8c5a10ebd))

### Chores

- Sort by domain, name, then alphabetical order
  ([`a53553d`](https://github.com/IAmTheMitchell/renogy-ha/commit/a53553d44f0ba58b4db7e0760910e03abb181b1c))

### Continuous Integration

- Add Hassfest validation
  ([`a921529`](https://github.com/IAmTheMitchell/renogy-ha/commit/a921529c0357434cc69097254f10b07d588e0fba))


## v0.2.3 (2025-04-08)

### Bug Fixes

- Try syncing version again
  ([`d6414fb`](https://github.com/IAmTheMitchell/renogy-ha/commit/d6414fbdf8e9de92c9db53f264d7a49916e217bf))

- Use version_variables for json version update
  ([`b95bdc7`](https://github.com/IAmTheMitchell/renogy-ha/commit/b95bdc764930e239d28e69a4edcb127b9f311fcd))


## v0.2.2 (2025-04-07)

### Bug Fixes

- Sync version in pyproject.toml and manifest.json
  ([`c673422`](https://github.com/IAmTheMitchell/renogy-ha/commit/c67342272f5e3ce166e2628587717abe6b68b530))


## v0.2.1 (2025-04-07)

### Bug Fixes

- Remove invalid HACS keys
  ([`944643d`](https://github.com/IAmTheMitchell/renogy-ha/commit/944643de382969438d735bf96c0ef8f52debe69a))

### Continuous Integration

- Add HACS validate.yaml
  ([`351f3dc`](https://github.com/IAmTheMitchell/renogy-ha/commit/351f3dc2ee1cc3e85b2990ac1c8d13e2d805f44a))

- Point to manifest.json for version
  ([`2480393`](https://github.com/IAmTheMitchell/renogy-ha/commit/2480393f8d4db0d2ffc9a4c39b541df5bc6b8e0a))


## v0.2.0 (2025-04-07)

### Bug Fixes

- Capitalize firmware type
  ([`072e610`](https://github.com/IAmTheMitchell/renogy-ha/commit/072e61078f347b9edafe8b8e2d7ba0540b88c349))

- Catch and log error during startup
  ([`06363b4`](https://github.com/IAmTheMitchell/renogy-ha/commit/06363b4fb61c179be0a15f2111f93dadb28c2327))

- Restrict to Python >=3.13 due to Home Assistant constraints
  ([`12e10cd`](https://github.com/IAmTheMitchell/renogy-ha/commit/12e10cd1e744293631ee2b7d210a320203cf9482))

- Update pyproject.toml to support Python >=3.10
  ([`3e74f25`](https://github.com/IAmTheMitchell/renogy-ha/commit/3e74f25956a10f15cd30501ebaaf7512e5438ce4))

- Update to use new renogy-ble parse signature
  ([`38db89a`](https://github.com/IAmTheMitchell/renogy-ha/commit/38db89a2da218d11f9201284e9af5cda8e4cf6ce))

- Use device_type as temporary model name
  ([`1ce2002`](https://github.com/IAmTheMitchell/renogy-ha/commit/1ce200258b1a691c9f945fb1c0706a13dff7ead7))

### Chores

- Automate test and release
  ([`c211c83`](https://github.com/IAmTheMitchell/renogy-ha/commit/c211c836de216bc9bcf3de8a55ad58939c20edc3))

### Features

- Prompt user for device type
  ([`9150126`](https://github.com/IAmTheMitchell/renogy-ha/commit/9150126137588ab59dc72a19fba4d6ea7994bd69))

- Update to latest renogy-ble library
  ([`50542ec`](https://github.com/IAmTheMitchell/renogy-ha/commit/50542ecbd3a615aaabf2c479bc4b6a1864c9c7fb))

### Refactoring

- Divy up commands by device type
  ([`7c7fed1`](https://github.com/IAmTheMitchell/renogy-ha/commit/7c7fed1fe18bbdb6cf7fff6c403510de4de33a8a))

- Dry up config schema
  ([`85e6d18`](https://github.com/IAmTheMitchell/renogy-ha/commit/85e6d1844d44a98d2f21f8dd20ead0246cd24c17))

- Dry up entity creation
  ([`8bbc216`](https://github.com/IAmTheMitchell/renogy-ha/commit/8bbc2163961dc98f98e69e82c45d3ea0809efc5b))

- Move config values to const.py
  ([`3f8ef75`](https://github.com/IAmTheMitchell/renogy-ha/commit/3f8ef75d8786612042e20f244cbe34705443a7a3))

- Remove unused constants
  ([`bcd5cd9`](https://github.com/IAmTheMitchell/renogy-ha/commit/bcd5cd977b730135990a003b16da6a9aff4412e9))

- Use Enum for device type
  ([`b846f19`](https://github.com/IAmTheMitchell/renogy-ha/commit/b846f19d1202c466747b9fe7cca1b25a91c72167))

- Use f strings formatting
  ([`7c874a9`](https://github.com/IAmTheMitchell/renogy-ha/commit/7c874a9521d65545f0bae7f2d581451edae22ea8))


## v0.1.7 (2025-03-21)


## v0.1.6 (2025-03-20)


## v0.1.5 (2025-03-19)


## v0.1.4 (2025-03-19)
