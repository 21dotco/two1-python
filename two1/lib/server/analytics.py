import click
import json
import platform
import traceback
import requests
from two1.commands import config as app_config
from two1.lib.util.uxstring import UxString


def capture_usage(func):
    def _capture_usage(*args, **kw):

        try:
            func_name = func.__name__[1:]
            config = args[0]
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

            res = func(*args, **kw)

            return res

        except Exception as e:
            tb = traceback.format_exc()
            data = {
                "channel": "cli",
                "level": "error",
                "username": username,
                "command": func_name,
                "platform": user_platform,
                "version": version,
                "exception": tb}
            log_message(data)
            click.echo(UxString.Error.server_err)
            if app_config.TWO1_DEV:
                raise e

    return _capture_usage


def log_message(message):
    url = app_config.TWO1_LOGGER_SERVER + "/logs"
    message_str = json.dumps(message)
    requests.request("post", url, data=message_str)
