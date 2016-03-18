.. NOT IMPLEMENTED two1.blockchain.base_provider
   ---------------------------------
   This submodule provides an abstract base class for a Provider, which
   provides information about the blockchain and broadcasts transactions
   by contacting a server. It is possible to put this "server" on the
   same local machine if desired or to keep it remote to save space.
   
   .. automodule:: two1.blockchain.base_provider
       :members:
       :undoc-members:
           :special-members: __init__
       :show-inheritance:

two1.blockchain.twentyone_provider
--------------------------------------
This submodule provides a concrete ``TwentyOneProvider`` class
that provides information about a blockchain by contacting
a server.

.. automodule:: two1.blockchain.twentyone_provider
    :members:
    :undoc-members:
	:special-members: __init__
    :show-inheritance:
