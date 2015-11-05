import click


class UxString:
    # account creation
    creating_account = "Creating 21.co account. Username: %s."
    missing_account = "Looks like you do not have a 21.co account. Let's create one..."

    account_failed = "Failed to create 21.co account."
    username_exists = "User %s already exists."
    enter_username = "Enter username for your 21.co account"
    enter_username_retry = "Create a new username and retry."
    # wallet
    create_wallet = "You do not have a Bitcoin wallet configured. "\
        "Let's create one. Press any key ...\n"
    create_wallet_done = "\nWallet successfully created. Press any key ..."
    wallet_daemon_started = "Started wallet daemon. To stop it, type 'wallet stopdaemon'."
    payout_address = "Setting mining payout address: %s."

    flush_success = "{}\n"\
        "Your mined Satoshis will be sent to you on the "\
        "Blockchain in the next payout cycle.\n"\
        "Estimated time of payout: ~20 minutes.\n"\
        "To check progress:  https://blockexplorer.com/address/{}\n"\
        "To get more liquid bitcoin, use {} to buy more API calls."

    # status
    status_exit_message = "\nUse {} to buy API calls for bitcoin from 21.co.\nFor help, do {}."
    status_empty_wallet = "\nUse {} to get some bitcoin from 21.co."

    status_account = "{account}\n"\
        "    Username        : {username}\n"\

    status_mining = "{mining}\n"\
       "    Status           : {is_mining}\n"\
       "    Hashrate         : {hashrate}\n"\
       "    Mined (all time) : {mined} Satoshi\n\n"\
       "Type {minecmd} to see a detailed view. Hit q to exit.\n"

    status_wallet = """{balance}
    Your spendable balance at 21.co [1]                       : {twentyone_balance} Satoshi
    Your spendable balance on the Blockchain [2,3]            : {onchain} Satoshi
    Amount flushing from 21.co balance to Blockchain balance  : {flushing} Satoshi

    [1]: Available for bittransfers (21.co/bittransfers)
    [2]: Available for on-chain (21.co/on-chain) & payment
         channels (21.co/payment-channels)
    [3]: To see all wallet addresses, do 21 status --detail
    """

    status_buyable =     """{}
    Search Queries        : {:<4} ({} Satoshis per search)
    News Articles         : {:<4} ({} Satoshis per article)
    Priority Twitter DMs  : {:<4} ({} Satoshis per message)
    """

    # mining
    mining_show_dashboard_prompt = "About to show mining dashboard.\n\n" + \
        "Hit any key to launch the dashboard. " + \
        click.style("Hit q to exit the dashboard. ", bold=True)
    
    mining_show_dashboard_context = "\nDo " + click.style("21 mine --dashboard", bold=True) + \
        " to see a mining dashboard.\n" + \
        "Do " + click.style("21 log", bold=True) + " to see more aggregated stats.\n" + \
        "Or just do " + click.style("21 status", bold=True) + " to see your mining progress."
        
    mining_chip_start = "21 Bitcoin Chip detected, trying to (re)start miner..."
    mining_chip_running = "Your 21 Bitcoin Chip is already running!\n" + \
        "You should now receive a steady stream of Satoshis."
    mining_start = "\n{}, you are mining {} Satoshis from 21.co\n" \
                   "This may take a little while...\n"
    mining_dashboard_no_chip = "Without a 21 mining chip, we can't show you a mining dashboard.\n"\
        "If you want to see this dashboard, run this on a 21 Bitcoin Computer."
    mining_success = "\n{}, you mined {} Satoshis in {:.1f} seconds!"
    mining_status = "\nHere's the new status of your balance after mining:\n"
    mining_finish = "\nView your balance with {}, or spend with {}."

    # updater
    update_check = "Checking for application update..."
    update_package = "Updating to version %s..."
    update_superuser = "You might need to enter superuser password."

    # flush
    flush_status = "\n* Your flushed amount of %s Satoshis will appear " \
                   "in your wallet balance as soon as they appear on the Blockchain."

    # ad
    buy_ad = "Get a 21 Bitcoin Computer at 21.co/buy"

    # log

    reasons = {"CLI": "Performed 21 mine in a command line interface",
               "Shares": "Submitted Shares through The 21 Bitcoin Computer",
               "flush_payout": "Performed 21 flush to move unpaid earnings to the Blockchain",
               "earning_payout": "Periodic 21 payout of portion of the earnings to the Blockchain"
               }

    class Error:
        # network errors
        connection = "Error: Cannot connect to {}. Please check your Internet connection."
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
        version_not_found = "Did not find version {}."
        invalid_username = "Invalid username. Username must be alphanumeric and between 5-32 characters."
        invalid_email = "Invalid email address."
        update_server_connection = "Could not connect to the update server. Please try again later."
        account_failed = "Could not create 21 account. Please check your email address."

        # version errors
        version_not_detected = "Could not properly detect your version of 21. \nTry"\
            " reinstalling from the 21 Toolbelt instructions at 21.co/learn. \nIf problems"\
            " persist, please contact support@21.co."
        resource_price_greater_than_max_price = "{} \nPlease use --maxprice to adjust the maximum price."
