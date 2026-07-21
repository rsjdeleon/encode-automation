import sqlite3
import string
from core.paths import WORKER_DB_PATH

DB_NAME_WORKER = WORKER_DB_PATH


def init_db_worker():
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS worker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                gform_value TEXT,
                website_value TEXT
            )
        ''')
        conn.commit()
    _migrate_names_to_full_name()
    _migrate_drop_thru_firstname()


def _default_gform_value(sw_lname, sw_fname, sw_mname):
    mname_initial = string.capwords(sw_mname)[0].upper() if sw_mname.strip() else ""
    name = f"{string.capwords(sw_lname)}, {string.capwords(sw_fname)}"
    return f"{name} {mname_initial}." if mname_initial else name


def _default_website_value(sw_lname, sw_fname, sw_mname, search_thru_first_name):
    if search_thru_first_name:
        if not sw_mname.strip():
            return f"{sw_fname} {sw_lname}".strip()
        return f"{sw_fname} {sw_mname} {sw_lname}".strip()
    return f"{sw_lname} {sw_fname} {sw_mname}".strip()


def _default_full_name(sw_lname, sw_fname, sw_mname):
    parts = [p for p in (sw_fname.strip(), sw_mname.strip()) if p]
    return f"{sw_lname.strip()}, {' '.join(parts)}" if parts else sw_lname.strip()


def _migrate_names_to_full_name():
    """One-time migration: the worker table used to store sw_lname/sw_fname/sw_mname
    separately. Rebuilds it around a single full_name plus explicit gform_value/
    website_value, defaulted from the same formatting the automation code used to
    compute on the fly, so existing records keep submitting the same text until
    an admin edits them in Social Worker Management.
    """
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(worker)")
        columns = {row[1] for row in c.fetchall()}
        if "sw_lname" not in columns:
            return

        c.execute("SELECT id, sw_lname, sw_fname, sw_mname, search_thru_first_name FROM worker")
        old_rows = c.fetchall()

        c.execute('''
            CREATE TABLE worker_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                gform_value TEXT,
                website_value TEXT,
                search_thru_first_name INTEGER NOT NULL DEFAULT 0
            )
        ''')

        for row_id, sw_lname, sw_fname, sw_mname, search_thru_first_name in old_rows:
            full_name = _default_full_name(sw_lname, sw_fname, sw_mname)
            gform_value = _default_gform_value(sw_lname, sw_fname, sw_mname)
            website_value = _default_website_value(sw_lname, sw_fname, sw_mname, search_thru_first_name)
            c.execute(
                "INSERT INTO worker_new (id, full_name, gform_value, website_value, search_thru_first_name) "
                "VALUES (?, ?, ?, ?, ?)",
                (row_id, full_name, gform_value, website_value, search_thru_first_name),
            )

        c.execute("DROP TABLE worker")
        c.execute("ALTER TABLE worker_new RENAME TO worker")
        conn.commit()


def _migrate_drop_thru_firstname():
    """One-time migration: removes search_thru_first_name, no longer used."""
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        c = conn.cursor()
        c.execute("PRAGMA table_info(worker)")
        columns = {row[1] for row in c.fetchall()}
        if "search_thru_first_name" not in columns:
            return

        c.execute("SELECT id, full_name, gform_value, website_value FROM worker")
        old_rows = c.fetchall()

        c.execute('''
            CREATE TABLE worker_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                full_name TEXT NOT NULL,
                gform_value TEXT,
                website_value TEXT
            )
        ''')
        c.executemany(
            "INSERT INTO worker_new (id, full_name, gform_value, website_value) VALUES (?, ?, ?, ?)",
            old_rows,
        )
        c.execute("DROP TABLE worker")
        c.execute("ALTER TABLE worker_new RENAME TO worker")
        conn.commit()


def get_all_workers():
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, full_name, gform_value, website_value
            FROM worker ORDER BY id ASC
        """)
        return cursor.fetchall()


def get_worker_id(sw_lname, sw_fname, sw_mname):
    """Compatibility shim for the pre-migration 3-field lookup.

    assistance_form.py hasn't been updated yet for the new full_name/
    gform_value/website_value schema and still calls this with separate name
    parts. Reconstructs the equivalent full_name (using the same formatting
    the migration used) to look up by, so records saved before this change
    still resolve to the right worker.
    """
    return get_worker_by_full_name(_default_full_name(sw_lname, sw_fname, sw_mname))


def get_worker_by_full_name(full_name):
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT id, full_name, gform_value, website_value "
            "FROM worker WHERE LOWER(TRIM(full_name)) = LOWER(TRIM(?)) LIMIT 1",
            (full_name,),
        )
        return cursor.fetchone()


def get_worker_by_id(id):
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT full_name, gform_value, website_value "
            "FROM worker WHERE id = ? LIMIT 1",
            (id,),
        )
        return cursor.fetchone()


def delete_worker_by_id(id):
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        conn.execute("DELETE FROM worker WHERE id=?", (id,))


def insert_worker(full_name, gform_value, website_value):
    try:
        with sqlite3.connect(DB_NAME_WORKER) as conn:
            conn.execute("""
                INSERT INTO worker (full_name, gform_value, website_value)
                VALUES (?, ?, ?)
            """, (full_name, gform_value, website_value))
        return True
    except Exception as e:
        print("Error insert :", e)
        return False


def update_worker(rowid, full_name, gform_value, website_value):
    try:
        with sqlite3.connect(DB_NAME_WORKER) as conn:
            conn.execute("""
                UPDATE worker SET
                    full_name = ?,
                    gform_value = ?,
                    website_value = ?
                WHERE id = ?;
            """, (full_name, gform_value, website_value, rowid))
        return True
    except Exception as e:
        print("Error update :", e)
        return False
