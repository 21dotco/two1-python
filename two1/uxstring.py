class UxString:
    # account creation
    creating_account = "Creating 21.co account. Username %s."
    payout_address = "Payout address: %s."
    account_failed = "Failed to create 21.co account."
    username_exists = "Username %s already exists."
    enter_username = "Enter Username for the account"
    enter_username_retry = "Create a new username and retry."

    class Error:
        # network errors
        connection = "Error: Cannot connect to %s."
        timeout = "Error: Connection to %s timed out."
        # 500 unknown error
        server_err = "Error: You have experienced a Technical Error. "\
            "We are working to correct this issue."
        non_existing_user = "Error: Username %s does not exist"

        # wallet errors
        electrum_missing = "Error: Could not find ElectrumWallet application."
        electrum_daemon = "Error: Could not start electrum daemon."
