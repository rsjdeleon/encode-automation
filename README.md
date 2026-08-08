# Encode Automation

This repository is organized with compatibility-first restructuring.

## Active app entry points
- assistance_form.py
- config_manager.py
- social_worker_manager.py

These remain at repository root so existing run/build workflows keep working.

## Package layout
- core/
  - Shared non-UI logic and runtime path definitions.
  - Includes: core/config.py, core/paths.py, core/utilities.py, core/license.py
- ui/
  - Shared UI resources and widgets.
  - Includes: ui/styles.py, ui/widgets.py
- db/
  - Database layer implementations.
  - Canonical modules: db/config_store.py, db/person_store.py, db/worker_store.py
  - Compatibility shims: db/db_config.py, db/db_new_person.py, db/db_worker.py
- scripts/
  - Utility/maintenance script entry points.
- build/
  - Build/release implementation scripts.
- archive/
  - Archived backups and legacy files.

## Compatibility wrappers
Root modules currently remain as wrappers for compatibility during migration:
- config.py -> core/config.py
- paths.py -> core/paths.py
- utilities.py -> core/utilities.py
- license.py -> core/license.py
- styles.py -> ui/styles.py
- widgets.py -> ui/widgets.py
- db_config.py -> db/db_config.py
- db_new_person.py -> db/db_new_person.py
- db_worker.py -> db/db_worker.py
  - (canonical targets are db/config_store.py, db/person_store.py, db/worker_store.py)

This allows existing imports to continue working while package layout is adopted incrementally.

## Build command
- Keep using build_release.ps1 at repo root.
- The root script delegates to build/build_release.ps1.

## Build executables

### Prerequisites
- Use the project virtual environment at .venv.
- Install dependencies from requirements.txt.
- PyInstaller must be available in the virtual environment.

### Windows build
Run from the repository root:

```powershell
powershell -ExecutionPolicy Bypass -File .\build_release.ps1
```

### What the build script does
- Builds assistance_form.py, config_manager.py, and social_worker_manager.py as windowed PyInstaller apps.
- Places the final executables in dist-release/.
- Copies each app's bundled runtime folder into dist-release/.
- Seeds shared data files into dist-release/ only if they are not already present:
  - config.db
  - person-record.db
  - worker.db
  - data-new.pkl
  - default.png
  - license.json

### Expected output
After a successful build, dist-release/ contains:
- assistance_form.exe
- config_manager.exe
- social_worker_manager.exe
- the corresponding _internal_* runtime folders
- the shared data files listed above

## Operational docs
- Main config work log: docs/maintenance/CONFIG_WORK.md
- Migration tracker: archive/MIGRATION_INDEX.md
