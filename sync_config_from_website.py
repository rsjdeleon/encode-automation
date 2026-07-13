"""Sync gform/website dual-value config lists against the live CRIMS website or
the Google Form.

By default, reads the real options out of a select2-backed dropdown on the
CRIMS site and uses them to correct the website-facing column of the matching
list — a config.db list for most fields, or the worker table (Social Worker)
for "assessed_by". Pass "gform" as an extra argument to instead read a Google
Form dropdown and correct the GForm-facing column — currently only supported
for "assessed_by" (Social Worker); see GFORM_SYNC_TARGETS. Read-only either
way: it never clicks Next/Submit or changes any field, it only reads option
text. Requires Chrome already running with --remote-debugging-port=9222,
logged in, and sitting on the page/step that contains the target field (the
CRIMS website page, or the Google Form page, matching whichever source you
pass).

Pass "add-missing" as an extra argument to also insert scraped options that
matched no existing row as new rows (every field on the new row defaults to
the scraped value; refine it afterward via the normal CRUD screen), instead of
only reporting them as candidates. Off by default — inserting is more
consequential than correcting an existing value, so it's opt-in. Only applies
to "per_row"/"self" fields — no current target uses "uniform" (a single value
shared by every existing row, with no per-entity row to add).

The "barangay" field needs a --city="CITY NAME" argument: the live Barangay
dropdown only shows options for whichever City is currently selected on that
page, so a scrape only ever reflects one city's worth of barangays — pass the
same city that's currently selected on the live page. Every other field
ignores --city.

Usage:
    python sync_config_from_website.py <field_id> [gform] [add-missing] [--city="CITY NAME"]

Example:
    python sync_config_from_website.py approved_by
    python sync_config_from_website.py assessed_by
    python sync_config_from_website.py assessed_by gform
    python sync_config_from_website.py assessed_by gform add-missing
    python sync_config_from_website.py barangay --city="CITY OF MALABON"
    python sync_config_from_website.py barangay --city="CITY OF MALABON" add-missing
"""

import difflib
import sys
import time

from selenium import webdriver
from selenium.common import NoSuchElementException
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select

from db_config import get_all_lists, get_items, update_item, insert_item
from db_worker import get_all_workers, update_worker, insert_worker

# field_id -> (config list key, column being corrected, mode)
# "per_row": the field has one option per config row, matched by a *different*
#            sibling column that shares the scraped text's format (e.g. each
#            approver's Label is close enough to their scraped GForm Value).
# "uniform": every row shares one value with no independent per-row identity —
#            the best-matching scraped option is applied to every row. (Region
#            used to be the example here when it lived as a duplicated column on
#            every list_of_city row; now that it's its own region_list row, it
#            uses "self" instead. No current target needs "uniform", but it's
#            kept for a future field shaped that way.)
# "self":    like "per_row" but matched against the row's own current value in the
#            target column, not a sibling column — needed when no sibling column
#            is close enough in format/word-order (e.g. Social Worker's full_name
#            is "Last, First MI." while website_value is "First MI. Last").
#
# "worker_list" is a sentinel: Social Worker records live in a separate `worker`
# table (db_worker.py), not config_lists/config_items, so it's adapted to the
# same (id, col1, col2, extra, extra2) row shape in sync_field() below.
FIELD_SYNC_TARGETS = {
    "approved_by": ("approved_by_list", "col2", "per_row"),
    "civil_status": ("civil_status_list", "col2", "per_row"),
    "relationship_bene": ("relationship_list", "col2", "per_row"),
    "FA2fund_source": ("fund_source_list", "col2", "per_row"),
    "region": ("region_list", "extra2", "self"),
    "city_muni": ("list_of_city", "extra2", "self"),
    "barangay": ("barangay_list", "extra2", "self"),
    "assessed_by": ("worker_list", "extra2", "self"),
}

# field_id -> (GForm dropdown pk_id, target column for the GForm-corrected value).
# Only fields with a confirmed, unambiguous GForm *dropdown* are listed here — the
# other fields' GForm equivalents are radio-button groups (a different, not yet
# built, scraping technique).
GFORM_SYNC_TARGETS = {
    "assessed_by": ("i157 i160", "col2"),
}

MATCH_CUTOFF = 0.6

COLUMN_INDEX = {"col1": 1, "col2": 2, "extra": 3, "extra2": 4}  # index into get_items() row tuple


def _row_with_override(row, target_col, new_value):
    """Return the (col1, col2, extra, extra2) update_item args for `row` with target_col replaced."""
    values = list(row[1:])  # [col1, col2, extra, extra2]
    values[COLUMN_INDEX[target_col] - 1] = new_value
    return values


def _worker_rows_as_config_rows():
    """Adapt worker table rows (id, full_name, gform_value, website_value) into the
    (id, col1, col2, extra, extra2) shape sync_per_row/sync_uniform expect. `extra`
    has no worker equivalent, so it's always None."""
    return [
        (worker_id, full_name, gform_value, None, website_value)
        for worker_id, full_name, gform_value, website_value in get_all_workers()
    ]


def _update_worker_row(item_id, col1, col2, _extra, extra2):
    """update_item-compatible adapter that writes back to the worker table
    (full_name, gform_value, website_value); `extra` has no worker equivalent
    and is discarded."""
    update_worker(item_id, col1, col2, extra2)


def _add_missing_rows(list_key, list_id, values, extra=None):
    """Insert each unmatched scraped value as a new row, with every relevant
    field defaulted to that same value — admin refines formatting afterward via
    the normal CRUD screen, same convention already used when seeding new
    province/city rows elsewhere in the app. `extra` is the row's link column
    (e.g. barangay's city), left None for targets with no such link."""
    added = []
    for value in values:
        if list_key == "worker_list":
            insert_worker(value, value, value)
        else:
            insert_item(list_id, value, value, extra, value)
        added.append(value)
    return added


def _best_match(reference, candidates):
    """Case-insensitive close-match lookup that returns the original-cased candidate."""
    reference = (reference or "").lower()
    by_lower = {c.lower(): c for c in candidates}
    match = difflib.get_close_matches(reference, by_lower.keys(), n=1, cutoff=MATCH_CUTOFF)
    return by_lower[match[0]] if match else None


def attach_to_chrome():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.debugger_address = "localhost:9222"
    return webdriver.Chrome(options=chrome_options)


def scrape_options(driver, field_id):
    """Return the list of option texts for a select2-backed field, real <select> first."""
    try:
        select_el = driver.find_element(By.ID, field_id)
        options = [opt.text.strip() for opt in Select(select_el).options if opt.text.strip()]
        if options:
            return options
    except NoSuchElementException:
        pass

    # Fallback: open the rendered combobox and scrape the select2 result list.
    combobox = driver.find_element(
        By.XPATH, f"//span[@role='combobox' and @aria-labelledby='select2-{field_id}-container']"
    )
    combobox.click()
    time.sleep(0.5)
    options = [
        li.text.strip()
        for li in driver.find_elements(By.XPATH, "//li[contains(@class, 'select2-results__option')]")
        if li.text.strip()
    ]
    combobox.click()  # close it back up
    return options


def scrape_gform_dropdown_options(driver, pk_id):
    """Return the list of option texts for a Google Form dropdown field.

    Mirrors the locator logic assistance-form-new.py's setGFormDropDown() already
    uses to *select* an option, so scraping stays consistent with how the
    automation actually reads the form: open the div[role=listbox] identified by
    aria-labelledby=pk_id, read data-value off each div[role=option].
    """
    dropdown = driver.find_element(By.XPATH, f"//div[@role='listbox' and @aria-labelledby='{pk_id}']")
    dropdown.click()
    time.sleep(0.5)
    options = [
        opt.get_attribute("data-value").strip()
        for opt in driver.find_elements(By.XPATH, "//div[@role='option']")
        if opt.get_attribute("data-value") and opt.get_attribute("data-value").strip()
    ]
    dropdown.click()  # close it back up
    return options


def sync_per_row(rows, scraped, target_col, update_row=update_item):
    """Match each row's other column against scraped options; update target_col per-row.

    "Other column" is col1 (the row's primary label) unless target_col IS col1, in
    which case col2 is used instead — this covers target_col values beyond col1/col2
    too (e.g. extra2), which always match by col1.
    """
    other_col = "col1" if target_col != "col1" else "col2"
    remaining_scraped = list(scraped)
    unmatched_rows = []
    updated = []

    for row in rows:
        item_id, col1, col2, extra, extra2 = row
        key_value = col1 if other_col == "col1" else col2
        current_value = row[COLUMN_INDEX[target_col]]
        scraped_value = _best_match(key_value, remaining_scraped)
        if scraped_value is None:
            unmatched_rows.append(key_value)
            continue

        remaining_scraped.remove(scraped_value)
        if scraped_value == current_value:
            continue

        update_row(item_id, *_row_with_override(row, target_col, scraped_value))
        updated.append((key_value, current_value, scraped_value))

    return updated, unmatched_rows, remaining_scraped


def sync_uniform(rows, scraped, target_col, update_row=update_item):
    """Find the scraped option matching the current shared value, and apply it to every row."""
    if not rows:
        return [], [], scraped

    reference = rows[0][COLUMN_INDEX[target_col]]
    scraped_value = _best_match(reference, scraped)
    if scraped_value is None:
        return [], [reference], scraped

    remaining_scraped = [v for v in scraped if v != scraped_value]

    updated = []
    for row in rows:
        item_id = row[0]
        current_value = row[COLUMN_INDEX[target_col]]
        if current_value == scraped_value:
            continue
        update_row(item_id, *_row_with_override(row, target_col, scraped_value))
        updated.append((f"row {item_id}", current_value, scraped_value))

    return updated, [], remaining_scraped


def sync_self(rows, scraped, target_col, update_row=update_item):
    """Match each row's own current target_col value against scraped options.

    Unlike sync_per_row (which matches via a *different*, sibling column — fine
    when that column shares the scraped text's format, e.g. approved_by's Label),
    this matches a row against its own prior value in target_col. Needed when no
    sibling column is close enough in format/word-order to match reliably — e.g.
    Social Worker's full_name is stored "Last, First MI." while the scraped
    website options (and the existing website_value) are "First MI. Last".
    """
    remaining_scraped = list(scraped)
    unmatched_rows = []
    updated = []

    for row in rows:
        item_id = row[0]
        current_value = row[COLUMN_INDEX[target_col]]
        scraped_value = _best_match(current_value, remaining_scraped)
        if scraped_value is None:
            unmatched_rows.append(current_value)
            continue

        remaining_scraped.remove(scraped_value)
        if scraped_value == current_value:
            continue

        update_row(item_id, *_row_with_override(row, target_col, scraped_value))
        updated.append((f"row {item_id}", current_value, scraped_value))

    return updated, unmatched_rows, remaining_scraped


def sync_field(field_id, source="website", log=print, add_missing=False, city=None):
    """Run a sync. `log` receives one line of text at a time (defaults to print,
    for CLI use); pass a different callable — e.g. a Qt signal's .emit — to
    route output elsewhere, such as a GUI log panel. `add_missing` (opt-in,
    default False) inserts scraped options that matched no existing row as new
    rows, instead of only reporting them as candidates — only meaningful for
    "per_row"/"self" modes; "uniform" (Region) has no per-entity row to add.
    `city` is required for the "barangay" target (see below) and ignored by
    every other target."""
    if field_id not in FIELD_SYNC_TARGETS:
        log(f"Unknown field id {field_id!r}. Known fields: {', '.join(FIELD_SYNC_TARGETS)}")
        return

    list_key, website_target_col, mode = FIELD_SYNC_TARGETS[field_id]

    if source == "gform":
        if field_id not in GFORM_SYNC_TARGETS:
            log(f"GForm sync not supported yet for {field_id!r}. Supported: {', '.join(GFORM_SYNC_TARGETS)}")
            return
        scrape_pk_id, target_col = GFORM_SYNC_TARGETS[field_id]
    else:
        scrape_pk_id, target_col = field_id, website_target_col

    if list_key == "worker_list":
        col1_label, col2_label = "Full Name", "GForm Value"
        rows = _worker_rows_as_config_rows()
        update_row = _update_worker_row
        list_id = None
    else:
        lists_by_key = {key: (list_id, col1_label, col2_label) for list_id, key, _, _, col1_label, col2_label in get_all_lists()}
        if list_key not in lists_by_key:
            log(f"Config list {list_key!r} not found in config.db.")
            return
        list_id, col1_label, col2_label = lists_by_key[list_key]
        rows = get_items(list_id)  # (id, col1, col2, extra, extra2)
        update_row = update_item

    if list_key == "barangay_list":
        # The live Barangay dropdown only shows options for whichever City is
        # currently selected on that page, so a scrape only ever reflects one
        # city's worth of barangays — the caller must say which one, rather
        # than the tool guessing from an unrelated column.
        if not city:
            log('City is required for barangay sync — pass city="CITY NAME" '
                "(the same city currently selected on the live page).")
            return
        rows = [row for row in rows if row[3] and row[3].strip().upper() == city.strip().upper()]

    driver = attach_to_chrome()
    try:
        if source == "gform":
            scraped = scrape_gform_dropdown_options(driver, scrape_pk_id)
        else:
            scraped = scrape_options(driver, scrape_pk_id)
    finally:
        driver.quit()

    if not scraped:
        log(f"No options scraped for field {field_id!r} (source={source}) — is the right page open?")
        return

    if mode == "per_row":
        updated, unmatched_rows, remaining_scraped = sync_per_row(rows, scraped, target_col, update_row)
    elif mode == "self":
        updated, unmatched_rows, remaining_scraped = sync_self(rows, scraped, target_col, update_row)
    else:
        updated, unmatched_rows, remaining_scraped = sync_uniform(rows, scraped, target_col, update_row)

    added = []
    if add_missing and mode in ("per_row", "self") and remaining_scraped:
        row_extra = city if list_key == "barangay_list" else None
        added = _add_missing_rows(list_key, list_id, remaining_scraped, extra=row_extra)
        remaining_scraped = []

    city_suffix = f", city={city!r}" if list_key == "barangay_list" else ""
    log(f"=== {list_key} ({col1_label}/{col2_label}) — field {field_id!r} [{mode}, source={source}{city_suffix}] ===")
    if updated:
        log(f"Updated {len(updated)} row(s):")
        for key_value, old, new in updated:
            log(f"  {key_value}: {old!r} -> {new!r}")
    else:
        log("No rows needed updating.")

    if unmatched_rows:
        log(f"{len(unmatched_rows)} existing value(s) had no matching scraped option (needs manual attention):")
        for key_value in unmatched_rows:
            log(f"  {key_value}")

    if added:
        log(f"Added {len(added)} new row(s):")
        for value in added:
            log(f"  {value}")

    if mode in ("per_row", "self") and remaining_scraped:
        log(f"{len(remaining_scraped)} scraped option(s) matched no existing row (candidates to add manually):")
        for value in remaining_scraped:
            log(f"  {value}")


if __name__ == "__main__":
    USAGE = f'Usage: python {sys.argv[0]} <field_id> [gform] [add-missing] [--city="CITY NAME"]'

    if len(sys.argv) < 2:
        print(USAGE)
        print(f"Known fields: {', '.join(FIELD_SYNC_TARGETS)}")
        sys.exit(1)

    field_id = sys.argv[1]
    city_arg = None
    flag_args = set()
    for arg in sys.argv[2:]:
        if arg.startswith("--city="):
            city_arg = arg[len("--city="):]
        else:
            flag_args.add(arg)

    unknown_args = flag_args - {"gform", "add-missing"}
    if unknown_args:
        print(f"Unknown argument(s): {', '.join(unknown_args)}")
        print(USAGE)
        print(f"Known fields: {', '.join(FIELD_SYNC_TARGETS)}")
        print(f"Fields supporting the optional 'gform' source: {', '.join(GFORM_SYNC_TARGETS)}")
        sys.exit(1)

    sync_field(
        field_id,
        source="gform" if "gform" in flag_args else "website",
        add_missing="add-missing" in flag_args,
        city=city_arg,
    )
