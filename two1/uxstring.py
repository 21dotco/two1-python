

class UxString:

	# account creation
	creating_account = "Creating 21.co account. Username %s."
	payout_address   = "Payout address: %s."
	account_failed   = "Failed to create 21.co account."
	username_exists  = "Username %s already exists."
	enter_username   = "Enter Username for the account:"

	# wallet
	create_wallet = "You do not have a Bitcoin wallet configured. Let's create one. Press any key ...\n"
	create_wallet_done = "\nWallet successfully created. Press any key ..."
	payout_address = "Setting mining payout address: %s."

	class Error:
		# network errors
		connection = "Error: Cannot connect to %s."
		timeout    = "Error: Connection to %s timed out."
		# 500 unknown error
		server_err = "Error: You have experienced a Technical Error. We are working to correct this issue."

		# file io errors
		file_load = "Error: Failed to load file %s."

		# wallet errors
		electrum_missing = "Error: Could not find ElectrumWallet application."
		electrum_daemon = "Error: Could not start electrum daemon."


