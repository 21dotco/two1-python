"""Utils for 21 version."""
import requests
import urllib.parse as parse
from pkg_resources import parse_version
from pkg_resources import SetuptoolsVersion
from distutils.version import LooseVersion

import two1


def get_latest_two1_version_pypi():
    """ Fetch latest version of two1 from pypi.

    Returns:
        latest_version (str): latest version of two1
    """
    url = parse.urljoin(two1.TWO1_PYPI_HOST, "pypi/two1/json")
    response = requests.get(url)
    return response.json()['info']['version']


def is_version_gte(actual, expected):
    """ Checks two versions for actual >= epected condition

        Versions need to be in Major.Minor.Patch format.

    Args:
        actual (str): the actual version being checked
        expected (str): the expected version being checked

    Returns:
        bool: True if the actual version is greater than or equal to
            the expected version.

    Raises:
        ValueError: if expected ot actual version is not in Major.Minor.Patch
            format.
    """
    if isinstance(parse_version(actual), SetuptoolsVersion):
        # This handles versions that end in things like `rc0`
        return parse_version(actual) >= parse_version(expected)
    else:
        # This handles versions that end in things like `-v7+` and `-generic`
        return LooseVersion(actual) >= LooseVersion(expected)
