[![Svenska Trygghetslosningar](https://github.com/gjohansson-ST/stl/blob/master/img/logo.png)](https://www.stl.nu/)

[![hacs_badge](https://img.shields.io/badge/HACS-Default-orange.svg?style=for-the-badge&cacheSeconds=3600)](https://github.com/custom-components/hacs)
[![size_badge](https://img.shields.io/github/repo-size/gjohansson-ST/stl?style=for-the-badge&cacheSeconds=3600)](https://github.com/gjohansson-ST/stl)
[![version_badge](https://img.shields.io/github/v/release/gjohansson-ST/stl?label=Latest%20release&style=for-the-badge&cacheSeconds=3600)](https://github.com/gjohansson-ST/stl/releases/latest)
[![download_badge](https://img.shields.io/github/downloads/gjohansson-ST/stl/total?style=for-the-badge&cacheSeconds=3600)](https://github.com/gjohansson-ST/stl/releases/latest)


# Integratation to Svenska Trygghetslösningar
---
**Title:** "Svenska Trygghetslösningar"

**Description:** "Support for Svenska Trygghetslösningar integration with Homeassistant."

**Date created:** 2021-04-05

**Last update:** 2021-05-13

---

Integrates with Swedish Svenska Trygghetslösningar home alarm system.
Currently supporting alarm_panel but will extend to binary sensors with next version.
Would most likely work with any Visonic alarm using api version 7.0

Binary sensors will be added as part of next release for door sensors to be included.

## Installation

### Option 1 (preferred)

Use [HACS](https://hacs.xyz/) to install

### Option 2

Below config-folder create a new folder called`custom_components` if not already exist.

Below new `custom_components` folder create a new folder called `stl`

Upload the files/folders in `custom_components/stl` directory to the newly created folder.

Restart before proceeding

## Activate integration in HA

After installation go to "Integrations" page in HA, press + and search for Svenska Trygghetslösningar
Follow onscreen information to type username, password, code etc.
No restart needed

### There is no option to use yaml for configuration
