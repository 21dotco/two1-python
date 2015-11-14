import click
import json
import platform
import traceback
import os
import requests
from functools import update_wrapper
from two1.commands import config as app_config
from two1.lib.util.exceptions import UnloggedException
from two1.lib.util.uxstring import UxString
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.server.rest_client import ServerConnectionError


def capture_usage(func):
    def _capture_usage(config, *args, **kw):

        try:
            if config.collect_analytics:
                func_name = func.__name__[1:]
                username = config.username
                user_platform = platform.system() + platform.release()
                # we can separate between updates
                version = app_config.TWO1_VERSION
                data = {
                    "channel": "cli",
                    "level": "info",
                    "username": username,
                    "command": func_name,
                    "platform": user_platform,
                    "version" : version
                }
                log_message(data)

            res = func(config, *args, **kw)

            return res

        except ServerRequestError as e:
            click.echo(str(next(iter(e.data.values()))) + "({})".format(e.status_code))

        except ServerConnectionError:
            click.echo(UxString.Error.connection.format("21 Servers"))

        # don't log UnloggedExceptions
        except UnloggedException:
            return
        except click.ClickException:
            raise

        except Exception as e:
            is_debug = str2bool(os.environ.get("TWO1_DEBUG", False))
            tb = traceback.format_exc()
            data = {
                "channel": "cli",
                "level": "error",
                "username": username,
                "command": func_name,
                "platform": user_platform,
                "exception": tb}
            if config.collect_analytics:
                log_message(data)
            click.echo(UxString.Error.server_err)
            if is_debug:
                raise e

    return update_wrapper(_capture_usage, func)


def str2bool(v):
    return str(v).lower() == "true"


def log_message(message):
    url = app_config.TWO1_LOGGER_SERVER + "/logs"
    message_str = json.dumps(message)
    requests.request("post", url, data=message_str)
    # TODO log a better error message in case of an uncaught exception
