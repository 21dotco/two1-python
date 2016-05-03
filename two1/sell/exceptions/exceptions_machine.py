""" `21 sell` machine exceptions.

Exceptions raised by the machine layer.

"""


class Two1MachineException(Exception):
    """ Base machine exception.
    """
    pass


# call super class with this message
class Two1MachineDoesNotExist(Two1MachineException):
    pass


class Two1MachineConnectionError(Two1MachineException):
    pass


class Two1MachineNotSupported(Two1MachineException):
    pass


class Two1MachineCreateException(Two1MachineException):
    pass


class Two1MachineDeleteException(Two1MachineException):
    pass


class Two1MachineStartException(Two1MachineException):
    pass


class Two1MachineStopException(Two1MachineException):
    pass


class Two1MachineNetworkStartException(Two1MachineException):
    pass


# Service composer exceptions.
class Two1SellException(Exception):
    pass


class Two1MachineExistException(Two1MachineException):
    pass


# Installer exceptions
class Two1InstallerException(Exception):
    pass
