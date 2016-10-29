""" All two1 command line related decorators """
import functools
import json as jsonlib
import logging
import platform
import sys
import traceback

import requests
import click

import two1
import two1.commands.util.uxstring as uxstring
import two1.commands.util.exceptions as exceptions


# Creates a ClickLogger
logger = logging.getLogger(__name__)


def json_output(f):
    """ Allows the return value to be optionally returned as json
    output with the '--json' flag.

    When a command fails but still has data to be printed as json, a
    Two1Error should be raised because it takes an optional json
    param. This means we can pass any json data using the Two1Error as
    a vehicle to "return" the json data to this decorator to allow
    printing. This design was motivated by the `21 doctor` command
    because when a doctor check fails it raises an exception and
    passes the results using the exception.

    This could be changed to to have the return value expect a key of
    "error" in the case of an error but since two1 uses exceptions to
    halt execution this design makes sense.
    """

    @click.option('--json', default=False, is_flag=True, help='Uses JSON output.')
    def _json_output(ctx, json, *args, **kwargs):
        """ This wrapper disables logging when json is set and restores it after print json value

            In order for this to work ALL output printed to console needs to be done through
            a logger.
        """
        # call early if --json wasn't given as a cmd line arg
        if not json:
            return f(ctx, *args, **kwargs)

        # gets the original level so the decorator can restore it
        original_level = logging.getLogger('').manager.disable

        # disables ALL log messages critical and below
        logging.disable(logging.CRITICAL)

        try:
            result = f(ctx, *args, **kwargs)
        except exceptions.Two1Error as ex:
            # sets the level back to original
            logging.disable(original_level)

            err_json = ex.json or {}
            err_json["error"] = ex.message

            # dumps the json error
            logger.info(jsonlib.dumps(err_json, indent=4, separators=(',', ': ')))

            raise ex
        else:
            # sets the level back to original
            logging.disable(original_level)

            # dumps the json result
            logger.info(jsonlib.dumps(result, indent=4, separators=(',', ': ')))

        return result

    return functools.update_wrapper(_json_output, f)


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
                logger.info(uxstring.UxString.unread_notifications.format(urgent_notifications))

        return res

    return functools.update_wrapper(_check_notifications, func)


def get_full_name(ctx):
    """
    Return the fully qualified name of the command.

    >>> main_ctx = click.Context(click.Command('main'))
    >>> market_ctx = click.Context(click.Command('market'), parent=main_ctx)
    >>> join_ctx = click.Context(click.Command('join'), parent=market_ctx)
    >>> get_full_name(join_ctx)
    '21_market_join'
    """
    if ctx.parent is None:  # This is `two1.cli.main`
        return '21'
    else:
        return get_full_name(ctx.parent) + '_' + ctx.command.name


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

        def _send_to_logger(data):
            try:
                # send usage payload to the logging server
                requests.post(two1.TWO1_LOGGER_SERVER + "/logs", jsonlib.dumps(data))
            except Exception as e:
                # ignore failures if not in debug mode since logging failure shouldn't be visible
                # to normal flow of the user.
                if ctx.obj['debug']:
                    raise e

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
            "command": get_full_name(ctx),
            "params": ctx.params,
            "platform": "{}-{}".format(platform.system(), platform.release()),
            "version": two1.TWO1_VERSION
        }

        # do not post a file to our logger.
        if 'data_file' in data['params']:
            data['params']['data_file'] = str(data['params']['data_file'])
        # send usage payload to the logging server
        _send_to_logger(data)

        try:
            # call decorated function and propigate args
            return func(ctx, *args, **kwargs)

        # Don't log UnloggedExceptions to the server
        except exceptions.UnloggedException:
            raise

        except Exception as ex:
            # protect against early cli failures
            if not ctx.obj or 'config' not in ctx.obj:
                raise ex

            # elevate the level to 'error'
            data['level'] = 'error'
            data['exception'] = traceback.format_exc()

            # add json data and message from a Two1Error to the data payload
            if isinstance(ex, exceptions.Two1Error) and hasattr(ex, "_json"):
                data['json'] = ex.json
                data['message'] = ex.message

            # send usage payload to the logging server
            _send_to_logger(data)

            raise ex

    return functools.update_wrapper(_capture_usage, func)


def catch_all(func):
    """
    Catch (nearly) all exceptions unless in debug mode.

    Args:
        func (function): function being decorated
    """
    def _catch_all(ctx, *args, **kwargs):
        """
        Args:
            ctx (click.Context): cli context object
            args (tuple): tuple of args of the fuction
            kwargs (dict): keyword args of the function
        """
        def stderr(msg):
            click.echo(click.style(msg, fg='red'), file=sys.stderr)
        try:
            return func(ctx, *args, **kwargs)
        except click.Abort:
            # on SIGINT click.prompt raises click.Abort
            logger.error('')  # just to get a newline

        except click.ClickException:
            raise  # Let click deal with it

        except Exception:
            # generic error string
            stderr(
                'You have experienced a client-side technical error.')

            # only dump the stack traces if the debug flag is set
            if kwargs.get('debug') or ctx.obj['debug']:
                stderr("\nFunction: {}.{}".format(func.__module__, func.__name__))
                stderr("Args: {}".format(args))
                stderr("Kwargs: {}".format(kwargs))
                stderr("{}".format(traceback.format_exc()))
            else:
                stderr(
                    'For more detail, run your command with the debug flag: '
                    '`21 --debug <command>.`')
        sys.exit(1)

    return functools.update_wrapper(_catch_all, func)
