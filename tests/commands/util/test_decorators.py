# standard python imports
import json
import logging

# 3rd party imports
import click
import pytest

# two1 imports
import two1.commands.util.decorators as decorators
import two1.commands.util.exceptions as exceptions


# Creates a ClickLogger
logger = logging.getLogger("{}.{}".format("two1", __name__))


@pytest.mark.parametrize("json_flag, output, return_value, side_effect", [
    # should print to screen
    (False, "test", None, None),

    # json set so output is swallowed and the return value is printed
    (True, "test", {"test": "json"}, None),
    (True, "test", None, None),

    # error conditions where a Two1Error occurs
    (True, "test", {"test": "json"}, exceptions.Two1Error)
    ])
def test_json_ouput(patch_click, json_flag, output, return_value, side_effect):

    @decorators.json_output
    def _fake_command(ctx, *args, **kwargs):
        logger.info(output)

        if side_effect:
            raise side_effect(message='', json=return_value)

        return return_value

    # check for exception if command is going to fail
    if side_effect:
        with pytest.raises(side_effect) as ex:
            _fake_command(object(), json=json_flag)

        assert ex.value.json == return_value
    else:
        assert _fake_command(object(), json=json_flag) == return_value

    # json is false then the output will be printed to screen
    if not json_flag:
        click.echo.assert_called_once_with(output)
    else:
        click.echo.assert_called_once_with(json.dumps(return_value, indent=4, separators=(',', ': ')))
