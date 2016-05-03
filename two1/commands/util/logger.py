""" Logger module which when imported changes the default logger class to ClickLogger

    The two1 command line tool is heavily dependent upon click for calling commands
    and also for printing to the console using click.echo() & click.style() functions.
    Importing `two1.commands.util.logger`, changes the default class created during
    `logging.getLogger()` to ClickLogger.
"""
# standard python imports
import os
import logging

# 3rd party imports
import click

# two1 imports
LESS_ENV = '-RPpress h for help, q for quit'


class ClickLogFormatter(logging.Formatter):
    """ Styles messages by calling click.style() """

    # supported click styles
    STYLES = ("fg", "bg", "bold", "dim", "underline", "reverse", "reset", "blink")

    def format(self, record):
        """ Formats the record.msg string by using click.style()

            The record will have attributes set to it when a user logs a message
            with any kwargs given. This function looks for any attributes that
            are in STYLES. If record has any sytle attributes, the record will
            be styled with the given sytle. This makes click logging with a logger very easy.

        Args:
            record (logging.LogRecord): record which gets styled with click.style()
        """
        # Sets the default kwargs
        kwargs = dict()

        # checks if any click args were passed along in the logger
        for kwarg_name in self.STYLES:
            if hasattr(record, kwarg_name):
                kwargs[kwarg_name] = getattr(record, kwarg_name)

        # styles the message of the record if a style was given
        if kwargs:
            record.msg = click.style(record.msg, **kwargs)

        return record


class ClickLogHandler(logging.Handler):
    """ Logs messages using click.echo() """

    ECHO_KWARGS = ("nl", "err", "color", "file")

    def emit(self, record):
        """ Echos the record.msg string by using click.echo()

            The record will have attributes set to it when a user logs a message
            with any kwargs given. This function looks for any attributes that
            are in ECHO_KWARGS. If record has any kwargs attributes, the record will
            be echoed with the given kwargs. This makes click logging with a logger very easy.

            A user can add {"pager": True} as an extra param to any of the log commands to print
            the content to a pager.

        Args:
            record (logging.LogRecord): record which gets echoed with click.echo()
        """
        try:
            # first format the record which adds the click style
            formatted_record = self.format(record)

            # user wants to use a pager to show message
            if hasattr(record, "pager") and record.pager:
                # save the original eviron dict
                original_env = dict(os.environ)

                # Force system to use pager and add default prompt at bottom left of the screen
                os.environ['PAGER'] = "less"
                os.environ['LESS'] = LESS_ENV
                try:
                    click.echo_via_pager(formatted_record.msg,
                                         color=record.color if hasattr(record, "color") else None)

                # being paranoid here because we do NOT want to mess with people's environment
                except:
                    os.environ.clear()
                    os.environ.update(original_env)
                    raise
                else:
                    os.environ.clear()
                    os.environ.update(original_env)
            else:
                # Sets the default kwargs
                kwargs = dict()

                # if user added a known kwarg, change the defaults
                for kwarg_name in self.ECHO_KWARGS:
                    if hasattr(record, kwarg_name):
                        kwargs[kwarg_name] = getattr(record, kwarg_name)

                # echo to console
                click.echo(formatted_record.msg, **kwargs)
        except (KeyboardInterrupt, SystemExit):
            raise
        except:
            self.handleError(record)


class ClickLogger(logging.getLoggerClass()):
    """ Logging class which handles click input and adds it to the extra param

        By specifying an extra dict to the log functions, the record will have the
        given key-value pair as an attribute making for easy to style and echo records.
    """

    def debug(self, msg, *args, **kwargs):
        """ Calls Logger.debug with extra set to kwargs """
        super(ClickLogger, self).debug(msg, *args, extra=kwargs)

    def info(self, msg, *args, **kwargs):
        """ Calls Logger.info with extra set to kwargs """
        super(ClickLogger, self).info(msg, *args, extra=kwargs)

    def warning(self, msg, *args, **kwargs):
        """ Calls Logger.warning with extra set to kwargs """
        super(ClickLogger, self).warning(msg, *args, extra=kwargs)

    def error(self, msg, *args, **kwargs):
        """ Calls Logger.error with extra set to kwargs """
        super(ClickLogger, self).error(msg, *args, extra=kwargs)

    def critical(self, msg, *args, **kwargs):
        """ Calls Logger.critical with extra set to kwargs """
        super(ClickLogger, self).critical(msg, *args, extra=kwargs)


# creates the handler which prints records
click_log_handler = ClickLogHandler()

# creates the formatter which styles the records
click_log_handler.formatter = ClickLogFormatter()

# captures the second most senior logger
click_logger = logging.getLogger('two1')

# adds the handler, formatter, and sets default level to the second lowest
click_logger.addHandler(click_log_handler)
click_logger.setLevel(logging.INFO)
logging.setLoggerClass(ClickLogger)
