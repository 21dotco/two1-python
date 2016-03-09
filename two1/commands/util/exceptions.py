import click


class TwoOneError(click.ClickException):
    def __init__(self, msg, json={}):
        self._msg = msg
        self._json = json
        super(TwoOneError, self).__init__(self._msg)

    def __str__(self):
        return self._msg

    def show(self, file=None):
        click.echo(str(self.format_message()), file=file)


class UnloggedException(TwoOneError):
    pass


class MiningDisabledError(UnloggedException):
    pass


class UpdateRequiredError(UnloggedException):
    pass


class BitcoinComputerNeededError(UnloggedException):
    pass


class ConfigError(Exception):
    pass


class FileDecodeError(ConfigError):
    pass


class ServerRequestError(click.ClickException):
    """ Error during a request to a server """

    def __init__(self, msg="", response=None, status_code=None, data=None):
        super(ServerRequestError, self).__init__(msg)
        if response:
            self.status_code = response.status_code
            try:
                self.data = response.json()
            except ValueError:
                self.data = {"error": "Request Error"}
        else:
            self.status_code = status_code
            self.data = data


class ServerConnectionError(click.ClickException):
    """Error during a connection to a server"""

    def __init__(self, msg=""):
        super(ServerConnectionError, self).__init__(msg)
