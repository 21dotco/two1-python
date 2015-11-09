import click
import json as jsonlib
from functools import update_wrapper
from two1.lib.util.exceptions import TwoOneError

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
