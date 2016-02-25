"""Utility functions for user accounts."""
import sys

from two1.commands.util import uxstring
from two1.lib.server import login
from two1.lib.blockchain import exceptions as bc_exceptions
from two1.commands.util import exceptions as cmd_exceptions


def get_or_create_username(config):
    """Create a new wallet or return the currently existing one."""
    try:
        login.check_setup_twentyone_account(config)
    except bc_exceptions.DataProviderUnavailableError:
        raise cmd_exceptions.TwoOneError(uxstring.UxString.Error.connection_cli)
    except bc_exceptions.DataProviderError:
        raise cmd_exceptions.TwoOneError(uxstring.UxString.Error.server_err)
    except cmd_exceptions.UnloggedException:
        sys.exit(1)

    if not config.username:
        sys.exit(1)
    return config.username
