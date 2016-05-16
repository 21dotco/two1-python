# 3rd party imports
import pytest

# two1 imports
import two1.commands.util.version as version


@pytest.mark.parametrize("actual_version, expected_version, return_value", [
    ("0.0.0", "0.0.1", False),
    ("0.0.0", "0.1.0", False),
    ("0.0.0", "1.0.0", False),
    ("0.0.1", "0.0.0", True),
    ("0.1.0", "0.0.0", True),
    ("1.0.0", "0.0.0", True),
    ("9.8.1", "9.8.1", True),
    ("3.0.0", "2.3.8", True),
    ("3.0.0", "3.0.0rc5", True),
    ('3.13.0-74-generic', '3.13.0', True),
    ('4.1.10-v7+', '4.0.0', True),
])
def test_is_version_gte(doctor, actual_version, expected_version, return_value):
    """ Ensures the logic of is_version_gte is correct and handle bad input """
    if isinstance(return_value, bool):
        assert version.is_version_gte(
            actual_version, expected_version) == return_value
    else:
        with pytest.raises(return_value):
            version.is_version_gte(actual_version, expected_version)
