# Renson Flux for Home Assistant

A lightweight, local Home Assistant custom component to monitor and control Renson Flux ventilation units. This integration connects directly to the Renson unit over your local network using the official third-party REST API—no cloud connection required.

## Features

**Sensors (Updates every 15 minutes or instantly after a command):**
* **Active Mode & Speed:** Displays the current mode (Automatic or Manual) and the exact live fan percentage.
* **Summer Breeze:** Indicates if the summer bypass/breeze mode is active.
* **CO2 Level:** Reads the local CO2 sensor (if installed).
* **VOC Level:** Reads the local odors/VOC sensor (if installed).
* **Humidity Level:** Reads the local humidity sensor (if installed).
* **Ventilation Limits:** Stores the physical lower and upper percentage limits of your unit as hidden attributes.

**Controls (Services):**
* `renson_flux.set_boost`: Set a custom fan percentage (11-100%) and duration.
* `renson_flux.set_minimum`: Drop the fan to the absolute minimum safe speed for a set duration (great for sleep).
* `renson_flux.set_auto`: Instantly cancel all timers and return the unit to automatic demand management.

---

## Installation via HACS

The easiest way to install this integration is using the Home Assistant Community Store (HACS).

1. Open **HACS** in your Home Assistant sidebar.
2. Click the three dots in the top right corner and select **Custom repositories**.
3. Paste the URL of this GitHub repository into the **Repository** field.
4. Select **Integration** as the category and click **Add**.
5. Close the popup, search for **Renson Flux** in HACS, and click **Download**.
6. **Restart Home Assistant.**

---

## Configuration

This integration supports full UI configuration (Config Flow). You do not need to edit your `configuration.yaml`.

1. Go to **Settings > Devices & Services**.
2. Click **+ Add Integration** in the bottom right.
3. Search for **Renson Flux**.
4. Enter your unit's local **IP Address** and your 10-digit **API Key**.
5. Click **Submit**. Your sensors will appear instantly!

---

## Recommended Dashboard Card

Want a clean, ready-to-use control panel for your Home Assistant dashboard? Add a **Manual** card and paste the YAML below to get a simple readout with quick-action buttons for Shower Boosts, Sleep Mode, and Auto Reset.

```yaml
type: vertical-stack
cards:
  - type: entities
    title: Renson Flux Dashboard
    entities:
      - entity: sensor.renson_active_mode
        name: Current Mode & Speed
      - entity: sensor.renson_breeze_status
        name: Summer Breeze
      - entity: sensor.renson_co2_level
        name: CO2
      - entity: sensor.renson_voc_level
        name: VOC (Odors)
      - entity: sensor.renson_humidity_level
        name: Humidity
  - type: grid
    columns: 2
    square: false
    cards:
      - type: button
        name: 100% Boost (30m)
        tap_action:
          action: call-service
          service: renson_flux.set_boost
          data:
            speed: 100
            timer: 30
      - type: button
        name: Minimum (60m)
        tap_action:
          action: call-service
          service: renson_flux.set_minimum
          data:
            timer: 60
      - type: button
        name: Sleep (8 Hours)
        tap_action:
          action: call-service
          service: renson_flux.set_boost
          data:
            speed: 20
            timer: 30
      - type: button
        name: Auto (Demand)
        tap_action:
          action: call-service
          service: renson_flux.set_auto