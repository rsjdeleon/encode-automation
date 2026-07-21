# Config Work — Status

Living status tracker for two pieces of work on the config system (`config.py` / `db_config.py` / `config_manager.py`). Update this file immediately after finishing each task below — don't batch it at the end. Full reasoning lives in the plan this was built from: `.claude/plans/what-approach-should-we-bright-panda.md` (kept locally, not committed).

## Part 1 — Sync gform/website dual values from the live CRIMS website

Several config lists store two values per item: one used to fill the Google Form, one used to fill the live website. The website-facing value was hand-typed and can drift. This adds a script to pull the real option text from the live site's combobox and correct the config.

Applies to: `approved_by_list`, `civil_status_list`, `relationship_list`, `fund_source_list` (per-row match, one option per config row) and `list_of_city`'s Region (uniform match — same scraped value applied to every city row). Not covered: `gender_list`/`target_sector_list`/`mode_of_release`/`financial_assistance_list` (no second value), `client_sub_category`/`approver_list` (not wired to a live field), and per-city Barangay data (would require the script to actually select every city on the live site, risking clobbering an in-progress real client record — left as manual Config Manager data entry instead, see below).

- [x] `sync_config_from_website.py` created — attaches to Chrome via `debugger_address=localhost:9222`, reads options via `Select` on the real `<select>` (or falls back to scraping rendered `li.select2-results__option`). Supports two match modes per field (`FIELD_SYNC_TARGETS`): `per_row` (matches each row's other column against a scraped option, case-insensitively via `_best_match`) and `uniform` (finds the one scraped option matching the list's current shared value and applies it to every row — used for Region). Read-only against the website — no clicks/navigation. Fields covered: `approved_by`, `civil_status`, `relationship_bene`, `FA2fund_source`, `region`.

## Part 2 — City-driven Region, Province, and Barangay

Region and province currently aren't real fields — region is a hardcoded literal typed 3x in `assistance-form-new.py` in two different formats (gform vs website), and province comes from the standalone `district_city` dict. Barangay is free text, which risks a mismatch against the website's fixed barangay combobox for a given city.

- [x] `db_config.py`: `extra2` column added to `config_items`, threaded through `get_items`/`insert_item`/`update_item`.
- [x] `db_config.py`: `barangay_list` (kind `"barangays"`) registered in `CONFIG_REGISTRY`, seeded empty.
- [x] `config.py`/seeding: every `list_of_city` row gets `col2 = "NCR (National Capital Region)"` (gform) and `extra2 = "NCR [National Capital Region]"` (website).
- [x] `config_manager.py`: "Region (GForm)" / "Region (Website)" input fields added for the `cities` kind, wired to `col2`/`extra2`.
- [x] `config_manager.py`: City-picker combobox added for the `barangays` kind (replaces free-text city input), wired to `extra`.
- [ ] Barangay data entered per city via Config Manager — **manual data-entry step, not code**; no authoritative barangay list exists in this repo to seed from. Until this is done, the barangay fields fall back to free typing (comboboxes are editable), so the form isn't blocked.
- [x] `assistance-form-new.py`: `client_barangay`/`bene_barangay` are now editable city-filtered comboboxes (repopulated via `on_client_city_changed`/`on_bene_city_changed`); all hardcoded region literals and the `district_city` dict lookups replaced by `self._city_lookup(city)` sourced from `list_of_city` (loaded once in `__init__` via `_load_city_config`/`_load_barangays_by_city`). `init_db()` now also calls `init_db_config`/`seed_from_config_if_empty`/`backfill_city_regions` so this works even if Config Manager was never run first.

## Part 3 — assistance-form-new.py reads all comboboxes from config.db

Previously only city/region/barangay were sourced from `config.db`; every other combobox (gender, civil status, fund source, target sector, mode of release, financial assistance, relationship, approved by, client sub-category) still read from the frozen `config.py` module-level lists, so edits made in Config Manager had no effect on the actual form.

- [x] Added `self._get_list_rows(key)` helper — looks up a config list by key via `get_all_lists()`/`get_items()`, returns `[]` if not found.
- [x] `gender_list`, `target_sector_list`, `mode_of_release`, `financial_assistance_list`, `client_sub_category` comboboxes now populate from `col1` via `_get_list_rows`.
- [x] `civil_status_list`, `fund_source_list`, `relationship_list` — `*_choices`/`*_data_map` now built from db rows (`col2` for display, `{col2: col1}` for the map) instead of the static python pairs.
- [x] `approved_by_list` — combobox and the `self.approved_by_map` dict (used in both the gform and website fill code) now sourced from db instead of the static `approved_by_list` dict.
- [x] Removed the now-unused `from config import ...` lines for all 9 lists (kept only `list_of_city`, still used to populate the City dropdowns).
- Verified against the live `config.db`: all 9 lists resolve correctly, including a `gender_list` row ("Non binary") that only exists in the database, not in `config.py` — confirms the form now actually reflects Config Manager edits instead of the frozen static lists.

**Known residual risk (accepted, not fixed):** saved records in `person-record.db` store each choice as a plain index into these lists (e.g. `"approved_by": 2`). Since these lists are now editable/reorderable via Config Manager, reordering or deleting an item later can shift what an old saved record's index actually points to. This risk already existed for `approved_by_list` before (it was still a positional list), it's just now editable through a UI instead of requiring a code change.

## Part 4 — gender_list becomes key/value (Label -> Value)

`gender_list` was the one remaining `kind="list"` combobox with no second value. The user wants it to work like the other pairs lists: the combobox shows a label, and a separate "Value" is what actually gets submitted, so the submitted value can differ from the displayed label if needed later (e.g. a different string required by the site vs. what's shown to the encoder).

- [x] `config.py`: `gender_list` changed from `["Male", "Female"]` to `[("Male", "Male"), ("Female", "Female")]` (label, value — identical by default).
- [x] `db_config.py`: `CONFIG_REGISTRY` entry changed to `kind="pairs"`, `col1_label="Label"`, `col2_label="Value"`.
- [x] `db_config.py`: added `migrate_gender_to_pairs()` — one-time migration for the already-seeded `gender_list` row: flips `kind`/labels to pairs and backfills `col2 = col1` for any row that predates this (so existing rows default to value == label). Wired into both `config_manager.py` and `assistance-form-new.py`'s init sequence, after `backfill_city_regions()`.
- [x] `assistance-form-new.py`: gender combobox now builds both `self.gender_options` (labels, unchanged combobox population) and `self.gender_map` (`{label: value}`); the 4 automation submission sites (`select2-sex-container`, `select2-b_sex-container`, gform `"SEX"` radio, gform `"i31 i34"` dropdown) now submit `self.gender_map.get(label, label)` instead of the raw combobox text. The `"Female"`/`"male"` UI-logic comparisons (target-sector defaulting) were left comparing against the label, since those are about what's displayed, not what's submitted.
- Verified against the live `config.db`: `gender_list` row correctly flipped to `kind='pairs'`/`Label`/`Value`, and both existing rows backfilled to `col2 = col1`.

Config Manager needed **no code change** for this — `kind="pairs"` was already fully generic there.

## Part 5 — civil_status_list unified to the same Label -> Value contract

`civil_status_list` was already `kind="pairs"` (`Choice`/`Mapped Value`), but the combobox displayed `col2` and the 4 submission sites were inconsistent: client-website looked up `col1` via the map (correct direction), while client-gform and both bene sites (website + gform) submitted the raw combobox text (`col2`) directly, with no map involved. Unified all 4 to the same Label(`col1`)-displayed / Value(`col2`)-submitted contract used for gender — no schema/registry change needed since it was already `kind="pairs"`.

- [x] `assistance-form-new.py`: swapped `self.civil_status_choices` to `col1` (was `col2`) and `self.civil_status_data_map` to `{col1: col2}` (was `{col2: col1}`).
- [x] Client-website site (`select2-civil_status-container`) needed no code change — it already did `data_map[caption]`, which now correctly resolves label -> value with the flipped map.
- [x] Client-gform site (`"CIVIL STATUS"` radio on the "barangay and district" page) changed from submitting the raw `civil_status_caption` to the already-computed `civil_status_name` (mapped value) — this was a real pre-existing inconsistency, now fixed.
- [x] Bene-website (`select2-b_civil_status-container`) and bene-gform (`"CIVIL STATUS"` radio) both changed from raw `self.bene_civil_status.currentText()` to `self.civil_status_data_map.get(caption, caption)`.
- Verified against the live `config.db`: one row's label had already been hand-edited in Config Manager to `"Single (11)"` while its value stayed `"Single"` — confirms the combobox now shows the edited label while all 4 automation sites still submit the correct underlying value (including `"Separated"` -> `"Seperated"`, an intentional-looking typo preserved as the submitted value).

## Part 6 — fund_source_list unified to the same Label -> Value contract

`fund_source_list` was already `kind="pairs"` (`Code`/`Display Name`). While implementing this I found it was actually **not** what Part 1's notes claimed ("website uses col1, already correct") — re-checking the real code showed the website site submitted `col2` (raw combobox text, no map) and only the gform site went through the map (to `col1`). So the field genuinely needed the same fix as civil_status, and Part 1's `sync_config_from_website.py` had the wrong target column for it.

- [x] `assistance-form-new.py`: swapped `self.fund_source_choices` to `col1` (was `col2`) and `self.fund_source_data_map` to `{col1: col2}` (was `{col2: col1}`).
- [x] Website site (`select2-FA2fund_source-container`) changed from submitting the raw `fund_source_caption` to `self.fund_source_data_map.get(caption, caption)` — previously bypassed the map entirely.
- [x] Gform site (`"FUND SOURCE"` radio) needed no code change — already did `data_map[caption]`, now correctly resolves label -> value with the flipped map.
- [x] **Bug fix in `sync_config_from_website.py`**: `FIELD_SYNC_TARGETS["FA2fund_source"]` was targeting `col1` on the theory that the website read `col1` directly and needed no correction — actually backwards, since the website reads `col2`. Changed to target `col2`, matching the corrected code above.
- Verified against the live `config.db`: a row's label had already been hand-edited to `"AKAP Mo"` in Config Manager while its value stayed `"AKAP Fund 2025"` — confirms the combobox shows the edited label while both website and gform submit the correct value.

## Part 7 — target_sector_list becomes key/value (Label -> Value)

Same treatment as gender (Part 4): `target_sector_list` was `kind="list"`, single value, no `col2`.

- [x] `config.py`: `target_sector_list` changed from a flat string list to `[(label, value), ...]` tuples (identical by default).
- [x] `db_config.py`: `CONFIG_REGISTRY` entry changed to `kind="pairs"`, `col1_label="Label"`, `col2_label="Value"`. Generalized the gender migration into `migrate_list_to_pairs(key)`, with `migrate_gender_to_pairs()` and `migrate_target_sector_to_pairs()` as thin wrappers over it — same flip-kind-and-backfill logic, reused instead of copy-pasted. Wired into both apps' init sequences.
- [x] `assistance-form-new.py`: added `self.target_sector_map` (`{label: value}`) alongside the existing `self.target_sector_options`. Updated the 2 website sites (`select2-cl_category-container`, `select2-bene_category-container` — the latter oddly already reused `self.target_sector`, a pre-existing quirk left as-is) and the gform `"CLIENT CATEGORY"` site to submit the mapped value. The `"senior citizens"` special-case override now checks the *label* (`sector_choice`) but overrides the *submitted value* (`sector_value`), preserving the original special-case behavior under the new label/value split. Note: `target_sector_bene` (the beneficiary-side combobox) is only ever used for index-based storage/UI-defaulting, never actually submitted anywhere — left untouched.
- Verified against the live `config.db`: all 8 rows correctly flipped to `kind='pairs'`/`Label`/`Value`, backfilled to `col2 = col1`.

## Part 8 — mode_of_release and financial_assistance_list become key/value (Label -> Value)

Same treatment as gender/target_sector: both were `kind="list"`, single value, no `col2`.

- [x] `config.py`: both changed from flat string lists to `[(label, value), ...]` tuples.
- [x] `db_config.py`: registry entries changed to `kind="pairs"`, `col1_label="Label"`, `col2_label="Value"`; added `migrate_mode_of_release_to_pairs()` / `migrate_financial_assistance_to_pairs()` as thin wrappers over `migrate_list_to_pairs()`. Wired into both apps' init sequences.
- [x] `assistance-form-new.py`: added `self.mode_release_map` and `self.financial_assist_map`.
  - `mode_of_release` is directly submitted in 2 places (gform `"MODE OF RELEASE"` radio, website `select2-FA2mode_of_asssitance}-container`) — both now submit the mapped value instead of the raw label.
  - `financial_assistance_list` is **never submitted directly** anywhere — it's only ever used as a match-case key (`match self.financial_assist.currentText().lower(): case "medical": ...`) to select one of several *hardcoded* output strings. Found a real latent fragility here: once this list becomes label-editable via Config Manager, renaming a label (e.g. "Medical" -> something else) would have silently broken every `match`/`case` block, since they compared against the displayed label directly. Fixed by matching against the mapped **value** instead of the label at all 4 match sites, so the label can be freely renamed in Config Manager without breaking the case dispatch, as long as the value stays a recognized key.
- Verified against the live `config.db`: both lists correctly flipped to `kind='pairs'`/`Label`/`Value`, all rows backfilled to `col2 = col1`.

## Part 9 — approver_list removed (dead config)

Confirmed via full-file grep that `approver_list` ("Approver") was never actually consumed anywhere in `assistance-form-new.py` — no combobox, no automation submission. The only match for "approver" in that file is an unrelated `case "approver":` page-title branch that fills the social worker (`assessed_by`) field, not this list. Since it was dead config with no consumer, removed it entirely rather than leaving an orphaned category in Config Manager.

- [x] `config.py`: deleted the `approver_list = {...}` definition.
- [x] `db_config.py`: removed the `("approver_list", ...)` entry from `CONFIG_REGISTRY` and the now-unused import. Added `delete_list_by_key(key)` (deletes a list's `config_items` then its `config_lists` row, no-op if already gone) and `remove_approver_list()` as a thin wrapper — mirrors the `migrate_*` wrapper pattern. Wired into both apps' init sequences (last step, after the migrations).
- Verified against the live `config.db`: `approver_list`'s `config_lists` row and all its `config_items` rows are gone; `get_all_lists()` no longer includes it.

## Part 10 — Mode of Admission added to config (new list, Label -> Value)

Mode of Admission was previously hardcoded directly on the combobox (`addItems(["On-site", "Walk-in", "Referral"])`), not sourced from config at all — the only field in the form that wasn't config-driven in some form. Added as a brand-new list, no migration needed since it never existed in `config.db` before (`seed_from_config_if_empty()` just inserts it fresh).

- [x] `config.py`: added `mode_of_admission_list = [("On-site","On-site"), ("Walk-in","Walk-in"), ("Referral","Referral")]`.
- [x] `db_config.py`: registered `("mode_of_admission_list", "Mode of Admission", "pairs", "Label", "Value", mode_of_admission_list)` in `CONFIG_REGISTRY`.
- [x] `assistance-form-new.py`: combobox now populates from `self.mode_of_admission_options`/`self.mode_of_admission_map` via `_get_list_rows`, same as every other pairs list.
- [x] Website site (`select2-mode_of_admission-container`) now submits the mapped value instead of the raw label.
- [x] **Fixed a real bug** (confirmed with the user first): the gform site (`"MODE OF ADMISSION"` radio) previously ignored the combobox entirely and always submitted the hardcoded literal `"WALK-IN"` regardless of what was actually selected. Now submits the mapped value from the actual selection, consistent with the website site.
- Verified against the live `config.db`: list seeded fresh with all 3 rows, `kind='pairs'`, `Label`/`Value` columns as expected.

## Part 11 — Social Worker: full_name + dual gform/website value (db_worker.py / social_worker_manager.py only)

The user explicitly asked to apply the dual gform/website-value pattern to social workers, and to trim the 3 separate name fields (Last/First/Middle) down to a single Full Name field — **but not to touch `assistance-form-new.py` yet**. So this is a deliberately incomplete, two-phase change: the storage layer and the management UI are done now; `assistance-form-new.py`'s consumption of worker data is untouched and will need a follow-up pass.

- [x] `db_worker.py`: rebuilt the `worker` table schema from `(sw_lname, sw_fname, sw_mname, search_thru_first_name)` to `(full_name, gform_value, website_value, search_thru_first_name)`. `init_db_worker()` now runs `_migrate_names_to_full_name()`, which rebuilds the table (SQLite can't easily drop/retype columns) and computes defaults for existing rows from the *exact* formatting `assistance-form-new.py` used to compute on the fly: gform default mirrors `f'{capwords(lname)}, {capwords(fname)} {mname_initial}.'`; website default mirrors the `thru_firstname` branching logic from the `case "approver":` block (fname-first order when `search_thru_first_name` is set, lname-first otherwise). Backed up `worker.db` to `worker.db.bak_before_fullname_migration` before running this against the real file (it does a real `DROP TABLE`).
- [x] Renamed `get_worker_id(lastname, firstname, middlename)` to `get_worker_by_full_name(full_name)`, matching the new single-field schema.
- [x] Added a **compatibility shim** `get_worker_id(sw_lname, sw_fname, sw_mname)` in `db_worker.py` that reconstructs the equivalent full_name and calls `get_worker_by_full_name` — purely so `assistance-form-new.py`'s existing `from db_worker import get_all_workers, get_worker_id` import doesn't hard-crash at startup. Verified it still resolves a pre-migration lookup (e.g. `get_worker_id('AYALA','CZARINA PEARL','COPELAND')`) to the correct worker id.
- [x] `social_worker_manager.py`: replaced the Last/First/Middle name row with one "Full Name" field, added "GForm Value" and "Website Value" fields (same UI pattern as Config Manager's dual-value fields), updated the table to 5 columns (ID, Full Name, GForm Value, Website Value, Thru Firstname), and updated all CRUD calls to the new signatures.
- Verified against the live `worker.db`: all 27 existing workers migrated correctly (e.g. thru-firstname workers got `"FNAME MNAME LNAME"` website values, non-thru workers got `"LNAME FNAME MNAME"`), and the compatibility shim resolves old-style lookups to the right id.

**Known incomplete state (by design, per explicit instruction):** `assistance-form-new.py` still reads `get_all_workers()` rows as `(_id, lname, fname, mname, _thru)` (now actually `(_id, full_name, gform_value, website_value, _thru)`) to build its social-worker combobox choices (`f"{fname}, {mname}, {lname}"`) and re-parses the selected combobox text by splitting on commas to call the old-shaped lookup. Since `gform_value` itself contains a comma (`"Lastname, Firstname M."`), the combobox will show **garbled text** and the reverse-parsing will not reliably find the right worker until `assistance-form-new.py` is updated to use `full_name`/`gform_value`/`website_value` directly instead of parsing 3 name parts back out of a combobox string. Flagged to the user; follow-up task, not done here.

## Part 12 — search_thru_first_name removed entirely

Follow-up to Part 11: the user asked to remove `search_thru_first_name` from both the Social Worker UI and the database.

- [x] `db_worker.py`: `CREATE TABLE IF NOT EXISTS` target schema (for brand-new installs) dropped the column. Added `_migrate_drop_thru_firstname()` — same rebuild-the-table pattern as the other migrations — to strip it from an already-migrated `worker` table (e.g. the one Part 11 just produced on the real `worker.db`). Backed up to `worker.db.bak_before_drop_thru_firstname` first. `get_all_workers`/`get_worker_by_full_name`/`get_worker_by_id`/`insert_worker`/`update_worker` all updated to drop the parameter/column.
- [x] `social_worker_manager.py`: removed the "Search thru Firstname" checkbox, its table column, and all read/write references.
- [x] **Crash fix in `assistance-form-new.py`** (confirmed with the user first, since the earlier instruction was to leave that file alone): `on_selection_worker` read `data_worker[4]` for the thru-firstname flag, which no longer exists in the tuple once the column is dropped — that's an `IndexError` on every worker selection, not just stale/garbled data like the rest of Part 11's known gap. Removed just that one line (`self.thru_firstname.setChecked(bool(data_worker[4]))`); the `self.thru_firstname` checkbox and its other uses (page-fill logic, save/load) are untouched and still work exactly as before, since the widget itself still exists — only the auto-check-from-worker-data behavior is gone.
- Verified against the live `worker.db`: `search_thru_first_name` column confirmed gone via `PRAGMA table_info`, all 27 rows preserved with correct `full_name`/`gform_value`/`website_value`.

## Part 13 — assistance-form-new.py updated to consume the new social worker schema

Closes the Part 11 gap: `assistance-form-new.py` now fully consumes `full_name`/`gform_value`/`website_value` directly instead of the old 3-part name reconstruction, and the `thru_firstname` UI/logic is trimmed out of this file too (not just the checkbox line patched in Part 12).

- [x] Import changed to `get_worker_by_full_name` (dropped the `get_worker_id` compatibility shim usage — it still exists in `db_worker.py` but nothing calls it anymore).
- [x] Social worker combobox now shows `full_name` directly (`self.social_worker_choices = [full_name for (_id, full_name, _gform, _website) in self.social_worker_list]`) instead of the garbled `f"{fname}, {mname}, {lname}"` reconstruction.
- [x] Removed the 3 hidden `sw_lname`/`sw_fname`/`sw_mname` `QLineEdit` fields and the `thru_firstname` checkbox entirely (they were only ever used to shuttle the now-obsolete 3-part decomposition around).
- [x] Removed `on_selection_worker`'s comma-splitting reverse-parse entirely; added `self._selected_worker()` — returns `(id, full_name, gform_value, website_value)` for whatever's currently selected in the combobox by index, no parsing needed.
- [x] All 3 automation submission sites now pull directly from `_selected_worker()`: the website site (`select2-assessed_by-container`, in the `case "approver":` branch) uses `worker[3]` (website_value); both gform sites (`"i157 i160"` dropdown in `on_fill_crims_offline`, `"i39 i40"` text field in `on_fill_crims_mov`) use `worker[2]` (gform_value) — replacing all the on-the-fly `capwords`/`thru_firstname` name-order construction.
- [x] Persistence: kept `db_new_person.py`'s schema and column order **untouched** (avoided a risky renumbering of ~40 positional `row[N]` indices elsewhere in the file) — the existing `sw_lname` column now just stores the worker's `full_name` text (renamed to `"sw_full_name"` at the Python/dict level only), and `sw_fname`/`sw_mname` are passed `""` going forward. Saved/loaded records now match the selected worker by `full_name` string lookup (`self.social_worker_choices.index(...)`) instead of by the old 3-part `get_worker_id` matching.
- [x] Removed the now-unused `import string` (its only use was the capwords-based gform name construction just removed).
- Verified: full-file compiles and `ast.parse`s cleanly; ran the actual data flow (`get_all_workers`/`get_worker_by_full_name`, index-based `_selected_worker` lookup, `choices.index(...)` reverse lookup) against the real `worker.db` and confirmed correct `gform_value`/`website_value` resolution.

**Residual, accepted tradeoff:** old person records saved before this change have their `sw_lname` column populated with an actual last name (not a full_name), so `self.social_worker_choices.index(person["sw_full_name"])` won't find a match for those and will fall back to no worker selected (`-1`) — the encoder just needs to reselect. New/updated records don't have this problem.

## Part 14 — Target Sector split into GForm Value + Website Value (reusable `dual_pairs` kind)

Target Sector had one "Value" used identically for both destinations. Generalized the dual-value pattern that only `list_of_city`'s Region had before into a reusable `kind="dual_pairs"`, rather than a Target-Sector-only special case, per the user's choice.

- [x] `config.py`: `target_sector_list` changed from `(label, value)` pairs to `(label, gform_value, website_value)` triples, both new values defaulting to the old value.
- [x] `db_config.py`: generalized `_pairs_for()` to always return `(col1, col2, extra2)` triples instead of `(col1, col2)` pairs (every existing kind just gets a trailing `None`; `dual_pairs` unpacks real triples). `seed_from_config_if_empty()`'s insert loop updated to match. Registry entry changed to `kind="dual_pairs"`, `col2_label="GForm Value"`. Added `migrate_target_sector_to_dual_pairs()` (same targeted-`UPDATE` style as `backfill_city_regions()`) to flip the already-seeded row's `kind`/`col2_label` and backfill `extra2 = col2` for existing rows. Wired into both apps' init sequences.
- [x] `config_manager.py`: generalized the Cities-only dual-value UI — `is_dual_value = kind in ("cities", "dual_pairs")` now controls the Website-Value field and the table's 4th column for *either* kind, with the label text switching between `"Region (Website)"` (cities) and `"Website Value"` (dual_pairs). `_extra2_value()` updated the same way. `_col2_value()`/`load_items`/`on_select_item`/`clear_form` needed no changes — already generic.
- [x] `assistance-form-new.py`: replaced the single `target_sector_map` with `target_sector_gform_map` and `target_sector_website_map` (from `col2`/`extra2` respectively). The 2 website sites (`select2-cl_category-container`, `select2-bene_category-container`) now use the website map; the gform `"CLIENT CATEGORY"` site (with its `"senior citizens"` override, unchanged) now uses the gform map.
- Verified against the live `config.db`: migration correctly flips `kind`/`col2_label` and backfills `extra2 = col2` for all 8 rows; both new maps resolve correctly and are identical right after migration (as expected, since both default to the old shared value). Confirmed Cities' existing "Region (GForm)"/"Region (Website)" wording is unaffected by the generalization (no regression).

## Part 15 — Approved By migrated to the same `dual_pairs` shape

`approved_by_list` was `kind="dict"` (Short Name -> Full Name), where `col1` (Short Name) doubled as *both* the display label *and* the gform submission value (the website used `col2`/Full Name; the gform site fed the raw combobox text — `col1` — directly into the radio button, ignoring the dict value entirely). Migrated it onto the same reusable `dual_pairs` shape as Target Sector, decoupling the label from both submission values — the payoff of building Part 14 as a generic pattern: **zero `config_manager.py` changes were needed**, since it was already generic for any `dual_pairs` list.

- [x] `config.py`: `approved_by_list` changed from a `{short_name: full_name}` dict to `[(label, gform_value, website_value), ...]` triples — `label` and `gform_value` both start as the old short name, `website_value` as the old full name.
- [x] `db_config.py`: registry entry changed to `kind="dual_pairs"`, `col2_label="GForm Value"`. Added `migrate_approved_by_to_dual_pairs()` — unlike Target Sector's migration (which only *added* `extra2`), this one reshuffles existing data: keeps `col1` as the label (unchanged text), sets new `col2` (GForm Value) = old `col1`, and new `extra2` (Website Value) = old `col2`. This exactly preserves what each destination already received — it just stops `col1` from doing double duty. Wired into both apps' init sequences.
- [x] `assistance-form-new.py`: split into `approved_by_gform_map` and `approved_by_website_map` (combobox population via a new `approved_by_options` list, unchanged values since `col1` didn't change). The website site (`select2-approved_by-container`) now uses the website map (unchanged behavior — it already used the dict value). The gform site (bare `setGFormRadioButton(driver, "", ...)`) now uses the gform map instead of the raw combobox text `selected_key` — this is the one site whose *code path* changed, though the *submitted value* is identical immediately after migration since `gform_map[label] == label` by default.
- Verified against the live `config.db`: migration correctly reshuffles all 5 rows (`col1` unchanged, `col2` = old short name, `extra2` = old full name); both new maps resolve to exactly the same values the old code was already producing pre-migration.

## Open questions
- Whether `district_city` in `config.py` gets deleted once its values are fully migrated into `list_of_city`'s `extra` column, or kept around as a fallback/reference.
- Whether to add a delete/reorder confirmation in Config Manager warning about the index-based storage in `person-record.db`, given Part 3 makes every list editable now, not just the cities/barangays.
- Whether `db_new_person.py`'s `sw_lname`/`sw_fname`/`sw_mname` columns should eventually be properly renamed to a single `sw_full_name` column (real schema migration) instead of the Part 13 workaround of repurposing `sw_lname` in place — deferred because it would require renumbering every other positional `row[N]` read in `assistance-form-new.py`.
- Whether `client_sub_category` (still `kind="dict"`, Key/Value) and `relationship_list`/`civil_status_list` (still `kind="pairs"`, single mapped value used for both destinations per Part 5/Part 6's unification) should eventually move to `dual_pairs` too, now that the reusable pattern exists.
