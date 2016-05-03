# 3rd party imports
import pytest

# two1 imports
from two1.sell.util.client_helpers import get_platform


@pytest.fixture()
def sys_platform():
    """ Fixture that gets system platform metadata.
    """
    return get_platform()
