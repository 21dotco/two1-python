'''
    Generic utility functions used by both the 21 CLI and the wallet CLI.
'''
from datetime import datetime
from datetime import timezone


def format_date(unix_timestamp):
    """ Return a standardized date format for use in the two1 library.

    This function produces a localized datetime string that includes the UTC timezone offset. This offset is
    computed as the difference between the local version of the timestamp (python's datatime.fromtimestamp)
    and the utc representation of the input timestamp.

    Args:
        unix_timestamp (float): a floating point unix timestamp

    Returns:
        string: A string formatted with "%Y-%m-%d %H:%M:%S %Z"
    """

    local_datetime = datetime.fromtimestamp(unix_timestamp)
    utz_offset = local_datetime - datetime.utcfromtimestamp(unix_timestamp)
    local_date = local_datetime.replace(
        tzinfo=timezone(utz_offset)
    ).strftime("%Y-%m-%d %H:%M:%S %Z")

    return local_date
