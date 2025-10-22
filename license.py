import json
import os
import datetime
import hashlib
import platform

TRIAL_FILE = "license.json"      # File to store activation info
SECRET = "admin_secret_key_v2"   # Used to hash keys
LIFETIME_MARKER = "lifetime"     # Special marker for lifetime activation

# -------------------- Device ID --------------------
def get_device_id():
    """
    Generate a unique ID based on the device hardware info.
    Uses CPU, OS, and node name for uniqueness.
    """
    raw_info = f"{platform.node()}-{platform.system()}-{platform.processor()}"
    return hashlib.sha256(raw_info.encode()).hexdigest()

# -------------------- Key Hashing --------------------
def hash_data(expire_date, device_id):
    """
    Create a secure hash signature based on expire_date, device_id, and SECRET.
    """
    raw = expire_date + device_id + SECRET
    return hashlib.sha256(raw.encode()).hexdigest()

# -------------------- Key Generation --------------------
def generate_trial_key(days_valid=None, device_id=None):
    """
    Generate a device-bound trial or lifetime key.
    If days_valid is None, generate a lifetime key.
    """
    if device_id is None:
        device_id = get_device_id()

    if days_valid is None:
        raw_key = LIFETIME_MARKER + device_id + SECRET
    else:
        expire_date = (datetime.datetime.now() + datetime.timedelta(days=days_valid)).strftime("%Y-%m-%d")
        raw_key = expire_date + device_id + SECRET

    return hashlib.sha256(raw_key.encode()).hexdigest()

# -------------------- Save/Load Activation --------------------
def save_activation(expire_date):
    """
    Save activation data with hash to prevent tampering.
    """
    device_id = get_device_id()
    data = {
        "expire_date": expire_date,
        "device_id": device_id,
        "signature": hash_data(expire_date, device_id)
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
    stored_device_id = data.get("device_id")

    if not expire_date or not signature or not stored_device_id:
        return None  # Invalid file

    if stored_device_id != get_device_id():
        print("This license file is not for this device!")
        return None  # Wrong device

    if signature != hash_data(expire_date, stored_device_id):
        print("Trial file tampered!")
        return None  # Data has been modified

    return expire_date

# -------------------- Trial Validation --------------------
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

# -------------------- Activation --------------------
def activate_trial(input_key):
    """
    Validate the key and activate trial or lifetime if correct.
    """
    device_id = get_device_id()

    # Check for lifetime key first
    expected_lifetime_key = generate_trial_key(None, device_id)
    if input_key == expected_lifetime_key:
        save_activation(LIFETIME_MARKER)
        return True

    # Otherwise check for trial keys (1, 2, 3, 5, 7, 30 days)
    for days in [1, 2, 3, 5, 7, 14, 15, 21, 30]:
        expected_key = generate_trial_key(days, device_id)
        if input_key == expected_key:
            expire_date = (datetime.datetime.now() + datetime.timedelta(days=days)).strftime("%Y-%m-%d")
            save_activation(expire_date)
            return True

    return False

# -------------------- Example Usage --------------------
if __name__ == "__main__":
    if is_trial_valid():
        print("✅ Access granted! Enjoy using the app.")
    else:
        print("❌ Trial expired or not activated.")
        print(f"Your Device ID: {get_device_id()}")
        print(f"Sample Lifetime Key: {generate_trial_key()}")
        print(f"Sample 7-Day Key: {generate_trial_key(7)}")
        user_key = input("Enter trial or lifetime key: ").strip()
        if activate_trial(user_key):
            print("✅ Activation successful!")
        else:
            print("❌ Invalid key.")
