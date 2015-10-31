import click
import json
import platform
import traceback
import requests
from two1.commands import config as app_config
from two1.lib.util.uxstring import UxString
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.server.rest_client import ServerConnectionError



def capture_usage(func):
    def _capture_usage(*args, **kw):

        try:
            func_name = func.__name__[1:]
            config = args[0]
            username = config.username
            user_platform = platform.system() + platform.release()
            # TODO we should add a version field to two1.json and log it here, that way
            # we can separate between updates
            data = {
                "channel": "cli",
                "level": "info",
                "username": username,
                "command": func_name,
                "platform": user_platform
            }
            log_message(data)

            res = func(*args, **kw)

            return res

        except ServerRequestError as e:
            click.echo(str(next(iter(e.data.values()))) + "({})".format(e.status_code))

        except ServerConnectionError:
            click.echo(UxString.Error.connection.format("21 Servers"))

        except click.ClickException:
            raise

        except Exception as e:
            tb = traceback.format_exc()
            data = {
                "channel": "cli",
                "level": "error",
                "username": username,
                "command": func_name,
                "platform": user_platform,
                "exception": tb}
            log_message(data)
            click.echo(UxString.Error.server_err)
            if app_config.DEBUG_MODE:
                raise e

    return _capture_usage


def log_message(message):
    url = app_config.TWO1_LOGGER_SERVER + "/logs"
    message_str = json.dumps(message)
    requests.request("post", url, data=message_str)
    # TODO log a better error message in case of an uncaught exception
