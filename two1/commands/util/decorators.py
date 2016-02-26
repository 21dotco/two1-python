# standard python imports
import os
import json as jsonlib
import functools
import platform
import traceback

# 3rd party imports
import requests
import click

# two1 imports
import two1
import two1.commands.util.uxstring as uxstring
import two1.commands.util.exceptions as exceptions
import two1.lib.server.rest_client as rest_client


def docstring_parameter(*args, **kwargs):
    def dec(obj):
        obj.__doc__ = obj.__doc__.format(*args, **kwargs)
        return obj
    return dec


def json_output(f):
    """Allows the return value to be optionally returned as json output
       with the '--json' flag."""
    @click.option('--json',
              default=False,
              is_flag=True,
              help='Uses JSON output.')
    @click.pass_context
    def wrapper(ctx, json, *args, **kwargs):
        config = ctx.obj['config']
        config.set_json_output(json)
        try:
            result = f(ctx, *args, **kwargs)
        except exceptions.TwoOneError as e:
            if (json):
                err_json = e._json
                err_json["error"] = e._msg
                click.echo(jsonlib.dumps(err_json, indent=4, separators=(',', ': ')))
            raise e
        else:
            if (json):
                click.echo(jsonlib.dumps(result, indent=4, separators=(',', ': ')))

        return result

    return functools.update_wrapper(wrapper, f)


def check_notifications(func):
    """ Checks whether user has any notifications
    """

    def _check_notifications(ctx, *args, **kwargs):
        config = ctx.obj['config']
        client = ctx.obj['client']
        res = func(ctx, *args, **kwargs)

        try:
            notifications = client.get_notifications(config.username)
            notification_json = notifications.json()
            urgent_notifications = notification_json["urgent_count"]
            if urgent_notifications > 0:
                click.secho(UxString.unread_notifications.format(urgent_notifications))
        except:
            pass

        return res

    return functools.update_wrapper(_check_notifications, func)


def capture_usage(func):
    """ Wraps a 21 CLI command in a function that logs usage statistics

    Args:
        func (function): function being decorated
    """
    def _capture_usage(ctx, *args, **kw):
        """ Captures usages and sends stastics to the 21 api if use opted in

        Args:
            ctx (click.Context): cli context object
            args (tuple): tuple of args of the fuction
            kwargs (dict): keyword args of the function
        """
        config = ctx.obj['config']

        if hasattr(config, "username"):
            username = config.username
        else:
            username = "unknown"

        try:
            if config.collect_analytics:
                func_name = func.__name__[1:]
                username = config.username
                user_platform = platform.system() + platform.release()
                username = username or "unknown"
                data = {
                    "channel": "cli",
                    "level": "info",
                    "username": username,
                    "command": func.__name__[1:],
                    "platform": "{}-{}".format(platform.system(), platform.release()),
                    "version" : two1.TWO1_VERSION
                }
                _log_message(data)

            res = func(ctx, *args, **kw)

            return res

        except exceptions.ServerRequestError as ex:
            click.echo(uxstring.UxString.Error.request)

        except exceptions.ServerConnectionError:
            click.echo(uxstring.UxString.Error.connection.format("21 Servers"))

        # don't log UnloggedExceptions
        except exceptions.UnloggedException:
            return
        except click.ClickException:
            raise

        except Exception as e:
            is_debug = _str2bool(os.environ.get("TWO1_DEBUG", False))
            tb = traceback.format_exc()
            if config.collect_analytics:
                data = {
                    "channel": "cli",
                    "level": "error",
                    "username": username,
                    "command": func_name,
                    "platform": user_platform,
                    "version": two1.TWO1_VERSION,
                    "exception": tb}
                _log_message(data)
            click.echo(uxstring.UxString.Error.server_err)
            if is_debug:
                raise e

    return functools.update_wrapper(_capture_usage, func)


def _str2bool(v):
    """Convenience method for converting from string to boolean."""
    return str(v).lower() == "true"


def _log_message(message):
    """Send the payload to the logging server."""
    url = two1.TWO1_LOGGER_SERVER + "/logs"
    message_str = jsonlib.dumps(message)
    requests.request("post", url, data=message_str)
