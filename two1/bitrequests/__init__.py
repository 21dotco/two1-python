"""BitRequests wraps the python Requests library, adding a simple API for users
to pay for resources. It enables a client to pay a server for a resource. See
`docs/README.md` for more information.
"""
from .bitrequests import BitRequests  # noqa
from .bitrequests import BitTransferRequests
from .bitrequests import OnChainRequests
from .bitrequests import ChannelRequests

from .bitrequests import BitRequestsError  # noqa
from .bitrequests import UnsupportedPaymentMethodError  # noqa
from .bitrequests import ResourcePriceGreaterThanMaxPriceError  # noqa

OFF_CHAIN = 'offchain'
ON_CHAIN = 'onchain'
CHANNEL = 'channel'
_requests = {}
_current_method = OFF_CHAIN
_current_wallet = None


def use(payment_method=None, wallet=None):
    """Set the payment method to be used in the request."""
    global _current_method
    global _current_wallet

    if payment_method:
        if payment_method not in [OFF_CHAIN, ON_CHAIN, CHANNEL]:
            raise ValueError('Method not supported.')
        _current_method = payment_method

    if wallet:
        from two1.wallet import Two1Wallet, Wallet
        if not isinstance(wallet, Wallet) and not isinstance(wallet, Two1Wallet):
            raise ValueError('Invalid wallet type.')
        _current_wallet = wallet


def request(*args, payment_method=None, **kwargs):
    """Instantiate, or use a cached BitRequests object, and make a request."""
    global _requests
    global _current_method
    global _current_wallet
    payment_method = payment_method or _current_method

    if not _current_wallet:
        from two1.wallet import Wallet
        _current_wallet = Wallet()

    if payment_method not in _requests:
        if payment_method == OFF_CHAIN:
            from two1.server.machine_auth_wallet import MachineAuthWallet
            _requests[_current_method] = BitTransferRequests(MachineAuthWallet(_current_wallet))
        elif payment_method == ON_CHAIN:
            _requests[_current_method] = OnChainRequests(_current_wallet)
        elif payment_method == CHANNEL:
            _requests[_current_method] = ChannelRequests(_current_wallet)
        else:
            raise ValueError('That method is not supported.')

    return _requests[payment_method].request(*args, **kwargs)


def get(*args, **kwargs):
    return request('get', *args, **kwargs)


def put(*args, **kwargs):
    return request('put', *args, **kwargs)


def post(*args, **kwargs):
    return request('post', *args, **kwargs)


def delete(*args, **kwargs):
    return request('delete', *args, **kwargs)


def head(*args, **kwargs):
    return request('head', *args, **kwargs)
