"""Two1 project variables."""
import os
import os.path


try:
    from two1.version import VERSION as version
except ImportError:
    try:
        from two1.commands.util.mkrelease import get_version_from_git
        version = get_version_from_git()
    except:
        raise Exception('Version not found. Is there a tag available?')

# Define all project global variables
TWO1_VERSION = version
TWO1_PACKAGE_NAME = 'two1'
TWO1_USER_FOLDER = os.path.expanduser('~/.two1/')
TWO1_CONFIG_FILE = TWO1_USER_FOLDER + 'two1.json'
TWO1_HOST = os.environ.get('TWO1_HOST', 'https://api.21.co')
TWO1_PROVIDER_HOST = os.environ.get('TWO1_PROVIDER_HOST', 'https://blockchain.21.co')
TWO1_PYPI_HOST = os.environ.get('TWO1_PYPI_HOST', 'https://pypi-3844.21.co')
TWO1_LOGGER_SERVER = os.environ.get('TWO1_LOGGER_SERVER', 'http://logger.21.co')
TWO1_POOL_URL = os.environ.get('TWO1_POOL_URL', 'swirl+tcp://grid.21.co:21006')
TWO1_MERCHANT_HOST = os.environ.get('TWO1_MERCHANT_HOST', 'http://market.21.co')
TWO1_DEVICE_ID = os.environ.get('TWO1_DEVICE_ID')
