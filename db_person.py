import sqlite3

DB_NAME = 'person-b1-ajean.db'

def init_db_person():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS person (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                encoder_name TEXT,
                date_encoded DATE NOT NULL,

                target_sector INTEGER NOT NULL,
                target_sector_bene INTEGER NOT NULL,
                financial_assist INTEGER NOT NULL,
                amount TEXT NOT NULL,
                fund_source INTEGER NOT NULL,
                sw_lname TEXT NOT NULL,
                sw_fname TEXT NOT NULL,
                sw_mname TEXT NOT NULL,
                interview_date DATE NOT NULL,

                client_lastname TEXT NOT NULL,
                client_firstname TEXT NOT NULL,
                client_middlename TEXT NOT NULL,
                client_ext TEXT,

                client_relationship INTEGER NOT NULL,
                client_gender INTEGER NOT NULL,
                client_civil_status INTEGER NOT NULL,
                client_bday DATE NOT NULL,
                client_age INTEGER NOT NULL,
                client_contact_no TEXT,
                client_house_street TEXT,
                client_barangay TEXT,
                client_city INTEGER NOT NULL,

                bene_lastname TEXT NOT NULL,
                bene_firstname TEXT NOT NULL,
                bene_middlename TEXT NOT NULL,
                bene_ext TEXT,

                bene_relationship INTEGER NOT NULL,
                bene_gender INTEGER NOT NULL,
                bene_civil_status INTEGER NOT NULL,
                bene_bday DATE NOT NULL,
                bene_age INTEGER NOT NULL,
                bene_contact_no TEXT,
                bene_house_street TEXT,
                bene_barangay TEXT,
                bene_city INTEGER NOT NULL,

                has_beneficiary INTEGER NOT NULL DEFAULT 0,
                encoded INTEGER NOT NULL DEFAULT 0
            )
        ''')
        conn.commit()

def set_encoded(rowid, value):
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                UPDATE person SET
                    encoded = ? 
                WHERE rowid = ?;
            """, (
                value,
                rowid
            ))
        return True
    except Exception as e:
        print("Error encoded :", e)
        return False

def person_exists(cursor, firstname, lastname, middlename):
    try:
        query = """
            SELECT 1 FROM person 
            WHERE LOWER(TRIM(firstname)) = LOWER(TRIM(?))
              AND LOWER(TRIM(lastname)) = LOWER(TRIM(?))
              AND (
                middlename IS NULL AND ? IS NULL OR
                LOWER(TRIM(middlename)) = LOWER(TRIM(?))
              )
            LIMIT 1;
            """
        cursor.execute(query, (firstname, lastname, middlename, middlename))
        return cursor.fetchone() is not None
    except Exception as e:
        print("Error fetch :", e)
        return False

def get_all_person_by_encoded(is_encoded):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        cursor.execute(""" 
            SELECT 
                id,
                encoder_name,
                date_encoded,
                target_sector,
                financial_assist,
                amount,
                fund_source,
                sw_lname,
                sw_fname,
                sw_mname,
                interview_date,
                client_relationship,
                client_lastname,
                client_firstname,
                client_middlename,
                client_ext,
                client_gender,
                client_bday,
                client_age,
                client_contact_no,
                client_civil_status,
                client_house_street,
                client_barangay,
                client_city,
                bene_relationship,
                bene_lastname,
                bene_firstname,
                bene_middlename,
                bene_ext,
                bene_gender,
                bene_bday,
                bene_age,
                bene_contact_no,
                bene_civil_status,
                bene_house_street,
                bene_barangay,
                bene_city,
                has_beneficiary,
                encoded,
                target_sector_bene  
            FROM person WHERE encoded = ? ORDER BY id ASC
        """, is_encoded)
        return cursor.fetchall()

def delete_person_by_id(id):
    with sqlite3.connect(DB_NAME) as conn:
        conn.execute("DELETE FROM person WHERE id=?", (id,))

def insert_person(
        encoder_name,
        date_encoded,
        target_sector,
        target_sector_bene,
        financial_assist,
        amount,
        fund_source,
        sw_lname,
        sw_fname,
        sw_mname,
        interview_date,
        client_relationship,
        client_lastname,
        client_firstname,
        client_middlename,
        client_ext,
        client_gender,
        client_bday,
        client_age,
        client_contact_no,
        client_civil_status,
        client_house_street,
        client_barangay,
        client_city,
        bene_relationship,
        bene_lastname,
        bene_firstname,
        bene_middlename,
        bene_ext,
        bene_gender,
        bene_bday,
        bene_age,
        bene_contact_no,
        bene_civil_status,
        bene_house_street,
        bene_barangay,
        bene_city,
        has_beneficiary,
):
    """Insert a person record into the database"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            if not person_exists(
                    conn.cursor(),
                    client_firstname,
                    client_lastname,
                    client_middlename
            ):
                conn.execute("""
                    INSERT INTO person (
                        encoder_name,
                        date_encoded,

                        target_sector,
                        target_sector_bene,
                        financial_assist,
                        amount,
                        fund_source,
                        sw_lname,
                        sw_fname,
                        sw_mname,
                        interview_date,

                        client_relationship,

                        client_lastname,
                        client_firstname,
                        client_middlename,

                        client_ext,

                        client_gender,

                        client_bday,
                        client_age,

                        client_contact_no,
                        client_civil_status,

                        client_house_street,
                        client_barangay,
                        client_city,

                        bene_relationship,

                        bene_lastname,
                        bene_firstname,
                        bene_middlename,
                        bene_ext,

                        bene_gender,

                        bene_bday,
                        bene_age,

                        bene_contact_no,
                        bene_civil_status,

                        bene_house_street,
                        bene_barangay,
                        bene_city,

                        has_beneficiary
                    ) VALUES (?, ?, ?, ?, ?, ?, 
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?, ?, ?);
                """, (
                    encoder_name,
                    date_encoded,
                    target_sector,
                    target_sector_bene,
                    financial_assist,
                    amount,
                    fund_source,
                    sw_lname,
                    sw_fname,
                    sw_mname,
                    interview_date,
                    client_relationship,
                    client_lastname,
                    client_firstname,
                    client_middlename,
                    client_ext,
                    client_gender,
                    client_bday,
                    client_age,
                    client_contact_no,
                    client_civil_status,
                    client_house_street,
                    client_barangay,
                    client_city,
                    bene_relationship,
                    bene_lastname,
                    bene_firstname,
                    bene_middlename,
                    bene_ext,
                    bene_gender,
                    bene_bday,
                    bene_age,
                    bene_contact_no,
                    bene_civil_status,
                    bene_house_street,
                    bene_barangay,
                    bene_city,
                    has_beneficiary,
                ))
                return True
            else:
                return False  # Already exists
    except Exception as e:
        print("Error inserting person:", e)
        return False


def update_person(
        rowid,
        encoder_name,
        date_encoded,

        target_sector,
        target_sector_bene,
        financial_assist,
        amount,
        fund_source,
        sw_lname,
        sw_fname,
        sw_mname,
        interview_date,

        client_relationship,
        client_lastname,
        client_firstname,
        client_middlename,
        client_ext,
        client_gender,
        client_bday,
        client_age,
        client_contact_no,
        client_civil_status,
        client_house_street,
        client_barangay,
        client_city,

        bene_relationship,
        bene_lastname,
        bene_firstname,
        bene_middlename,
        bene_ext,
        bene_gender,
        bene_bday,
        bene_age,
        bene_contact_no,
        bene_civil_status,
        bene_house_street,
        bene_barangay,
        bene_city,

        has_beneficiary,
):
    """Update a person record by rowid"""
    try:
        with sqlite3.connect(DB_NAME) as conn:
            conn.execute("""
                UPDATE person SET
                    encoder_name = ?,
                    date_encoded= ?,

                    target_sector = ?,
                    target_sector_bene = ?,
                    financial_assist = ?,
                    amount = ?,
                    fund_source = ?,
                    sw_lname = ?,
                    sw_fname = ?,
                    sw_mname = ?,
                    interview_date = ?,

                    client_relationship = ?,
                    client_lastname = ?,
                    client_firstname = ?,
                    client_middlename = ?,
                    client_ext = ?,
                    client_gender = ?,
                    client_bday = ?,
                    client_age = ?,
                    client_contact_no = ?,
                    client_civil_status = ?,
                    client_house_street = ?,
                    client_barangay = ?,
                    client_city = ?,

                    bene_relationship = ?,
                    bene_lastname = ?,
                    bene_firstname = ?,
                    bene_middlename = ?,
                    bene_ext = ?,
                    bene_gender = ?,
                    bene_bday = ?,
                    bene_age = ?,
                    bene_contact_no = ?,
                    bene_civil_status = ?,
                    bene_house_street = ?,
                    bene_barangay = ?,
                    bene_city = ?,

                    has_beneficiary = ?
                WHERE rowid = ?;
            """, (
                encoder_name,
                date_encoded,
                target_sector,
                target_sector_bene,
                financial_assist,
                amount,
                fund_source,
                sw_lname,
                sw_fname,
                sw_mname,
                interview_date,
                client_relationship,
                client_lastname,
                client_firstname,
                client_middlename,
                client_ext,
                client_gender,
                client_bday,
                client_age,
                client_contact_no,
                client_civil_status,
                client_house_street,
                client_barangay,
                client_city,
                bene_relationship,
                bene_lastname,
                bene_firstname,
                bene_middlename,
                bene_ext,
                bene_gender,
                bene_bday,
                bene_age,
                bene_contact_no,
                bene_civil_status,
                bene_house_street,
                bene_barangay,
                bene_city,
                has_beneficiary,
                rowid
            ))
        return True
    except Exception as e:
        print("Error updating person:", e)
        return False