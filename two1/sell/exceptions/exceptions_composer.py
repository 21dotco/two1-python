class Two1ComposerException(Exception):
    """ Base composer exception.
    """
    pass


class Two1ComposerConnectionException(Two1ComposerException):
    pass


class Two1ComposerWalletCreationException(Two1ComposerException):
    pass


class Two1ComposerRouteException(Two1ComposerException):
    pass


class Two1ComposerBuildException(Two1ComposerException):
    pass


class Two1ComposerRouterException(Two1ComposerException):
    pass


class Two1ComposerStartException(Two1ComposerException):
    pass


class Two1ComposerStopException(Two1ComposerException):
    pass


class Two1ComposerServiceDefinitionException(Two1ComposerException):
    pass
