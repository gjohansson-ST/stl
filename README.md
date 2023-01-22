# Project has been archived and is not maintained!

# Integratation to Svenska Trygghetslösningar
---
**Title:** "Svenska Trygghetslösningar"

**Description:** "Support for Svenska Trygghetslösningar integration with Homeassistant."

**Date created:** 2021-04-05

**Last update:** 2023-01-22

---

Integrates with Swedish Svenska Trygghetslösningar home alarm system.
Currently supporting alarm_panel and doorsensors
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
