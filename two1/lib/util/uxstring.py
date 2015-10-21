class UxString:
    # account creation
    creating_account = "Creating 21.co account. Username: %s."
    missing_account = "Looks like you do not have a 21.co account. Let's create one..."

    account_failed = "Failed to create 21.co account."
    username_exists = "User %s already exists."
    enter_username = "Choose username for your account"
    enter_username_retry = "Create a new username and retry."
    # wallet
    create_wallet = "You do not have a Bitcoin wallet configured. "\
        "Let's create one. Press any key ...\n"
    create_wallet_done = "\nWallet successfully created. Press any key ..."
    wallet_daemon_started = "Started wallet daemon. To stop it, type 'wallet stopdaemon'."
    payout_address = "Setting mining payout address: %s."
    flush_success = "\nYour mined Bitcoin will be sent to you on the Blockchain in" \
                    " our next payout cycle.\nEstimated time of payout: 20 minutes"

    # status
    status_exit_message = "\nYou can use your spendable balance to buy {} searches, " \
                          "{} full text articles, or send up to {} " \
                          "paid direct messages with {}.\nTry {} for more."
    status_empty_wallet = "\nUse {} to get some Bitcoin from 21.co."

    # mining
    mining_start = "\n{}, you are mining {} Satoshis from 21.co\n" \
                   "This may tak a little while...\n"
    mining_success = "\n{}, you mined {} Satoshis in {:.1f} seconds!"
    mining_finish = "\nView your balance with {}, or spend with {}.\n"

    # updater
    update_check = "Checking for application update..."
    update_package = "Updating to version %s..."
    update_superuser = "You might need to enter superuser password."

    # flush
    flush_status = "You have requested that %s of your earned Satoshis be paid to " \
                   "your wallet.\nYou will be paid in our next " \
                   "payout cycle.\nEstimated time: 10 minutes"

    # ad
    buy_ad = "\nGet a 21 Bitcoin Computer at 21.co/buy"
    
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
        create_wallet_failed = "Error: Could not create wallet."

        # data unavailable
        data_unavailable = "[ Unavailable ]"

        # file errors
        file_load = "file %s does not exist"
        # Updater
        update_failed = "Error occured during update process. Please try to run a manual update."
        version_not_found = "Did not find version '%s'. Defaulting to latest."
