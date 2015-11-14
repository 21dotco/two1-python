import click


class UxString:
    # account creation
    creating_account = "Creating 21.co account. Username: %s."
    missing_account = "Looks like you do not have a 21.co account. Let's create one..."

    account_failed = "Failed to create 21.co account."
    username_exists = "User %s already exists."
    enter_username = "Enter a username for your 21.co account"
    enter_email = "Enter your email address"
    enter_username_retry = "Create a new username and retry."
    # wallet
    create_wallet = "You do not have a Bitcoin wallet configured. "\
        "Let's create one. Press any key ...\n"
    create_wallet_done = "Wallet successfully created.\n\n"\
                         "You can recover the private key to your wallet using the following 12 words (in this order) :\n"\
                         "\n%s\n\n"\
                         "Write down and store these words in a safe place.\n\n"\
                         "Press any key ..."

    wallet_daemon_started = "Started wallet daemon. To stop it, type 'wallet stopdaemon'."
    payout_address = "Setting mining payout address: %s."
    analytics_optin = "\nWould you like 21.co to collect usage analytics?\n"\
        "This may help us debug any issues and improve software quality."
    analytics_thankyou = "Thank you!\n"

    flush_success = "{}\n"\
        "Your mined Satoshis will be sent to you on the "\
        "Blockchain in the next payout cycle.\n"\
        "Estimated time of payout: ~20 minutes.\n"\
        "To check progress:  https://blockexplorer.com/address/{}\n"\
        "To get more bitcoin, use {}."

    # status
    status_exit_message = "\nUse {} to buy API calls for bitcoin from 21.co.\nFor help, do {}."
    status_empty_wallet = "\nUse {} to get some bitcoin from 21.co."

    status_account = click.style("21.co Account", fg='magenta') + "\n"\
        "    Username        : {username}\n"\

    status_mining = mining=click.style("Mining", fg='magenta') + "\n"\
       "    Status           : {is_mining}\n"\
       "    Hashrate         : {hashrate}\n"\
       "    Mined (all time) : {mined} Satoshis\n\n"\
       "Type " + click.style("21 mine --dashboard", bold=True) + " to see a detailed view. Hit q to exit.\n"

    status_wallet = click.style("Balance", fg='magenta') + """
    Your spendable balance at 21.co [1]                       : {twentyone_balance} Satoshis
    Your spendable balance on the Blockchain [2]              : {onchain} Satoshis
    Amount flushing from 21.co balance to Blockchain balance  : {flushing} Satoshis

    [1]: Available for off-chain (21.co/micropayments)
    [2]: Available for on-chain (21.co/micropayments)

    {byaddress}
    """

    status_buyable = click.style("How many API calls can you buy?", fg='magenta') + """
    Search Queries        : {buyable_searches:<4} ({search_unit_price} Satoshis per search)
    SMS Messages          : {buyable_sms:<4} ({sms_unit_price} Satoshis per SMS)
    """

    # doctor
    doctor_start = click.style("21.co Doctor", fg='green') + "\n\n" + \
        click.style("Checking health..", fg='magenta') + "\n"
    doctor_general = click.style("Checking general settings..", fg='yellow')
    doctor_dependencies = click.style("Checking dependencies..", fg='yellow')
    doctor_demo_endpoints = click.style("Checking demo endpoints..", fg='yellow')
    doctor_servers = click.style("Checking servers..", fg='yellow')
    doctor_error = click.style("    Error: ", fg='red')
    doctor_total = click.style("Summary", fg='yellow')

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

    mining_advance_not_possible = "\nFurther advances against your Bitcoin Computer " \
                                  "work are not possible at this time. Please try again " \
                                  "in a few of hours."
    mining_limit_reached = "\nYou have reached the daily limit for getting advances " \
                           "against your Bitcoin Computer work. Please try again in a " \
                           "few of hours"

    # updater
    update_check = "Checking for application updates..."
    update_package = "Updating to version %s..."
    update_superuser = "You might need to enter superuser password."
    update_not_needed = "Already up to date!"

    # flush
    flush_status = "\n* Your flushed amount of %s Satoshis will appear " \
                   "in your wallet balance as soon as they appear on the Blockchain."

    flush_insufficient_earnings = "You must have a minimum of 20000 Satoshis to " \
                                  "be able to flush your earnings to the Blockchain"
    # ad
    buy_ad = "Get a 21 Bitcoin Computer at 21.co/buy"

    # log
    reasons = {
        "CLI": "You got an advance against your future work on the Bitcoin Computer",
        "Shares": "You submitted work through the 21 Bitcoin Computer",
        "flush_payout": "You performed 21 flush to move your earnings to the "
                        "Blockchain",
        "earning_payout": "This is a periodic payout of your mining earnings to "
                          "the Blockchain.",
        "BC": "Your bitcoin bonus for booting the 21 Bitcoin Computer."
    }

    empty_logs = "[No events yet]"

    log_intro = "21 Bitcoin Computer Activity Log.\n\n"

    debit_message = "{} : {:+d} Satoshis to your 21.co balance"
    blockchain_credit_message = "{} : {:+d} Satoshis from your 21.co balance, " \
                                "{:+d} Satoshis to " \
                                "your " \
                                "Blockchain balance"
    credit_message = "{} : {:+d} Satoshis from your 21.co balance"

    buy_message = "You bought {} from {}"
    sell_message = "You sold {} to {}"

    # publish
    coming_soon = click.style("Coming soon", bold=True)
    slack_21_co = click.style("slack.21.co", bold=True)
    support_21_co = click.style("support@21.co", bold=True)
    publish_stub = """%s
- Publish functionality will be available in a forthcoming 21 update
- In the meantime, please visit the 21 Developer Community at %s
- There, you can find other 21 developers to buy your machine-payable endpoints
For further information, please contact %s""" % \
  (coming_soon, slack_21_co, support_21_co)

    # sell
    sell_stub = """%s
- Full sell functionality will be available in a forthcoming 21 update
- To get started, please see 21.co/learn/sell-or-license-any-file-for-bitcoin
- Then visit the 21 Developer Community at %s
- There, you can find other 21 developers to buy your machine-payable endpoints
For further information, please contact %s""" % \
  (coming_soon, slack_21_co, support_21_co)

    # search
    search_stub = """%s
- Full search functionality will be available in a forthcoming 21 update
- In the meantime, please visit the 21 Developer Community at %s
- There, you can find machine-payable endpoints to buy from other 21 developers
For further information, please contact %s""" % \
  (coming_soon, slack_21_co, support_21_co)

    # rate
    rate_stub = """%s
- Rating functionality will be available in a forthcoming 21 update
- In the meantime, please visit the 21 Developer Community at %s
- There, you can find machine-payable endpoints to buy from other 21 developers
For further information, please contact %s""" % \
  (coming_soon, slack_21_co, support_21_co)

    class Error:
        # network errors
        connection = "Error: Cannot connect to {}. Please check your Internet connection."
        connection_cli = "An internet connection is required to run this command."
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
        account_failed = "Could not create a 21 account. Please check the username."

        # version errors
        version_not_detected = "Could not properly detect your version of 21. \nTry"\
            " reinstalling from the 21 Toolbelt instructions at 21.co/learn. \nIf problems"\
            " persist, please contact support@21.co."
        resource_price_greater_than_max_price = "{} \nPlease use --maxprice to adjust the maximum price."
        insufficient_funds_mine_more = "Insufficient satoshis for off-chain (zero-fee) transaction. "\
            "Type {} to get more.*\n\n"\
            "You may also use your on-chain balance for this transaction. It will include a {} satoshi tx fee."\
            "To use on-chain balance add {} to your buy command*".format(
                    click.style("21 mine", bold=True), {}, click.style("-p onchain", bold=True)
                )
