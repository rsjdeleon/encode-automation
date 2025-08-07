import json
import os
import datetime
import hashlib

TRIAL_FILE = "license.json"  # File to store activation info
SECRET = "admin_secret_key_v2"      # Used to hash keys

LIFETIME_MARKER = "lifetime"    # Special marker for lifetime activation


def hash_data(expire_date):
    """
    Create a secure hash signature based on expire_date and SECRET.
    """
    raw = expire_date + SECRET
    return hashlib.sha256(raw.encode()).hexdigest()

def generate_trial_key(days_valid=None):
    """
    Generate a simple key.
    If days_valid is None, generate a lifetime key.
    """
    if days_valid is None:
        raw_key = LIFETIME_MARKER + SECRET
    else:
        expire_date = (datetime.datetime.now() + datetime.timedelta(days=days_valid)).strftime("%Y-%m-%d")
        raw_key = expire_date + SECRET

    return hashlib.sha256(raw_key.encode()).hexdigest()

def save_activation(expire_date):
    """
    Save activation data with hash to prevent tampering.
    """
    data = {
        "expire_date": expire_date,
        "signature": hash_data(expire_date)
    }
    with open(TRIAL_FILE, 'w') as f:
        json.dump(data, f)

def load_activation():
    """
    Load activation data and verify integrity.
    """
    if not os.path.exists(TRIAL_FILE):
        return None
    with open(TRIAL_FILE, 'r') as f:
        data = json.load(f)

    expire_date = data.get("expire_date")
    signature = data.get("signature")

    if not expire_date or not signature:
        return None  # Invalid file

    if signature != hash_data(expire_date):
        print("Trial file tampered!")
        return None  # Data has been modified

    return expire_date

def is_trial_valid():
    """
    Check if the trial period is still valid or lifetime activated.
    """
    expire_date = load_activation()
    if not expire_date:
        return False

    if expire_date == LIFETIME_MARKER:
        return True  # Lifetime access granted

    expire_date_dt = datetime.datetime.strptime(expire_date, "%Y-%m-%d")
    return datetime.datetime.now() <= expire_date_dt

def activate_trial(input_key):
    """
    Validate the key and activate trial or lifetime if correct.
    """
    # Check for lifetime key first
    expected_lifetime_key = generate_trial_key()
    if input_key == expected_lifetime_key:
        save_activation(LIFETIME_MARKER)
        return True

    # Otherwise check for trial keys (1, 2, 5 days)
    for days in [1, 2, 3, 5, 7, 30]:
        expected_key = generate_trial_key(days)
        if input_key == expected_key:
            expire_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            save_activation(expire_date)
            return True

    return False

# Example Usage
if __name__ == "__main__":
    if is_trial_valid():
        print("Access granted! Enjoy using the app.")
    else:
        print("Trial expired or not activated.")
        user_key = input("Enter trial or lifetime key: ").strip()
        if activate_trial(user_key):
            print("Activation successful!")
        else:
            print("Invalid key.")
