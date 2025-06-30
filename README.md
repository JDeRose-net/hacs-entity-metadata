# Entity Metadata Persistence for Home Assistant

A general-purpose Home Assistant integration that exports, imports, and backs-up
entity metadata such as friendly name, visibility, and enabled status. Useful
for preserving these values across integration resets.

If you have ever had to remove a device integration (e.g., Z-Wave, etc.) and
lost your carefully curated entity metadata, you know why we created this...

## Features 💡

*	Export/import metadata for any Home Assistant entities
*	Support for friendly_name, enabled, and visible
*	Manual export/import triggers
*   Option to automatically import at Home Assistant startup
*	Configurable backup retention (# of copies)
*	UI-based configuration via Home Assistant's Integrations panel

## Installation via HACS 📦

1.	Go to HACS → ⋮ menu → Custom Repositories
2.	Add https://github.com/jderose-net/hass-entity-metadata as an Integration repository
3.	Go to Settings → Devices & Services → Add Integration
4.  Add Entity Metadata
4.	Restart Home Assistant
5.	Configure via Settings → Devices & Services → Entity Metadata → Configure

## Options 🔁

Accessible via the integration's ⚙️  menu:
* Set maximum number of backup files to retain
* Enable import on startup
* Trigger export

## Services 🛠

| Service                             | Description                                     |
|-------------------------------------|-------------------------------------------------|
| `entity_overrides.export_overrides` | Export metadata values to overrides.yaml file   |
| `entity_overrides.import_overrides` | Import metadata values from overrides.yaml file |

## Files 🗂

*	Exports: config/entity_metadata/overrides.yaml
    sensor.garage_motion_sensor_state:
      friendly_name: "Garage Motion"
    light.bedroom_lamp_color_temp:
      enabled: false
    switch.water_heater:
      visible: false

*	Backups: config/entity_metadata/backups/overrides.YYYYMMDD-HHMMSS.yaml

## Codeowners 🧑💻

  @john-derose

## License 🪪

  MIT
