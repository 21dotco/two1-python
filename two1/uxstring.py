

class UxString:

	#account creation
	creating_account = "Creating 21.co account. Username %s."
	payout_address   = "Payout address: %s."
	account_failed   = "Failed to create 21.co account."
	username_exists  = "Username %s already exists."
	enter_username   = "Enter Username for the account:"

	class Error:
		#network errors
		connection = "Error: Cannot connect to %s."
		timeout    = "Error: Connection to %s timed out."

		#file io errors
		file_load = "Error: Failed to load file %s."

		#wallet errors
		electrum_missing = "Error: Could not find ElectrumWallet application."


