# Persistent Entity Overrides for Home Assistant

A general-purpose Home Assistant integration that exports, imports, and backs-up entity metadata like friendly name, visibility, and enabled status — preserving these values even across integration resets. If you have ever had to remove a device integration (e.g., Z-Wave, etc.) and lost your carefully curated entity metadata, you know why I created this...

## Features 🔧

*	Apply overrides to any entity in Home Assistant
*	Friendly name, enabled / disabled, and visible / hidden support
*	Configurable backup retention
*	UI-based config via Home Assistant’s Integrations panel
*	Manual export + reapply services

## Installation via HACS 🔧

1.	Go to HACS → Integrations → ⋮ menu → “Custom repositories”
2.	Add: https://github.com/john-derose/homeassistant-entity-overrides as a Integration repository
3.	Install “Entity Overrides”
4.	Restart Home Assistant
5.	Configure via Settings → Devices & Services → Add Integration

## Options 🔁

Accessible via the integration’s ⚙️ menu:
* Max backups to retain
* Enable Restore on HA startup
* Trigger one-time Export

## Services 🛠

| Service                           | Description                        |
|----------------------------------|------------------------------------|
| `entity_overrides.apply_overrides`  | Reapply overrides immediately       |
| `entity_overrides.export_overrides` | Export current overrides to file   |

## File Paths 🗂

*	Exports: config/entity_overrides/overrides.yaml
*	Backups: config/entity_overrides/backups/

## Example overrides.yaml 📘

    sensor.garage_motion_sensor_state:
      friendly_name: "Garage Motion"
    light.bedroom_lamp_color_temp:
      enabled: false
    switch.water_heater:
      visible: false

## Codeowners 🧑‍💻

  @john-derose

## License 🪪

MIT
