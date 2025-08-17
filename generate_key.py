from license import generate_trial_key
import getpass

if __name__ == "__main__":
    try:
        password = getpass.getpass("Enter password: ")
        if password == "adminfcc":
            deviceId = input("Enter Device Id: ").strip()
            deviceIdArray = deviceId.split(":")
            print("-" * 100)
            print(f"deviceId: {deviceIdArray[0]} ")
            print("-" * 100)
            # Trial keys
            for days in [1, 2, 3, 5, 7, 14, 21, 30]:
                key = generate_trial_key(days, deviceIdArray[0])
                print(f"Trial {days} days key: {key}")
            print("-" * 100)
            if len(deviceIdArray) == 2 :
                lifetime_key = generate_trial_key()
                print(f"Lifetime key: {lifetime_key}")
                print("-" * 100)
            # Lifetime key

        else:
            print("Invalid Password.")
    finally:
        input("Press Enter to exit...")