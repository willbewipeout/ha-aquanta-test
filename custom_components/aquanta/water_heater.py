"""Aquanta water heater component."""

from __future__ import annotations

import logging
import asyncio # <--- FIXED: Added missing import
import json

# ==============================================================================
# PASTE YOUR BROWSER COOKIE HERE
# Example: "JSESSIONID=123456789; other_token=abc;"
# ==============================================================================
PORTAL_COOKIE = "_gcl_au=1.1.10278341.1769975114; sbjs_migrations=1418474375998%3D1; sbjs_current_add=fd%3D2026-02-01%2019%3A45%3A13%7C%7C%7Cep%3Dhttps%3A%2F%2Faquanta.io%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fcommunity.home-assistant.io%2F; sbjs_first_add=fd%3D2026-02-01%2019%3A45%3A13%7C%7C%7Cep%3Dhttps%3A%2F%2Faquanta.io%2F%7C%7C%7Crf%3Dhttps%3A%2F%2Fcommunity.home-assistant.io%2F; sbjs_current=typ%3Dreferral%7C%7C%7Csrc%3Dcommunity.home-assistant.io%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_first=typ%3Dreferral%7C%7C%7Csrc%3Dcommunity.home-assistant.io%7C%7C%7Cmdm%3Dreferral%7C%7C%7Ccmp%3D%28none%29%7C%7C%7Ccnt%3D%2F%7C%7C%7Ctrm%3D%28none%29%7C%7C%7Cid%3D%28none%29%7C%7C%7Cplt%3D%28none%29%7C%7C%7Cfmt%3D%28none%29%7C%7C%7Ctct%3D%28none%29; sbjs_udata=vst%3D1%7C%7C%7Cuip%3D%28none%29%7C%7C%7Cuag%3DMozilla%2F5.0%20%28Macintosh%3B%20Intel%20Mac%20OS%20X%2010_15_7%29%20AppleWebKit%2F537.36%20%28KHTML%2C%20like%20Gecko%29%20Chrome%2F144.0.0.0%20Safari%2F537.36; _ga_G5V0CL50MS=GS2.1.s1769975114$o1$g0$t1769975114$j60$l0$h0; _ga=GA1.1.1480383937.1769975114; cf_clearance=EMXcQ5Dl5aUc_lt2T56N2XEuqbqhPZee6gUxur0s8_s-1769975114-1.2.1.1-A7XYiShFI9lBOIp8DNTb02xCVnBOsqtLPSWaNOqq.2CF64JB4j.h6g0IUrYyoZrVeSYogU6lJnmVX9s2cXOc0KTJ8TwhdJKYEYa.2.WB3sryUMVkK1_x_042gb.ys5PI0iAhXkUZvMSUmAw1O0iKMO_m.73TWw4ZqL2rsaSvaS1kHnMAMuzALPPsGj05NuGDCPBg_w9aNAIvWZYd8lPz9jzI3T1B8XIdk3BQzeHfwQg; _fbp=fb.1.1769975114537.4238373266210619; aquanta-prod=s%3ACgMD5kOnj-gHPJqNe4zWVgj7LM4lcCrw.W%2F5kgqpMJxpVht7REuxdRlcmFg6xdlf5Ao6ZPegbwIA" 
# ==============================================================================


from homeassistant.components.water_heater import (
    STATE_ECO,
    STATE_PERFORMANCE,
    STATE_OFF,
    WaterHeaterEntity,
    WaterHeaterEntityFeature,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    UnitOfTemperature,
    ATTR_TEMPERATURE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .entity import AquantaEntity
from .const import DOMAIN, LOGGER

async def async_setup_entry(
    hass: HomeAssistant,
    config_entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Initialize Aquanta devices from config entry."""

    coordinator = hass.data[DOMAIN][config_entry.entry_id]
    entities: list[AquantaWaterHeater] = []

    for aquanta_id in coordinator.data["devices"]:
        entities.append(
            AquantaWaterHeater(coordinator, aquanta_id)
        )

    async_add_entities(entities)

class AquantaWaterHeater(AquantaEntity, WaterHeaterEntity):
    """Representation of an Aquanta water heater controller."""

    _attr_has_entity_name = True
    _attr_supported_features = (WaterHeaterEntityFeature.AWAY_MODE | WaterHeaterEntityFeature.TARGET_TEMPERATURE)
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _attr_operation_list = [STATE_ECO, STATE_PERFORMANCE, STATE_OFF]
    _attr_name = "Water heater"

    def __init__(self, coordinator, aquanta_id) -> None:
        """Initialize the water heater."""
        super().__init__(coordinator, aquanta_id)
        self._attr_name = "Water heater"
        self._attr_unique_id = self._base_unique_id + "_water_heater"
        LOGGER.debug("Created water heater with unique ID %s", self._attr_unique_id)

    @property
    def current_temperature(self):
        """Return the current temperature."""
        return self.coordinator.data["devices"][self.aquanta_id]["water"]["temperature"]

    @property
    def current_operation(self):
        """Return current operation ie. eco, performance, off."""
        operation = STATE_OFF

        if (
            self.coordinator.data["devices"][self.aquanta_id]["info"]["currentMode"][
                "type"
            ]
            != "off"
        ):
            found = False

            for record in self.coordinator.data["devices"][self.aquanta_id]["info"][
                "records"
            ]:
                if record["type"] == "boost" and record["state"] == "ongoing":
                    operation = STATE_PERFORMANCE
                    found = True
                elif record["type"] == "away" and record["state"] == "ongoing":
                    operation = STATE_OFF
                    found = True
                    break

            if not found:
                operation = STATE_ECO

        return operation

#    @property
#    def target_temperature(self):
#        """Return the temperature we try to reach."""
#        if self.coordinator.data["devices"][self.aquanta_id]["advanced"][
#            "thermostatEnabled"
#        ]:
#            return self.coordinator.data["devices"][self.aquanta_id]["advanced"][
#                "setPoint"
#            ]
#        else:
#            return None

    @property
    def target_temperature(self):
        """Return the temperature we try to reach."""
        advanced_data = self.coordinator.data["devices"][self.aquanta_id].get(
            "advanced", {}
        )
        if advanced_data.get("thermostatEnabled"):
            return advanced_data.get("setPoint")
        return None

#    @property
#    def min_temp(self):
#        """Return the minimum temperature."""
#        return 110  # Fahrenheit (Aquanta standard min)

#    @property
#    def max_temp(self):
#        """Return the maximum temperature."""
#        return 140  # Fahrenheit (Aquanta standard max)

    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return

        LOGGER.warning(f"--- COOKIE STRATEGY v0.34 for {target_temp}C ---")

        try:
            if not self._api:
                return

            device_obj = self._api[self.aquanta_id]
            helper = device_obj._helper
            clean_temp = int(round(target_temp))

            if "PASTE_YOUR_COOKIE" in PORTAL_COOKIE or len(PORTAL_COOKIE) < 5:
                LOGGER.error("Aquanta: Missing PORTAL_COOKIE in water_heater.py")
                return

            # Mimic the Portal Payload
            payload = {
                "aquantaIntel": True,
                "aquantaSystem": False,
                "setPoint": clean_temp
            }

            url = "https://portal.aquanta.io/portal/set/advancedSettings"

            def _send_portal_request():
                session = helper._session
                
                # Headers that mimic a browser session
                headers = {
                    "Cookie": PORTAL_COOKIE,
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://portal.aquanta.io/views/settings.shtml",
                    "Origin": "https://portal.aquanta.io"
                }
                
                # Send the request
                # We try appending the ID to the URL as a fail-safe
                url_with_id = f"{url}?id={self.aquanta_id}"
                return session.put(url_with_id, json=payload, headers=headers)

            resp = await self.hass.async_add_executor_job(_send_portal_request)

            if resp is not None:
                if resp.status_code in [200, 201, 204]:
                    LOGGER.info(f"Aquanta: Successfully set temperature to {clean_temp}")
                    await self.coordinator.async_request_refresh()
                else:
                    LOGGER.error(f"Aquanta: Failed to set temp. Status: {resp.status_code}. Your Cookie may have expired.")
            else:
                LOGGER.error("Aquanta: Connection failed.")

        except Exception as e:
            LOGGER.error(f"Aquanta: Error setting temperature: {e}")
