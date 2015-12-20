import click
import json as jsonlib
from functools import update_wrapper
from two1.lib.util.exceptions import TwoOneError
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.util.uxstring import UxString


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
          result = f(config, *args, **kwargs)
        except TwoOneError as e:
            if (json):
                err_json = e._json
                err_json["error"] = e._msg
                click.echo(jsonlib.dumps(err_json, indent=4, separators=(',', ': ')))
            raise e
        else:
            if (json):
                click.echo(jsonlib.dumps(result, indent=4, separators=(',', ': ')))

        return result

    return update_wrapper(wrapper, f)


def check_notifications(func):
    """ Checks whether user has any notifications
    """

    def _check_notifications(config, *args, **kwargs):

        res = func(config, *args, **kwargs)

        try:
            client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                                     config.machine_auth,
                                                     config.username)
            notifications = client.get_notifications(config.username)
            notification_json = notifications.json()
            urgent_notifications = notification_json["urgent_count"]
            if urgent_notifications > 0:
                click.secho(UxString.unread_notifications.format(urgent_notifications))
        except:
            pass

        return res

    return update_wrapper(_check_notifications, func)
