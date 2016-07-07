"""Two1 project variables."""
import os
import os.path


VERSION = (3, 5, 3)

__version__ = '.'.join(map(str, VERSION))


# Defines hard coded global variables
TWO1_VERSION = __version__
TWO1_VERSION_MESSAGE = '21 version %(version)s'
TWO1_USER_FOLDER = os.path.expanduser('~/.two1/')
TWO1_CONFIG_FILE = TWO1_USER_FOLDER + 'two1.json'
# two parents up from current dir
TWO1_BASE_DIR = os.path.abspath(os.path.join(os.path.abspath(__file__), os.pardir, os.pardir))


# simple logic to load the environment only once
if "env_loaded" not in locals():
    env_loaded = True

    # ensures the file exists
    dotenv_path = os.path.join(TWO1_BASE_DIR, ".env")
    if os.path.exists(dotenv_path):
        with open(dotenv_path, "rt") as f:
            for line in f:
                if not line or line.startswith('#') or '=' not in line:
                    continue
                key, value = line.strip().split('=', 1)
                value = value.strip("'").strip('"')
                os.environ.setdefault(key, value)


# Defines configurable global variables
TWO1_HOST = os.environ.get('TWO1_HOST', 'https://api.21.co')
TWO1_WWW_HOST = os.environ.get('TWO1_WWW_HOST', 'https://21.co')
TWO1_PROVIDER_HOST = os.environ.get('TWO1_PROVIDER_HOST', 'https://blockchain.21.co')
TWO1_PYPI_HOST = os.environ.get('TWO1_PYPI_HOST', 'https://pypi.python.org/')
TWO1_LOGGER_SERVER = os.environ.get('TWO1_LOGGER_SERVER', 'https://logger.21.co')
TWO1_POOL_URL = os.environ.get('TWO1_POOL_URL', 'swirl+tcp://grid.21.co:21006')
TWO1_DEVICE_ID = os.environ.get('TWO1_DEVICE_ID')
