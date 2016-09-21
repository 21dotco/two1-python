""" All command line related exceptions """
# standart python imports
import logging
import sys

# 3rd party imports
import click


# Creates a ClickLogger
logger = logging.getLogger(__name__)


class Two1Error(click.ClickException):
    """
    A ClickException with customized formatting.
    """

    def __init__(self, message, json=None):
        self.json = json if json else {}
        super(Two1Error, self).__init__(message)

    def format_message(self):
        return click.style(str(self.message), fg='red')

    def show(self, file=None):
        """
        Same as base method but without printing "Error: "
        """
        if file is None:
            file = sys.stderr
        click.echo(self.format_message(), file=file)


class UnloggedException(Two1Error):
    """ An error used to exit out of a commnad and not log the exception """


class MiningDisabledError(UnloggedException):
    """ A error indicating that the mining limit has been reached """


class UpdateRequiredError(UnloggedException):
    """ Error during a request os made and the client is out of date """


class FileDecodeError(Exception):
    """ Error when a config file cannot be decoded """


class ServerRequestError(Two1Error):
    """ Error during a request to a server """

    def __init__(self, message="", response=None, status_code=None, data=None):
        super(ServerRequestError, self).__init__(message)
        if response is not None:
            self.status_code = response.status_code
            try:
                self.data = response.json()
            except ValueError:
                self.data = {"error": "Request Error"}
        else:
            self.status_code = status_code
            self.data = data


class ServerConnectionError(Two1Error):
    """Error during a connection to a server"""

    def __init__(self, message=""):
        super(ServerConnectionError, self).__init__(message)


class BitcoinComputerNeededError(ServerRequestError):
    """ Error during a request made on a protected api """


class ValidationError(Two1Error):
    """ Manifest validation error occurs when parsing manifest file """
