import sqlite3

DB_NAME_WORKER = 'worker.db'

def init_db_worker():
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS worker (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                sw_lname TEXT NOT NULL,
                sw_fname TEXT NOT NULL,
                sw_mname TEXT NOT NULL,
                search_thru_first_name INTEGER NOT NULL DEFAULT 0
            )
        ''')
        conn.commit()

def get_all_workers():
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        cursor = conn.cursor()
        cursor.execute(""" 
                           SELECT 
                               id,
                               sw_lname,
                               sw_fname,
                               sw_mname,
                               search_thru_first_name 
                           FROM worker ORDER BY id ASC
                       """)
        return cursor.fetchall()

def get_worker_id(lastname, firstname, middlename):
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        cursor = conn.cursor()
        query = """
            SELECT id, sw_lname, sw_fname, sw_mname, search_thru_first_name FROM worker 
            WHERE LOWER(TRIM(sw_lname)) = LOWER(TRIM(?))
              AND LOWER(TRIM(sw_fname)) = LOWER(TRIM(?))
                            AND (
                                (sw_mname IS NULL AND ? IS NULL) OR
                                LOWER(TRIM(sw_mname)) = LOWER(TRIM(?))
                            )
            LIMIT 1;
            """
        cursor.execute(query, (lastname, firstname,  middlename, middlename))
        return cursor.fetchone()

def get_worker_by_id(id):
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        cursor = conn.cursor()
        query = """
            SELECT sw_lname, sw_fname, sw_mname, search_thru_first_name 
            FROM worker WHERE id = ?
            LIMIT 1;
            """
        cursor.execute(query, (id,))
        return cursor.fetchone()

def delete_worker_by_id(id):
    with sqlite3.connect(DB_NAME_WORKER) as conn:
        conn.execute("DELETE FROM worker WHERE id=?", (id,))

def insert_worker(sw_lname, sw_fname, sw_mname, search_thru_first_name):
    try:
        with sqlite3.connect(DB_NAME_WORKER) as conn:
            conn.execute("""
                INSERT INTO worker (
                        sw_lname,
                        sw_fname,
                        sw_mname,
                        search_thru_first_name
                ) VALUES (?, ?, ?, ?)
            """, (
                sw_lname,
                sw_fname,
                sw_mname,
                search_thru_first_name
            ))
        return True
    except Exception as e:
        print("Error insert :", e)
        return False

def update_worker(rowid, sw_lname, sw_fname, sw_mname, search_thru_first_name):
    try:
        with sqlite3.connect(DB_NAME_WORKER) as conn:
            conn.execute("""
                 UPDATE worker SET
                     sw_lname = ?,
                     sw_fname = ?,
                     sw_mname = ?,
                     search_thru_first_name = ?
                 WHERE rowid = ?;
             """, (
                sw_lname,
                sw_fname,
                sw_mname,
                search_thru_first_name,
                rowid
            ))
        return True
    except Exception as e:
        print("Error update :", e)
        return False