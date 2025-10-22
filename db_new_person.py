import sqlite3

DB_NAME = 'person-record.db'

def init_db_person():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute('''
            CREATE TABLE IF NOT EXISTS person (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                encoder_name TEXT,
                date_encoded DATE ,

                target_sector INTEGER ,
                target_sector_bene INTEGER ,
                financial_assist INTEGER ,
                amount TEXT ,
                fund_source INTEGER ,
                sw_lname TEXT ,
                sw_fname TEXT ,
                sw_mname TEXT ,
                interview_date DATE ,

                client_lastname TEXT ,
                client_firstname TEXT ,
                client_middlename TEXT ,
                client_ext TEXT,

                client_relationship INTEGER ,
                client_gender INTEGER ,
                client_civil_status INTEGER ,
                client_bday DATE ,
                client_age INTEGER ,
                client_contact_no TEXT,
                client_house_street TEXT,
                client_barangay TEXT,
                client_city INTEGER ,

                bene_lastname TEXT ,
                bene_firstname TEXT ,
                bene_middlename TEXT ,
                bene_ext TEXT,

                bene_relationship INTEGER ,
                bene_gender INTEGER ,
                bene_civil_status INTEGER ,
                bene_bday DATE ,
                bene_age INTEGER ,
                bene_contact_no TEXT,
                bene_house_street TEXT,
                bene_barangay TEXT,
                bene_city INTEGER ,

                has_beneficiary INTEGER  DEFAULT 0,
                mode_release INTEGER DEFAULT 0,
                approved_by INTEGER DEFAULT 0,
                sub_category INTEGER DEFAULT 0,
                encoded INTEGER  DEFAULT 0
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
                        WHERE LOWER(TRIM(client_firstname)) = LOWER(TRIM(?))
                          AND LOWER(TRIM(client_lastname)) = LOWER(TRIM(?))
                          AND (
                            (client_middlename IS NULL AND ? IS NULL) OR
                            LOWER(TRIM(client_middlename)) = LOWER(TRIM(?))
                          )
            LIMIT 1;
            """
        # Note: parameter order matches the placeholders: firstname, lastname, middlename, middlename
        cursor.execute(query, (firstname, lastname, middlename, middlename))
        return cursor.fetchone() is not None
    except Exception as e:
        print("Error fetch :", e)
        return False

def get_all_person_by_encoded(is_encoded):
    with sqlite3.connect(DB_NAME) as conn:
        cursor = conn.cursor()
        # Ensure parameters are passed as a single-element tuple
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
                target_sector_bene,
                mode_release, 
                approved_by,
                sub_category 
            FROM person WHERE encoded = ? ORDER BY id ASC
        """, (is_encoded,))
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
        mode_release,
        approved_by,
        sub_category
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
                        has_beneficiary,
                        mode_release, 
                        approved_by,
                        sub_category 
                    ) VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 
                    ?);
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
                    mode_release,
                    approved_by, 
                    sub_category
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
        mode_release,
        approved_by,
        sub_category,
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

                    has_beneficiary = ?,
                    mode_release = ?,
                    approved_by = ?,
                    sub_category = ? 
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
                mode_release,
                approved_by,
                sub_category,
                rowid
            ))
        return True
    except Exception as e:
        print("Error updating person:", e)
        return False