import sqlite3

from config import (
    gender_list, mode_of_admission_list, civil_status_list, fund_source_list,
    target_sector_list, mode_of_release, financial_assistance_list,
    relationship_list, list_of_city, district_city, approved_by_list,
    client_sub_category, region_list, province_list,
)

DB_NAME_CONFIG = 'config.db'

# (key, label, kind, col1_label, col2_label, source_data)
# kind: 'list' | 'pairs' | 'dual_pairs' | 'dict' | 'set' | 'cities' | 'barangays' | 'provinces'
# 'dual_pairs': like 'pairs' but with a 3rd value (Website Value, stored in extra2),
# independent from col2 (GForm Value) — source_data is a list of (label, gform_value, website_value).
CONFIG_REGISTRY = [
    ("gender_list", "Gender", "dual_pairs", "Label", "GForm Value", gender_list),
    ("mode_of_admission_list", "Mode of Admission", "pairs", "Label", "Value", mode_of_admission_list),
    ("civil_status_list", "Civil Status", "dual_pairs", "Choice", "GForm Value", civil_status_list),
    ("fund_source_list", "Fund Source", "dual_pairs", "Code", "GForm Value", fund_source_list),
    ("target_sector_list", "Target Sector", "dual_pairs", "Label", "GForm Value", target_sector_list),
    ("mode_of_release", "Mode of Release", "dual_pairs", "Label", "GForm Value", mode_of_release),
    ("financial_assistance_list", "Financial Assistance", "dual_pairs", "Label", "GForm Value", financial_assistance_list),
    ("relationship_list", "Relationship", "dual_pairs", "Choice", "GForm Value", relationship_list),
    # region_list/province_list must precede list_of_city: cities link to a province
    # by id at seed time, so the province rows need to already exist.
    ("region_list", "Regions", "dual_pairs", "Region", "GForm Value", region_list),
    ("province_list", "Provinces", "provinces", "Province", "GForm Value", province_list),
    ("list_of_city", "Cities", "cities", "City", "GForm Value", list_of_city),
    ("approved_by_list", "Approved By", "dual_pairs", "Label", "GForm Value", approved_by_list),
    ("client_sub_category", "Client Sub-Category", "dual_pairs", "Key", "GForm Value", client_sub_category),
    ("barangay_list", "Barangays", "barangays", "Barangay", "GForm Value", []),
]


def init_db_config():
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS config_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                key TEXT UNIQUE NOT NULL,
                label TEXT NOT NULL,
                kind TEXT NOT NULL,
                col1_label TEXT NOT NULL,
                col2_label TEXT
            )
        ''')
        c.execute('''
            CREATE TABLE IF NOT EXISTS config_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                list_id INTEGER NOT NULL REFERENCES config_lists(id),
                sort_order INTEGER NOT NULL,
                col1 TEXT NOT NULL,
                col2 TEXT,
                extra TEXT,
                UNIQUE(list_id, sort_order)
            )
        ''')
        c.execute("PRAGMA table_info(config_items)")
        existing_columns = {row[1] for row in c.fetchall()}
        if "extra2" not in existing_columns:
            c.execute("ALTER TABLE config_items ADD COLUMN extra2 TEXT")
        conn.commit()


def _pairs_for(kind, source_data):
    """Normalize each registry entry's source data into an ordered list of (col1, col2, extra2) triples."""
    if kind == "list":
        return [(v, None, None) for v in source_data]
    if kind == "set":
        return [(v, None, None) for v in source_data]
    if kind == "pairs":
        return [(a, b, None) for a, b in source_data]
    if kind == "dual_pairs":
        return [(a, b, c) for a, b, c in source_data]
    if kind == "dict":
        return [(k, v, None) for k, v in source_data.items()]
    if kind == "cities":
        return [(a, b, c) for a, b, c in source_data]
    if kind == "barangays":
        return [(v, None, None) for v in source_data]
    if kind == "provinces":
        return [(a, b, c) for a, b, c in source_data]
    raise ValueError(f"Unknown kind: {kind}")


def _first_region_item_id(c, list_ids_by_key):
    """Look up the config_items.id of the first region_list row, so provinces can
    link to a region by id rather than by (renameable) label text. Checks the
    list just inserted in this same seeding pass first, falling back to querying
    an already-existing region_list."""
    region_list_id = list_ids_by_key.get("region_list")
    if region_list_id is None:
        c.execute("SELECT id FROM config_lists WHERE key = 'region_list'")
        row = c.fetchone()
        if not row:
            return None
        region_list_id = row[0]
    c.execute("SELECT id FROM config_items WHERE list_id = ? ORDER BY sort_order ASC LIMIT 1", (region_list_id,))
    row = c.fetchone()
    return row[0] if row else None


def _province_item_id_by_label(c, list_ids_by_key, label):
    """Look up the config_items.id of the province_list row whose col1 == label, so
    cities can link to a province by id rather than by (renameable) label text.
    Checks the list just inserted in this same seeding pass first, falling back to
    querying an already-existing province_list. Returns None if label is None or
    no matching province row exists."""
    if label is None:
        return None
    province_list_id = list_ids_by_key.get("province_list")
    if province_list_id is None:
        c.execute("SELECT id FROM config_lists WHERE key = 'province_list'")
        row = c.fetchone()
        if not row:
            return None
        province_list_id = row[0]
    c.execute("SELECT id FROM config_items WHERE list_id = ? AND col1 = ?", (province_list_id, label))
    row = c.fetchone()
    return row[0] if row else None


def _city_item_id_by_label(c, list_ids_by_key, label):
    """Look up the config_items.id of the list_of_city row whose col1 == label, so
    barangays can link to a city by id rather than by (renameable) label text.
    Checks the list just inserted in this same seeding pass first, falling back to
    querying an already-existing list_of_city. Returns None if label is None or
    no matching city row exists."""
    if label is None:
        return None
    city_list_id = list_ids_by_key.get("list_of_city")
    if city_list_id is None:
        c.execute("SELECT id FROM config_lists WHERE key = 'list_of_city'")
        row = c.fetchone()
        if not row:
            return None
        city_list_id = row[0]
    c.execute("SELECT id FROM config_items WHERE list_id = ? AND col1 = ?", (city_list_id, label))
    row = c.fetchone()
    return row[0] if row else None


def seed_from_config_if_empty():
    """Seed any list from CONFIG_REGISTRY that isn't already in config_lists.

    Runs on every startup rather than bailing once config_lists is non-empty, so
    a list added to CONFIG_REGISTRY later (e.g. barangay_list) still gets created
    in an existing, already-populated config.db.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT key FROM config_lists")
        existing_keys = {row[0] for row in c.fetchall()}
        list_ids_by_key = {}

        for key, label, kind, col1_label, col2_label, source_data in CONFIG_REGISTRY:
            if key in existing_keys:
                continue

            c.execute(
                "INSERT INTO config_lists (key, label, kind, col1_label, col2_label) VALUES (?, ?, ?, ?, ?)",
                (key, label, kind, col1_label, col2_label),
            )
            list_id = c.lastrowid
            list_ids_by_key[key] = list_id

            for sort_order, (col1, col2, extra2) in enumerate(_pairs_for(kind, source_data)):
                extra = None
                if kind == "cities":
                    province_item_id = _province_item_id_by_label(c, list_ids_by_key, district_city.get(col1))
                    extra = str(province_item_id) if province_item_id is not None else None
                elif kind == "provinces":
                    region_item_id = _first_region_item_id(c, list_ids_by_key)
                    extra = str(region_item_id) if region_item_id is not None else None
                c.execute(
                    "INSERT INTO config_items (list_id, sort_order, col1, col2, extra, extra2) VALUES (?, ?, ?, ?, ?, ?)",
                    (list_id, sort_order, col1, col2, extra, extra2),
                )
        conn.commit()


def backfill_city_regions():
    """One-time backfill for list_of_city rows seeded before Region existed (col2/extra2 NULL)."""
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM config_lists WHERE key = 'list_of_city'")
        row = c.fetchone()
        if not row:
            return
        list_id = row[0]
        c.execute(
            "UPDATE config_items SET col2 = ?, extra2 = ? "
            "WHERE list_id = ? AND (col2 IS NULL OR extra2 IS NULL)",
            ("NCR (National Capital Region)", "NCR [National Capital Region]", list_id),
        )
        conn.commit()


def migrate_list_to_pairs(key, col1_label="Label", col2_label="Value"):
    """One-time migration for a list that used to be single-value (kind != 'pairs', no col2)
    or stored as some other single-value shape (e.g. kind='dict').

    Converts it to kind='pairs' and backfills col2 = col1 for any row seeded before
    this existed, so existing rows default to value == label. col1_label/col2_label
    let callers match whatever headers CONFIG_REGISTRY declares for this list, rather
    than always falling back to the generic "Label"/"Value".
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, kind FROM config_lists WHERE key = ?", (key,))
        row = c.fetchone()
        if not row:
            return
        list_id, kind = row
        if kind != "pairs":
            c.execute(
                "UPDATE config_lists SET kind = 'pairs', col1_label = ?, col2_label = ? WHERE id = ?",
                (col1_label, col2_label, list_id),
            )
        c.execute(
            "UPDATE config_items SET col2 = col1 WHERE list_id = ? AND col2 IS NULL",
            (list_id,),
        )
        conn.commit()


def migrate_gender_to_pairs():
    migrate_list_to_pairs("gender_list")


def migrate_target_sector_to_pairs():
    migrate_list_to_pairs("target_sector_list")


def migrate_mode_of_release_to_pairs():
    migrate_list_to_pairs("mode_of_release")


def migrate_financial_assistance_to_pairs():
    migrate_list_to_pairs("financial_assistance_list")


def migrate_civil_status_to_pairs():
    migrate_list_to_pairs("civil_status_list", "Choice", "Mapped Value")


def migrate_fund_source_to_pairs():
    migrate_list_to_pairs("fund_source_list", "Code", "Display Name")


def migrate_relationship_to_pairs():
    migrate_list_to_pairs("relationship_list", "Choice", "Mapped Value")


def migrate_client_sub_category_to_pairs():
    """One-time migration: client_sub_category used to be kind='dict' (Key -> Value,
    both always identical). Converts it to kind='pairs' like the other Choice/Value
    lists, so it's edited the same way in Config Manager. migrate_list_to_pairs
    backfills col2 = col1 for any row seeded before this existed."""
    migrate_list_to_pairs("client_sub_category", "Key", "Value")


def migrate_approved_by_to_dual_pairs():
    """One-time migration: approved_by_list used to be kind='dict' (Short Name -> Full Name),
    where col1 (Short Name) doubled as both the display label AND the gform submission value,
    and col2 (Full Name) was the website value.

    Flips it to kind='dual_pairs' (Label/GForm Value/Website Value), keeping col1 as the label
    (unchanged text) while reshuffling: new col2 (GForm Value) = old col1, new extra2 (Website
    Value) = old col2. This preserves exactly what gets submitted to each destination today —
    it just makes the label independently editable going forward.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, kind FROM config_lists WHERE key = 'approved_by_list'")
        row = c.fetchone()
        if not row:
            return
        list_id, kind = row
        if kind == "dual_pairs":
            return

        c.execute(
            "UPDATE config_lists SET kind = 'dual_pairs', col1_label = 'Label', col2_label = 'GForm Value' "
            "WHERE id = ?",
            (list_id,),
        )
        c.execute("SELECT id, col1, col2 FROM config_items WHERE list_id = ?", (list_id,))
        items = c.fetchall()
        for item_id, col1, col2 in items:
            c.execute(
                "UPDATE config_items SET col2 = ?, extra2 = ? WHERE id = ?",
                (col1, col2, item_id),
            )
        conn.commit()


def migrate_target_sector_to_dual_pairs():
    """One-time migration: target_sector_list used to be kind='pairs' (Label/Value only).

    Flips it to kind='dual_pairs' (Label/GForm Value/Website Value) and backfills
    extra2 = col2 for any row that predates this, so existing rows default their
    new Website Value to whatever the old single Value already was.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, kind FROM config_lists WHERE key = 'target_sector_list'")
        row = c.fetchone()
        if not row:
            return
        list_id, kind = row
        if kind != "dual_pairs":
            c.execute(
                "UPDATE config_lists SET kind = 'dual_pairs', col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute(
            "UPDATE config_items SET extra2 = col2 WHERE list_id = ? AND extra2 IS NULL",
            (list_id,),
        )
        conn.commit()


def migrate_list_to_dual_pairs(key):
    """One-time migration for a list that used to be kind='pairs' (Label/Value only).

    Flips it to kind='dual_pairs' (Label/GForm Value/Website Value) and backfills
    extra2 = col2 for any row that predates this, so existing rows default their
    new Website Value to whatever the old single Value already was. Mirrors
    migrate_gender_to_dual_pairs/migrate_target_sector_to_dual_pairs, generalized
    for the several other lists needing the same upgrade.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, kind FROM config_lists WHERE key = ?", (key,))
        row = c.fetchone()
        if not row:
            return
        list_id, kind = row
        if kind != "dual_pairs":
            c.execute(
                "UPDATE config_lists SET kind = 'dual_pairs', col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute(
            "UPDATE config_items SET extra2 = col2 WHERE list_id = ? AND extra2 IS NULL",
            (list_id,),
        )
        conn.commit()


def migrate_civil_status_to_dual_pairs():
    migrate_list_to_dual_pairs("civil_status_list")


def migrate_fund_source_to_dual_pairs():
    migrate_list_to_dual_pairs("fund_source_list")


def migrate_mode_of_release_to_dual_pairs():
    migrate_list_to_dual_pairs("mode_of_release")


def migrate_financial_assistance_to_dual_pairs():
    migrate_list_to_dual_pairs("financial_assistance_list")


def migrate_relationship_to_dual_pairs():
    migrate_list_to_dual_pairs("relationship_list")


def migrate_client_sub_category_to_dual_pairs():
    migrate_list_to_dual_pairs("client_sub_category")


def migrate_gender_to_dual_pairs():
    """One-time migration: gender_list used to be kind='pairs' (Label/Value only).

    Flips it to kind='dual_pairs' (Label/GForm Value/Website Value) and backfills
    extra2 = col2 for any row that predates this, so existing rows default their
    new Website Value to whatever the old single Value already was.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, kind FROM config_lists WHERE key = 'gender_list'")
        row = c.fetchone()
        if not row:
            return
        list_id, kind = row
        if kind != "dual_pairs":
            c.execute(
                "UPDATE config_lists SET kind = 'dual_pairs', col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute(
            "UPDATE config_items SET extra2 = col2 WHERE list_id = ? AND extra2 IS NULL",
            (list_id,),
        )
        conn.commit()


def migrate_region_to_dual_pairs():
    """One-time migration: region_list used to be kind='list' (Region name only).

    Flips it to kind='dual_pairs' (Region/GForm Value/Website Value), mirroring
    target_sector_list, and backfills col2/extra2 for any row seeded before this
    existed, defaulting both to the known NCR GForm/Website values (same literals
    list_of_city's region columns already default to).
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, kind FROM config_lists WHERE key = 'region_list'")
        row = c.fetchone()
        if not row:
            return
        list_id, kind = row
        if kind != "dual_pairs":
            c.execute(
                "UPDATE config_lists SET kind = 'dual_pairs', col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute(
            "UPDATE config_items SET col2 = ?, extra2 = ? "
            "WHERE list_id = ? AND (col2 IS NULL OR extra2 IS NULL)",
            ("NCR (National Capital Region)", "NCR [National Capital Region]", list_id),
        )
        conn.commit()


def migrate_province_region_link_to_id():
    """One-time migration: province_list.extra used to store the linked region's
    LABEL text (a name match that silently breaks if the region is later renamed).

    Converts it to store the linked region's config_items.id instead, resolving
    each existing province's stored region label to that region's current item id.
    Idempotent: once a province's extra holds an id, it won't match any region
    label text, so re-running this is a no-op for already-migrated rows.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM config_lists WHERE key = 'region_list'")
        region_row = c.fetchone()
        c.execute("SELECT id FROM config_lists WHERE key = 'province_list'")
        province_row = c.fetchone()
        if not region_row or not province_row:
            return
        region_list_id, province_list_id = region_row[0], province_row[0]

        c.execute("SELECT id, col1 FROM config_items WHERE list_id = ?", (region_list_id,))
        region_id_by_label = {label: item_id for item_id, label in c.fetchall()}

        c.execute("SELECT id, extra FROM config_items WHERE list_id = ?", (province_list_id,))
        for item_id, extra in c.fetchall():
            if extra in region_id_by_label:
                c.execute(
                    "UPDATE config_items SET extra = ? WHERE id = ?",
                    (str(region_id_by_label[extra]), item_id),
                )
        conn.commit()


def migrate_city_province_link_to_id():
    """One-time migration: list_of_city.extra used to store the linked province's
    LABEL text (a name match that silently breaks if the province is later renamed).

    Converts it to store the linked province's config_items.id instead, resolving
    each existing city's stored province label to that province's current item id.
    Idempotent: once a city's extra holds an id, it won't match any province
    label text, so re-running this is a no-op for already-migrated rows.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM config_lists WHERE key = 'province_list'")
        province_row = c.fetchone()
        c.execute("SELECT id FROM config_lists WHERE key = 'list_of_city'")
        city_row = c.fetchone()
        if not province_row or not city_row:
            return
        province_list_id, city_list_id = province_row[0], city_row[0]

        c.execute("SELECT id, col1 FROM config_items WHERE list_id = ?", (province_list_id,))
        province_id_by_label = {label: item_id for item_id, label in c.fetchall()}

        c.execute("SELECT id, extra FROM config_items WHERE list_id = ?", (city_list_id,))
        for item_id, extra in c.fetchall():
            if extra in province_id_by_label:
                c.execute(
                    "UPDATE config_items SET extra = ? WHERE id = ?",
                    (str(province_id_by_label[extra]), item_id),
                )
        conn.commit()


def migrate_barangay_city_link_to_id():
    """One-time migration: barangay_list.extra used to store the linked city's
    LABEL text (a name match that silently breaks if the city is later renamed).

    Converts it to store the linked city's config_items.id instead, resolving
    each existing barangay's stored city label to that city's current item id.
    Real-world barangay rows were entered over time with inconsistent casing and
    sometimes the city's col2 (GForm value, e.g. "QUIAPO") instead of its col1
    (display label, e.g. "Quiapo"), so the lookup matches case-insensitively
    against either column. Idempotent: once a barangay's extra holds a numeric
    id, it won't match any city label text, so re-running this is a no-op for
    already-migrated rows.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM config_lists WHERE key = 'list_of_city'")
        city_row = c.fetchone()
        c.execute("SELECT id FROM config_lists WHERE key = 'barangay_list'")
        barangay_row = c.fetchone()
        if not city_row or not barangay_row:
            return
        city_list_id, barangay_list_id = city_row[0], barangay_row[0]

        c.execute("SELECT id, col1, col2 FROM config_items WHERE list_id = ?", (city_list_id,))
        city_id_by_label = {}
        for item_id, col1, col2 in c.fetchall():
            if col1:
                city_id_by_label.setdefault(col1.strip().upper(), item_id)
            if col2:
                city_id_by_label.setdefault(col2.strip().upper(), item_id)

        c.execute("SELECT id, extra FROM config_items WHERE list_id = ?", (barangay_list_id,))
        for item_id, extra in c.fetchall():
            if extra is None:
                continue
            city_id = city_id_by_label.get(extra.strip().upper())
            if city_id is not None:
                c.execute(
                    "UPDATE config_items SET extra = ? WHERE id = ?",
                    (str(city_id), item_id),
                )
        conn.commit()


def migrate_province_to_dual_pairs():
    """One-time migration: province_list rows used to carry only a name (col2/extra2
    unset). Adds GForm Value/Website Value columns, mirroring region_list and
    target_sector_list, and backfills col2/extra2 for any row seeded before this
    existed, defaulting both to the province's own label (province currently uses
    the same text in both destinations, same as list_of_city's province link did
    before region needed two distinct formats).
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, col2_label FROM config_lists WHERE key = 'province_list'")
        row = c.fetchone()
        if not row:
            return
        list_id, col2_label = row
        if col2_label != "GForm Value":
            c.execute(
                "UPDATE config_lists SET col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute(
            "UPDATE config_items SET col2 = COALESCE(col2, col1), extra2 = COALESCE(extra2, col1) "
            "WHERE list_id = ? AND (col2 IS NULL OR extra2 IS NULL)",
            (list_id,),
        )
        conn.commit()


def migrate_city_to_dual_pairs():
    """One-time migration: list_of_city.col2/extra2 used to duplicate the single
    NCR-wide REGION's GForm/Website values onto every city row. Now that
    region_gform/region_website are derived by walking city -> province -> region
    (each linked by id) instead, col2/extra2 become the CITY's own GForm
    Value/Website Value, defaulting to the city's own label (except "CITY OF
    CALOOCAN", whose real-world website value is "KALOOKAN CITY", matching the
    special case previously hardcoded in the Selenium automation).

    Overwrites any row whose col2/extra2 are still NULL or still hold the old
    region literal (i.e. haven't been customized since this migration); leaves
    anything else alone.
    """
    OLD_REGION_GFORM = "NCR (National Capital Region)"
    OLD_REGION_WEBSITE = "NCR [National Capital Region]"
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, col2_label FROM config_lists WHERE key = 'list_of_city'")
        row = c.fetchone()
        if not row:
            return
        list_id, col2_label = row
        if col2_label != "GForm Value":
            c.execute(
                "UPDATE config_lists SET col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute("SELECT id, col1, col2, extra2 FROM config_items WHERE list_id = ?", (list_id,))
        for item_id, col1, col2, extra2 in c.fetchall():
            new_col2 = col1 if col2 in (None, OLD_REGION_GFORM) else col2
            default_website = "KALOOKAN CITY" if col1 == "CITY OF CALOOCAN" else col1
            new_extra2 = default_website if extra2 in (None, OLD_REGION_WEBSITE) else extra2
            if new_col2 != col2 or new_extra2 != extra2:
                c.execute(
                    "UPDATE config_items SET col2 = ?, extra2 = ? WHERE id = ?",
                    (new_col2, new_extra2, item_id),
                )
        conn.commit()


def migrate_barangay_to_dual_pairs():
    """One-time migration: barangay_list rows used to carry only a name + city
    link (col2/extra2 unset). Adds GForm Value/Website Value columns, mirroring
    list_of_city/province_list, and backfills col2/extra2 for any row added via
    the admin UI before this existed, defaulting both to the barangay's own
    label.
    """
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id, col2_label FROM config_lists WHERE key = 'barangay_list'")
        row = c.fetchone()
        if not row:
            return
        list_id, col2_label = row
        if col2_label != "GForm Value":
            c.execute(
                "UPDATE config_lists SET col2_label = 'GForm Value' WHERE id = ?",
                (list_id,),
            )
        c.execute(
            "UPDATE config_items SET col2 = COALESCE(col2, col1), extra2 = COALESCE(extra2, col1) "
            "WHERE list_id = ? AND (col2 IS NULL OR extra2 IS NULL)",
            (list_id,),
        )
        conn.commit()


def delete_list_by_key(key):
    """Remove a config list (and its items) that's no longer in CONFIG_REGISTRY. No-op if already gone."""
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        c = conn.cursor()
        c.execute("SELECT id FROM config_lists WHERE key = ?", (key,))
        row = c.fetchone()
        if not row:
            return
        list_id = row[0]
        c.execute("DELETE FROM config_items WHERE list_id = ?", (list_id,))
        c.execute("DELETE FROM config_lists WHERE id = ?", (list_id,))
        conn.commit()


def remove_approver_list():
    delete_list_by_key("approver_list")


def get_all_lists():
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, key, label, kind, col1_label, col2_label
            FROM config_lists ORDER BY id ASC
        ''')
        return cursor.fetchall()


def get_items(list_id):
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute('''
            SELECT id, col1, col2, extra, extra2
            FROM config_items WHERE list_id = ? ORDER BY sort_order ASC
        ''', (list_id,))
        return cursor.fetchall()


def insert_item(list_id, col1, col2, extra, extra2=None):
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COALESCE(MAX(sort_order), -1) FROM config_items WHERE list_id = ?", (list_id,))
        next_order = cursor.fetchone()[0] + 1
        conn.execute(
            "INSERT INTO config_items (list_id, sort_order, col1, col2, extra, extra2) VALUES (?, ?, ?, ?, ?, ?)",
            (list_id, next_order, col1, col2, extra, extra2),
        )


def update_item(item_id, col1, col2, extra, extra2=None):
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        conn.execute(
            "UPDATE config_items SET col1 = ?, col2 = ?, extra = ?, extra2 = ? WHERE id = ?",
            (col1, col2, extra, extra2, item_id),
        )


def delete_item(item_id):
    with sqlite3.connect(DB_NAME_CONFIG) as conn:
        conn.execute("DELETE FROM config_items WHERE id = ?", (item_id,))
