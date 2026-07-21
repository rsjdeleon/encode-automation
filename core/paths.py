import os


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def root_path(*parts):
    return os.path.join(BASE_DIR, *parts)


CONFIG_DB_PATH = root_path("config.db")
PERSON_DB_PATH = root_path("person-record.db")
WORKER_DB_PATH = root_path("worker.db")

LICENSE_FILE_PATH = root_path("license.json")
FORM_CACHE_FILE_PATH = root_path("data-new.pkl")
CRASH_LOG_FILE_PATH = root_path("crash.log")
