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

_requests = None


def request(*args, payment_method='offchain', **kwargs):
    global _requests

    if _requests is None:
        from two1.lib.wallet import Wallet
        if payment_method == 'offchain':
            from two1.lib.server.machine_auth_wallet import MachineAuthWallet
            _requests = BitTransferRequests(MachineAuthWallet(Wallet()))
        elif payment_method == 'onchain':
            _requests = OnChainRequests(Wallet())
        elif payment_method == 'channel':
            _requests = ChannelRequests(Wallet())
        else:
            raise ValueError('That method is not supported.')

    return _requests.request(*args, **kwargs)


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
