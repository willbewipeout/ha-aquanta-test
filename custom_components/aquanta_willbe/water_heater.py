"""Aquanta water heater component."""

from __future__ import annotations

import logging
import asyncio
import json

# ==============================================================================
# PERMANENT LOGIN CONFIGURATION
# Fill in your Aquanta Portal login details below.
# The script will use these to automatically generate a fresh cookie when needed.
# ==============================================================================
AQUANTA_EMAIL = "Email"
AQUANTA_PASSWORD = "Password"
AQUANTA_API_KEY = "API Key" 
# ==============================================================================

# Global variable to store the active session cookie
CACHED_PORTAL_COOKIE = None

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

from homeassistant.helpers.aiohttp_client import async_get_clientsession

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

    async def _async_get_fresh_cookie(self):
        """Async method to perform login flow using aiohttp."""
        global CACHED_PORTAL_COOKIE
        LOGGER.info("Aquanta: Attempting to refresh session cookie via Async Login...")

        try:
            session = async_get_clientsession(self.hass)

            # Step 1: Google Identity Toolkit Login
            google_url = f"https://www.googleapis.com/identitytoolkit/v3/relyingparty/verifyPassword?key={AQUANTA_API_KEY}"
            google_payload = {
                "email": AQUANTA_EMAIL,
                "password": AQUANTA_PASSWORD,
                "returnSecureToken": True
            }

            async with session.post(google_url, json=google_payload) as resp_google:
                if resp_google.status != 200:
                    text = await resp_google.text()
                    LOGGER.error(f"Aquanta Login Failed (Google): {text}")
                    return None
                
                google_data = await resp_google.json()
                id_token = google_data.get("idToken")

            # Step 2: Aquanta Portal Login
            aquanta_url = "https://portal.aquanta.io/portal/login"
            aquanta_payload = {"idToken": id_token, "remember": True}
            
            async with session.post(aquanta_url, json=aquanta_payload) as resp_aquanta:
                if resp_aquanta.status != 200:
                    text = await resp_aquanta.text()
                    LOGGER.error(f"Aquanta Login Failed (Portal): {resp_aquanta.status} - {text}")
                    return None
                
                # Step 3: Extract Cookies
                # aiohttp stores cookies in the response object
                cookies = resp_aquanta.cookies
                
                # We construct the cookie string manually to be safe
                cookie_parts = []
                for key, morsel in cookies.items():
                    cookie_parts.append(f"{key}={morsel.value}")
                
                cookie_string = "; ".join(cookie_parts)
                
                if not cookie_string:
                    LOGGER.error("Aquanta Login Failed: No cookies received in response.")
                    return None

                CACHED_PORTAL_COOKIE = cookie_string
                LOGGER.info("Aquanta: Successfully refreshed session cookie!")
                return CACHED_PORTAL_COOKIE

        except Exception as e:
            LOGGER.error(f"Aquanta Login Error: {e}")
            return None


    async def async_set_temperature(self, **kwargs):
        """Set new target temperature."""
        target_temp = kwargs.get(ATTR_TEMPERATURE)
        if target_temp is None:
            return

        LOGGER.warning(f"--- COOKIE STRATEGY for {target_temp}C ---")

        try:
            if not self._api:
                LOGGER.error("Aquanta: API client missing.")
                return

            # Check Configuration
            if "YOUR_EMAIL" in AQUANTA_EMAIL:
                LOGGER.error("Aquanta Config Error: Please edit water_heater.py and fill in AQUANTA_EMAIL and AQUANTA_PASSWORD.")
                return

            clean_temp = int(round(target_temp))

            # --- EXECUTION LOGIC ---
            global CACHED_PORTAL_COOKIE
            
            # 1. Login if we don't have a cookie yet
            if CACHED_PORTAL_COOKIE is None:
                await self._async_get_fresh_cookie()
                
            if CACHED_PORTAL_COOKIE is None:
                LOGGER.error("Aquanta: Could not obtain cookie. Aborting.")
                return

            # Helper function to send the request
            async def _send_request(cookie_to_use):
                session = async_get_clientsession(self.hass)
                url = f"https://portal.aquanta.io/portal/set/advancedSettings?id={self.aquanta_id}"
                
                payload = {
                    "aquantaIntel": True,
                    "aquantaSystem": False,
                    "setPoint": clean_temp
                }
                
                headers = {
                    "Cookie": cookie_to_use,
                    "Content-Type": "application/json",
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    "Referer": "https://portal.aquanta.io/views/settings.shtml",
                    "Origin": "https://portal.aquanta.io"
                }
                
                return await session.put(url, json=payload, headers=headers)

            # 2. Try Request
            resp = await _send_request(CACHED_PORTAL_COOKIE)

            # 3. Handle Expiry (401)
            if resp.status == 401:
                LOGGER.warning("Aquanta: Cookie expired (401). Refreshing and retrying...")
                await self._async_get_fresh_cookie()
                
                if CACHED_PORTAL_COOKIE:
                    # Retry once
                    resp = await _send_request(CACHED_PORTAL_COOKIE)

            # 4. Final Result Check
            if resp.status in [200, 201, 204]:
                LOGGER.info(f"Aquanta: Successfully set temperature to {clean_temp}°C")
                await self.coordinator.async_request_refresh()
            else:
                text = await resp.text()
                LOGGER.error(f"Aquanta Error: Failed to set temp (Status {resp.status}). Response: {text}")

        except Exception as e:
            LOGGER.error(f"Aquanta Critical Error: {e}")
