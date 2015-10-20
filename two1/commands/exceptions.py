class ServerRequestError(Exception):
    pass


class ServerUnavailable(Exception):
    pass


class ServerConnectionError(Exception):
    pass


class ServerTimeout(Exception):
    pass
