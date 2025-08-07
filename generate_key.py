from license import generate_trial_key

if __name__ == "__main__":
    # Trial keys
    for days in [1, 2, 3, 5, 7, 30]:
        key = generate_trial_key(days)
        print(f"Trial {days} days key: {key}")

    # Lifetime key
    lifetime_key = generate_trial_key()
    print(f"Lifetime key: {lifetime_key}")

# Trial 1 days key: 4152afcd5b666c789422ebd77b608d1b89ef5b8aa966e88200a342f226e06bf7
# Trial 2 days key: 4d182290b214e352093931e6220bec9a9fb52c5ccd6d10a03549d8581042742e
# Trial 3 days key: 42220597ddecf8ea03bf47f8d899b0225815dd188b152fa9a30eb0a8b62924fc
# Trial 5 days key: 6890c2e5de7c46e8c3fa776bd4707080f6c0b1cfd2920725d2d6ac9d48d4e29a
# Trial 7 days key: 684cd41af02b4273dea28b18e7291eaba1ea3d3f1ba6aaf81a2da64f6d17d035
# Trial 30 days key: b244fc05658965e59221fe2535df0b215d75078a5d348ac08bcd8745c19df8c7
# Lifetime old key: 1bfbb8cbe67d2678ad1df8ff5e4c0dda2ecc760feef4761ab9a998aa4752b46c

# new b624dc45c8a2d7f5188a8d0a5c082ab135ff80e3e6096548cca4ab7c0dba82f3