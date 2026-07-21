# Archive

This folder stores legacy and backup artifacts moved out of the project root to keep the workspace tidy.

## Structure
- `backups/config/`: historical `config.db` backup files.
- `backups/worker/`: historical `worker.db` backup files.
- `legacy-code/`: old or non-runtime code snapshots.

## Notes
- Active runtime files remain at root for compatibility.
- Only artifacts not needed for normal app startup should be moved here.
