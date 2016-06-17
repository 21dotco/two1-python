import os
import os.path

BASE_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir))


# simple logic to load the environment only once
if "env_loaded" not in locals():
    env_loaded = True

    # ensures the file exists
    dotenv_path = os.path.join(BASE_DIR, ".env")
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "rt") as f:
            for line in f:
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.strip().split('=', 1)
                value = value.strip("'").strip('"')
                os.environ.setdefault(key, value)

