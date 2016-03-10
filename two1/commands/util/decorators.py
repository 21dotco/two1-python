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

        # protect against early cli failures
        if ctx.obj and 'config' in ctx.obj:
            config = ctx.obj['config']
            config.set_json_output(json)

        try:
            result = f(ctx, *args, **kwargs)
        except exceptions.Two1Error as e:
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
        config = None
        client = None
        # protect against early cli failures
        if ctx.obj and 'config' in ctx.obj and 'client' in ctx.obj:
            config = ctx.obj['config']
            client = ctx.obj['client']

        res = func(ctx, *args, **kwargs)

        if client and config:
            notifications_resp = client.get_notifications(config.username)
            notification_json = notifications_resp.json()
            urgent_notifications = notification_json["urgent_count"]
            if urgent_notifications > 0:
                click.secho(uxstring.UxString.unread_notifications.format(urgent_notifications))

        return res

    return functools.update_wrapper(_check_notifications, func)


def capture_usage(func):
    """ Wraps a 21 CLI command in a function that logs usage statistics

    Args:
        func (function): function being decorated
    """
    def _capture_usage(ctx, *args, **kwargs):
        """ Captures usages and sends stastics to the 21 api if use opted in

        Args:
            ctx (click.Context): cli context object
            args (tuple): tuple of args of the fuction
            kwargs (dict): keyword args of the function
        """
        # protect against early cli failures
        if not ctx.obj or 'config' not in ctx.obj:
            return func(ctx, *args, **kwargs)

        config = ctx.obj['config']

        # return early if they opted out of sending usage stats
        if hasattr(config, "collect_analytics") and not config.collect_analytics:
            return func(ctx, *args, **kwargs)

        # add a default username if user is not logged in
        username = "unknown"
        if hasattr(config, "username"):
            username = config.username

        # log payload as a dict
        data = {
            "channel": "cli",
            "level": "info",
            "username": username,
            "command": func.__name__[1:],
            "platform": "{}-{}".format(platform.system(), platform.release()),
            "version" : two1.TWO1_VERSION
        }

        # send usage payload to the logging server
        requests.post(two1.TWO1_LOGGER_SERVER + "/logs", jsonlib.dumps(data))

        try:
            # call decorated function and propigate args
            return func(ctx, *args, **kwargs)

        # Don't log UnloggedExceptions to the server
        except exceptions.UnloggedException:
            return

        except Exception as ex:
            # protect against early cli failures
            if not ctx.obj or 'config' not in ctx.obj:
                raise ex

            # Add the errors to the data payload
            data['level'] = 'error'
            data['exception'] = traceback.format_exc()

            # send usage payload to the logging server
            requests.post(two1.TWO1_LOGGER_SERVER + "/logs", jsonlib.dumps(data))

            raise ex

    return functools.update_wrapper(_capture_usage, func)


def catch_all(func):
    """ Adds a safety net to functions that catches all exceptions

    Args:
        func (function): function being decorated
    """
    def _catch_all(ctx, *args, **kwargs):
        """ Catches all exceptions and prints the stacktrace if an environment variable is set

        Args:
            ctx (click.Context): cli context object
            args (tuple): tuple of args of the fuction
            kwargs (dict): keyword args of the function
        """
        try:
            return func(ctx, *args, **kwargs)

        # raise all click exceptions because they are used to bail and print a message
        except click.ClickException:
            raise

        except Exception:
            # generic error string
            click.echo(uxstring.UxString.Error.server_err)

            # only dump the stack traces if the debug flag is set
            if "TWO1_DEBUG" in  os.environ:
                click.secho("\nFunction: {}.{}".format(func.__module__, func.__name__), fg="red")
                click.secho("Args: {}".format(args), fg="red")
                click.secho("Kwargs: {}".format(kwargs), fg="red")
                click.secho("{}".format(traceback.format_exc()), fg="red")

    return functools.update_wrapper(_catch_all, func)
