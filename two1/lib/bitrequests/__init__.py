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
