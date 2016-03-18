"""BitRequests wraps the python Requests library, adding a simple API for users
to pay for resources. It enables a client to pay a server for a resource. See
`docs/README.md` for more information.
"""
from .bitrequests import BitRequests
from .bitrequests import BitTransferRequests
from .bitrequests import OnChainRequests
from .bitrequests import ChannelRequests

from .bitrequests import BitRequestsError
from .bitrequests import UnsupportedPaymentMethodError
from .bitrequests import ResourcePriceGreaterThanMaxPriceError

OFF_CHAIN = 'offchain'
ON_CHAIN = 'onchain'
CHANNEL = 'channel'
_requests = {}
_current_method = OFF_CHAIN


def use(payment_method):
    """Set the payment method to be used in the request."""
    global _current_method
    if payment_method not in [OFF_CHAIN, ON_CHAIN, CHANNEL]:
        raise ValueError('That method is not supported.')
    _current_method = payment_method


def request(*args, payment_method=None, **kwargs):
    """Instantiate, or use a cached BitRequests object, and make a request."""
    global _requests
    global _current_method
    payment_method = payment_method or _current_method

    if payment_method not in _requests:
        from two1.wallet import Wallet
        if payment_method == OFF_CHAIN:
            from two1.server.machine_auth_wallet import MachineAuthWallet
            _requests[_current_method] = BitTransferRequests(MachineAuthWallet(Wallet()))
        elif payment_method == ON_CHAIN:
            _requests[_current_method] = OnChainRequests(Wallet())
        elif payment_method == CHANNEL:
            _requests[_current_method] = ChannelRequests(Wallet())
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
