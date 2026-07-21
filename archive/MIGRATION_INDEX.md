# Migration Index

This file tracks what has been moved from the project root as part of the conservative cleanup.

## Completed
- Moved `scratch.py` to `archive/legacy-code/scratch.py`.
- Moved `db_person.py` to `archive/legacy-code/db_person.py`.
- Moved `assistance-form.py` to `archive/legacy-code/assistance-form.py`.
- Moved `data.pkl` to `archive/legacy-code/data.pkl`.
- Moved the full build implementation to `build/build_release.ps1`.
- Kept root compatibility via a wrapper script in `build_release.ps1`.
- Added centralized runtime paths in `paths.py` for db, cache, license, and crash log files.
- Updated `db_config.py`, `db_new_person.py`, `db_worker.py`, `license.py`, and `assistance-form-new.py` to use centralized path constants.
- Moved `generate_key.py` implementation into `scripts/generate_key.py`.
- Kept root compatibility via `generate_key.py` wrapper.
- Added scripts launcher `scripts/sync_config_from_website.py` while keeping root module import-compatible.
- Moved `CONFIG_WORK.md` content to `docs/maintenance/CONFIG_WORK.md`.
- Kept root compatibility note in `CONFIG_WORK.md`.
- Moved shared UI modules into `ui/`:
  - `ui/styles.py`
  - `ui/widgets.py`
- Kept root compatibility wrappers in `styles.py` and `widgets.py`.
- Moved shared core modules into `core/`:
  - `core/paths.py`
  - `core/utilities.py`
  - `core/license.py`
- Kept root compatibility wrappers in `paths.py`, `utilities.py`, and `license.py`.
- Moved configuration implementation to `core/config.py`.
- Kept root compatibility wrapper in `config.py`.
- Moved database implementations into `db/`:
  - `db/db_config.py`
  - `db/db_new_person.py`
  - `db/db_worker.py`
- Kept root compatibility wrappers in `db_config.py`, `db_new_person.py`, and `db_worker.py`.
- Introduced canonical renamed db modules:
  - `db/config_store.py`
  - `db/person_store.py`
  - `db/worker_store.py`
- Converted `db/db_config.py`, `db/db_new_person.py`, and `db/db_worker.py` to compatibility shims pointing to canonical db modules.
- Added canonical main entry script `assistance_form.py`.
- Removed `assistance-form-new.py`; `assistance_form.py` is now the single runnable main entry file.
- Updated build script targets to use canonical `assistance_form.py`.
- Moved root backup artifacts into archive folders:
  - `archive/backups/config/config.db.bak_before_barangay_city_link_20260712_143840`
  - `archive/backups/config/config.db.bak_before_dual_pairs_migration_20260712_154047`
  - `archive/backups/config/config.db.bak_before_pairs_migration_20260712_151959`
  - `archive/backups/worker/worker.db.bak_before_drop_thru_firstname`
  - `archive/backups/worker/worker.db.bak_before_fullname_migration`
- Created organizational folders:
  - `archive/backups/config/`
  - `archive/backups/worker/`
  - `archive/legacy-code/`
  - `scripts/`
  - `build/`

## Pending (next safe passes)
- Optional: migrate remaining root imports in helper/wrapper scripts to package paths where appropriate.
- Optional: after a stability period, remove now-redundant root wrappers if no external dependencies require them.

## Documentation updates completed
- Added root `README.md` documenting:
  - Current folder conventions
  - Compatibility wrapper policy
  - Build script delegation
  - Operational document locations

## Direct package import adoption completed
- Updated `assistance_form.py` imports to use package modules directly:
  - `ui.widgets`, `ui.styles`
  - `core.utilities`, `core.config`, `core.paths`, `core.license`
  - `db.person_store`, `db.worker_store`, `db.config_store`
- Updated `config_manager.py` imports to use:
  - `db.config_store`
  - `ui.styles`
- Updated `social_worker_manager.py` imports to use:
  - `db.worker_store`
  - `ui.styles`
- Updated `sync_config_from_website.py` imports to use:
  - `db.config_store`
  - `db.worker_store`
- Root wrapper modules remain for compatibility with any external scripts not yet migrated.

## Resolved tooling issue
- Terminal-based file moves were unreliable in this session; file relocation was completed successfully via Python file operations.

## Compatibility Policy
- Runtime entry scripts remain at root.
- Runtime data files remain at root.
- Any move must preserve runnable state after each phase.
