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
    flush_success = "\nYour mined Satoshis will be sent to you on the Blockchain in" \
                    " our next payout cycle.\nEstimated time of payout: 20 minutes"

    # status
    status_exit_message = "\nYou can use your spendable balance to buy {} searches, {} full text" \
                          "\narticles, or send up to {} paid direct messages with {}." \
                          "\nDo {} for more info."
    status_empty_wallet = "\nUse {} to get some Bitcoin from 21.co."

    # mining
    mining_start = "\n{}, you are mining {} Satoshis from 21.co\n" \
                   "This may take a little while...\n"
    mining_success = "\n{}, you mined {} Satoshis in {:.1f} seconds!"
    mining_finish = "\nView your balance with {}, or spend with {}."

    # updater
    update_check = "Checking for application update..."
    update_package = "Updating to version %s..."
    update_superuser = "You might need to enter superuser password."

    # flush
    flush_status = "\n* Your flushed amount of %s Satoshis will appear " \
                   "in your wallet balance as soon as they appear on the Blockchain."

    # ad
    buy_ad = "\nGet a 21 Bitcoin Computer at 21.co/buy"

    # log

    reasons = {"CLI": "Performed 21 mine in a command line interface",
               "Shares": "Submitted Shares through The 21 Bitcoin Computer",
               "flush_payout": "Performed 21 flush to move unpaid earnings to the Blockchain",
               "earning_payout": "Periodic 21 payout of portion of the earnings to the Blockchain"
               }
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
