import click


class TwoOneError(click.ClickException):
    def __init__(self, msg, json={}):
        self._msg = msg
        self._json = json
        super(TwoOneError, self).__init__(self._msg)

    def __str__(self):
        return self._msg


class UnloggedException(Exception):
    pass


class MiningDisabledError(UnloggedException):
    pass
