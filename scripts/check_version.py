import json
import sys
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: check_version.py <git_tag>")
    sys.exit(1)

# Strip 'v' from tag prefix if present
git_tag = sys.argv[1].lstrip("v")

manifest_path = Path("custom_components/entity_overrides/manifest.json")

try:
    with manifest_path.open() as f:
        manifest = json.load(f)
except Exception as e:
    print(f"Failed to read manifest.json: {e}")
    sys.exit(1)

manifest_version = manifest.get("version")

if manifest_version != git_tag:
    print(f"❌ Version mismatch: Git tag is {git_tag}, but manifest has {manifest_version}")
    sys.exit(1)

print(f"✅ Version matches: {git_tag}")
