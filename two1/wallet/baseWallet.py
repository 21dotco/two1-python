satoshi_to_btc = 1e8

class BaseWallet(object):
	""" An abstract wallet class. """
	def __init__(self):
		super(BaseWallet, self).__init__()

	@property
	def addresses(self):
		""" Gets the address list for the current wallet.
		Returns:
			(list): The current list of addresses in this wallet.
		"""
		raise NotImplementedError('Abstract class, `addresses` must be overridden')

	@property
	def current_address(self):
		""" Gets the preferred address.
		Returns:
			(str): The current preferred payment address. 
		"""
		raise NotImplementedError('Abstract class, `current_address` must be overridden')

	@property
	def confirmed_balance(self):
		""" Gets the current confirmed balance of the wallet.
		Returns:
			(number): The current confirmed balance.
		"""
		raise NotImplementedError('Abstract class `confirmed_balance` must be overridden')
	@property
	def unconfirmed_balance(self):
		""" Gets the current unconfirmed balance of the wallet.
		Returns:
			(number): The current unconfirmed balance.
		"""
		raise NotImplementedError('Abstract class, `unconfirmed_balance` must be overridden')

	def sign_transaction(self, tx):
		""" Signs the inputted transaction.
		Returns:
			(tx): The signed transaction object.
		"""
		raise NotImplementedError('Abstract class, `sign_transaction` must be overridden')

	def broadcast_transaction(self, tx):
		""" Broadcasts the transaction to the Bitcoin network.
		Args:
			tx (tx): The transaction to be broadcasted to the Bitcoin network..
		Returns:
			(str): The name of the transaction that was broadcasted.
		"""
		raise NotImplementedError('Abstract class, `broadcast_transaction` must be overridden')

	def make_signed_transaction_for(self, address, amount):
		""" Makes a raw signed unbrodcasted transaction for the specified amount.
		Args:
			address (str): The address to send the Bitcoin to.
			amount (number): The amount of Bitcoin to send.
		Returns:
			(dictionary): A dictionary containing the transaction name and the raw transaction object.
		"""
		raise NotImplementedError('Abstract class, `make_signed_transaction_for` must be overridden')
		
	def send_to(self, address, amount):
		""" Sends Bitcoin to the provided address for the specified amount.
		Args:
			address (str): The address to send the Bitcoin too.
			amount (number): The amount of Bitcoin to send.
		Returns:
			(dictionary): A dictionary containing the transaction name and the raw transaction object.
		"""
		raise NotImplementedError('Abstract class, `send_to` must be overridden')
