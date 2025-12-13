# CHANGELOG


## [0.2.10](https://github.com/IAmTheMitchell/renogy-ha/compare/v0.2.9...v0.2.10) (2025-12-13)


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
