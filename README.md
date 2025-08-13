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
2.	Add https://github.com/jderose-net/hacs-entity-metadata as an Integration repository
3.	Go to Settings → Devices & Services → Add Integration
4.  Add Entity Metadata
4.	Restart Home Assistant
5.	Configure via Settings → Devices & Services → Entity Metadata → Configure

## Options 🔁

Accessible via the integration's ⚙️  menu:

- **Export All Entities**  
  Includes entities that have no overrides (empty `{}` objects). Helpful for full inventories and bulk editing.  
  _Note:_ If you later import with `merge: false`, these empty entries will **reset** name/icon/hidden/disabled. Keep `merge: true` for safety.

- **Domains**  
  Multi-select filter applied during export. Example: `["light", "switch"]`.

- **Backup retention**  
  Number of timestamped backup files to keep under  
  `/config/etc/entity_metadata/backups/`. Older backups are pruned after each export.

- **Auto-Import on Startup**  
  If enabled, runs `entity_metadata.import_overrides` with `merge: true` on Home Assistant start.

- **Export Now**  
  One-shot action in the Options form that immediately triggers an export (writes `overrides.yaml` and a timestamped backup). This toggle is **not** persisted.

### Paths
- **Overrides:** `/config/etc/entity_metadata/overrides.yaml`  
- **Backups:** `/config/etc/entity_metadata/backups/overrides-YYYYMMDD-HHMMSS.yaml`

## Services 🛠

| Service                            | Description                                     |
|------------------------------------|-------------------------------------------------|
| `entity_metadata.export_overrides` | Export metadata values to overrides.yaml file   |
| `entity_metadata.import_overrides` | Import metadata values from overrides.yaml file |

## Files 🗂

* config/etc/entity_metadata/overrides.yaml
* config/etc/entity_metadata/backups/overrides.YYYYMMDD-HHMMSS.yaml

## Codeowners 🧑💻

  @john-derose

## License 🪪

  MIT
