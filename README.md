# Aquanta Water Heater Controller for Home Assistant with Temp Control


Component to integrate with [Aquanta Smart Water Heater Controllers][aquanta] through their undocumented cloud API.  Most of the work is from this repo (https://github.com/VolantisDev/ha-aquanta).

This is my first vibe coding work, so mistakes are bound to be included.

**This component will set up the following platforms.**

| Platform        | Description                                |
| --------------- | ------------------------------------------ |
| `water_heater`  | Manage one or more Aquanta devices.        |
| `sensor`        | Additional data about each Aquanta device  |
| `binary_sensor` | On/Off values for various Aquanta settings |
| `switch`        | Supports toggling Away and Boost modes     |

This integration uses cloud polling to update the data about your water heater controllers regularly.

Note: This is an unofficial integration that is not related to the Aquanta company in any way. There is no official public API yet, so the API being used is undocumented and could change (or be removed) at any point.

## Installation

### Option 1: HACS (Recommended)

1. Add this repository to HACS.
2. Search for "Aquanta" under "Integrations".
3. Install the integration.
4. Restart Home Assistant.

### Option 2: Manual

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `aquanta`.
4. Download _all_ the files from the `custom_components/aquanta/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant.


## Configuration

All configuration is done in the UI.

1. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "Aquanta".
2. Enter your Aquanta account email address and password in the form and submit to add the integration.

Your Aquanta devices should now show up in Home Assistant and the device data will be updated from the cloud every 60s by default.



