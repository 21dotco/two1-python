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


class ServerRequestError(Exception):
    pass


class ServerConnectionError(Exception):
    pass

