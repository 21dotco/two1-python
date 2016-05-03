""" Unit test to verify logger functionality """
# standard python imports
import logging
import io
import unittest.mock as mock
import subprocess

# 3rd party imports
import click
import pytest

# two1 imports
import two1.commands.util.logger as _logger
from two1.commands.util.logger import LESS_ENV


# Creates a ClickLogger
logger = logging.getLogger("{}.{}".format("two1", __name__))


def test_logger_import():
    """ Checks the root logger to ensure the handler and formatter are set correctly """
    # checks the logger is an instance of ClickLogger
    assert isinstance(logger, _logger.ClickLogger)

    # checks two1 logger for handler and formatter
    root_logger = logging.getLogger("two1")
    assert len(root_logger.handlers) == 1
    assert isinstance(root_logger.handlers[0], _logger.ClickLogHandler)
    assert isinstance(root_logger.handlers[0].formatter, _logger.ClickLogFormatter)

    # checks that this module logger soes NOT have a handler
    assert len(logger.handlers) == 0


@pytest.mark.parametrize("level, log_cmd, should_call", [
    # debug level is less than info
    (logging.DEBUG, "info", True),

    # same level logs do NOT work when using disable
    (logging.INFO, "info", False),

    # Critical is higher than info
    (logging.CRITICAL, "info", False),

    # 60 is greater than critical level
    (60, "critical", False),
    ])
def test_disable_levels(patch_click, level, log_cmd, should_call):
    """ Test to ensure that the ClickLogger adheres to logging levels """
    # gets the original disabled level from the root manager
    original_level = logging.getLogger('').manager.disable

    try:
        # Sets global logging level
        logging.disable(level)

        # ensure the command exists
        assert hasattr(logger, log_cmd)

        # logs a test string to the spceified command
        getattr(logger, log_cmd)("test")

        # ensure click.echo is called or not
        if should_call:
            click.echo.assert_called_with("test")
        else:
            click.echo.assert_not_called()
    except:
        # sets the level back to original
        logging.disable(original_level)
        raise
    else:
        # sets the level back to original
        logging.disable(original_level)


@pytest.mark.parametrize("message, kwargs, supported", [
    # forground
    ("test", dict(fg="red"), True),
    ("", dict(fg="red"), True),

    # background
    ("test", dict(bg="magenta"), True),
    ("", dict(bg="magenta"), True),

    # bold
    ("test", dict(bold=True), True),
    ("", dict(bold=True), True),

    # dim
    ("test", dict(bold=True), True),
    ("", dict(bold=True), True),

    # underline
    ("test", dict(bold=True), True),
    ("", dict(bold=True), True),

    # reverse
    ("test", dict(bold=True), True),
    ("", dict(bold=True), True),

    # not supported param
    ("test", dict(not_supported=True), False),
    ("", dict(not_supported=True), False),

    # multiple params
    ("test", dict(bold=True, fg="red"), True),
    ("", dict(bold=True, fg="red"), True),
    ])
def test_styles(patch_click, message, kwargs, supported):
    """ Test to ensure the ClickLogger is sytling messges correctly """
    # uses click.style to make the expected formatted string
    if supported:
        expected_output = click.style(message, **kwargs)
    else:
        expected_output = message

    # logs the message with the given kwargs
    logger.info(message, **kwargs)

    # ensure the formatted string is the same as what click would have done
    click.echo.assert_called_with(expected_output)


@pytest.mark.parametrize("message, kwargs, expected_output", [
    # add a newline character
    ("test", dict(nl=False), "test"),
    ("", dict(nl=True), ""),

    # log to stderr
    ("test", dict(err=True), "test"),
    ("", dict(err=True), ""),

    # color
    (click.style("test", "red"), dict(color=True), click.style("test", "red")),
    (click.style("test", "red"), dict(color=False), "test"),

    # use a stringio file to check file kwarg
    ("test", dict(file=io.StringIO()), "test"),

    # multiple params
    (click.style("test", "red"), dict(nl=False, color=True), click.style("test", "red")),

    # not supported param
    ("test", dict(not_supported=True), "test"),
    ])
def test_echo(capsys, message, kwargs, expected_output):
    """ Echo test to ensure the kwargs are being passed to click.echo correctly """
    # logs the message with the given kwargs
    logger.info(message, **kwargs)

    # add the newline char here to avoind the newline getting printed in pytest output
    if 'nl' not in kwargs or kwargs['nl']:
        expected_output = "{}\n".format(expected_output)

    if kwargs.get("file", False):
        assert expected_output == kwargs['file'].getvalue()
    else:
        out, err = capsys.readouterr()
        if kwargs.get("err", False):
            assert err == expected_output
        else:
            assert out == expected_output


# patch these to make click to think the captured std io file descriptors are legit
@mock.patch("sys.stdin.isatty", return_value=True)
@mock.patch("sys.stdout.isatty", return_value=True)
def test_pager(patch_stdout, patch_stdin, monkeypatch):
    """ Pager test to ensure the pager is getting called AND that the env is getting set correctly """
    # click does some thing where it looks for an encoding type. Set a default value here as a workaround
    mock_popen = mock.Mock()
    mock_popen.stdin.encoding = ''

    # patch subprocess.Popen as a mock which returns another mock object
    monkeypatch.setattr(subprocess, "Popen", mock.Mock(return_value=mock_popen))

    # log to the pager
    logger.info("this will go to a pager", pager=True)

    # check to ensure that the subprocess was called and that the correct env was set for PAGER and LESS
    assert subprocess.Popen.called
    assert "env" in subprocess.Popen.call_args[1]
    assert "PAGER" in subprocess.Popen.call_args[1]['env']
    assert "less" in subprocess.Popen.call_args[1]['env']['PAGER']
    assert LESS_ENV in subprocess.Popen.call_args[1]['env']['LESS']
