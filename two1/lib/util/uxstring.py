"""
Strings for the two1 CLI user interface
"""
import click


class UxString:

    # general
    update_required = "You are using an old version of 21. Please update using the '21 " \
                      "update' command."
    bitcoin_computer_needed = "You need a 21 Bitcoin Computer (21.co/buy) to access " \
                              "this service. If you believe you have received this " \
                              "message in error, please contact support@21.co."
    max_accounts_reached = click.style(
        "You have reached the maximum number of 21.co accounts that you can create on "
        "this Bitcoin Computer. Use ",
        fg="red") + click.style(
        "21 login", fg="red", bold=True) + click.style(
        " to switch between your available accounts.",
        fg="red")
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

    # account recovery
    registered_usernames_title = "\nRegistered usernames: \n"
    login_prompt = "\nPlease select the number associated with the username you want to " \
                   "log in with"
    login_prompt_invalid_user = "Please select a number between {} and {} to select the " \
                                "corresponding username"
    login_prompt_user_does_not_exist = "User {} does not exist or is not authorized for this wallet/device.\n"

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
    Your spendable balance in Payment Channels                : {channels_balance} Satoshis
    Amount flushing from 21.co balance to Blockchain balance  : {flushing} Satoshis

    [1]: Available for off-chain transactions
    [2]: Available for on-chain and payment channel transactions
    (See 21.co/micropayments for more details)
    """

    status_wallet_detail_off = """\
    To see all wallet addresses/payment channels, use '21 status --detail'\n"""

    status_wallet_detail_on = """\
    Addresses:\n{addresses}
    Channels:\n{channels}"""

    status_wallet_address = "\t{}: {} (confirmed), {} (total)\n"
    status_wallet_channel = "\t{}://{}/ {}, {} Satoshis, {}\n"
    status_wallet_channels_none = "\tNo payment channels have been created yet.\n"

    status_buyable = click.style("How many API calls can you buy?", fg='magenta') + """
    Search Queries        : {buyable_searches:<4} ({search_unit_price} Satoshis per search)
    SMS Messages          : {buyable_sms:<4} ({sms_unit_price} Satoshis per SMS)
    """

    # buy
    buy_channel_warning = "Note: The default payment channel size is " + \
        "{} Satoshis. \nIn order to open this channel you’ll need to " + \
        "spend a small amount extra to cover transaction fees and costs.\n" + \
        "In addition, your *first* purchase will spend {} of your " + \
        "outstanding balance in the channel for merchant insurance.\n" + \
        "Read more at (https://21.co/micropayments/)\n" + \
        "Proceed?"
    buy_channel_aborted = "Payment aborted."

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

    mining_limit_reached = "\nFurther mining advances are not possible at this time. " \
                           "Please try again in a few hours"

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
    buy_ad = "Get a 21 Bitcoin Computer at https://21.co/buy"

    # inbox
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

    notification_intro = click.style("Account Notifications.\n\n", bold=True,
                                     fg="magenta")

    log_intro = click.style("21 Bitcoin Computer Activity Log.\n\n", bold=True, fg="magenta")

    debit_message = "{} : {:+d} Satoshis to your 21.co balance"
    blockchain_credit_message = "{} : {:+d} Satoshis from your 21.co balance, " \
                                "{:+d} Satoshis to " \
                                "your " \
                                "Blockchain balance"
    credit_message = "{} : {:+d} Satoshis from your 21.co balance"

    buy_message = "You bought {} from {}"
    sell_message = "You sold {} to {}"

    unread_notifications = click.style("\nYou have {} unread important notifications.Type ",
                                       fg="blue") + click.style("21 inbox",
                                                                bold=True, fg="blue") + click.style(
            " to view your notifications.", fg="blue")

    # join
    successful_join = "Joined network {}. It might take a couple of seconds for joining " \
                      "to take effect."
    invalid_network = "Invalid network specified, please verify the network name"
    join_cmd = click.style("21 join", bold=True)

    # publish
    coming_soon = click.style("Coming soon", bold=True)
    slack_21_co = click.style("slack.21.co", bold=True)
    support_21_co = click.style("support@21.co", bold=True)
    publish_docs_url = click.style("https://21.co/learn/21-publish/", bold=True)

    manifest_missing = "Could not find the manifest file at {}.\nFor instructions on " \
                       "how to create one, please refer to {}"

    bad_manifest = "The following error occurred while reading your manifest file at {}:\n{}\nFor " \
                   "instructions on publishing your app, please refer to {}"

    large_manifest = "Size of the manifest file at {} exceeds the maximum limit of " \
                     "2MB.\nFor instructions on publishing your app, please refer to {}"

    reading_manifest = "Reading app manifest from {}"

    no_zt_network = click.style("You are not part of the {}. Use {}",
                                fg="red") + click.style(" to join the market.", fg="red")

    wrong_ip = click.style(
        "It seems that the IP address "
        "that you put in your manifest file (") + click.style(
        "{}", bold=True) + click.style(
        ") is different than your current 21 marketplace IP (") + click.style(
        "{}", bold=True) + click.style(
        ")\nAre you sure you want to continue publishing with ") + click.style(
        "{}", bold=True) + click.style(" ?")

    switch_host = click.style(
        "Please edit ") + click.style("{}", bold=True) + click.style(
        " and replace ") + click.style("{}", bold=True) + click.style(
        " with ") + click.style("{}", bold=True)

    publish_start = click.style("Publishing {} at ") + click.style(
        "{}", bold=True) + click.style(" to {}")

    publish_success = click.style(
        "{} successfully published to {}. It may take a couple of minutes for your app "
        "to show up in the marketplace.", fg="magenta")

    valid_app_categories = {'blockchain', 'entertainment', 'social', 'markets', 'utilities'}

    valid_top_level_manifest_fields = ["schemes", "host", "basePath", "x-21-manifest-path",
                                       "x-21-healthcheck-path", "info"]
    top_level_manifest_field_missing = "Field '{}' is missing from the manifest file."
    manifest_info_fields = ["contact", "x-21-total-price", "description", "x-21-usage",
                            "x-21-quick-buy", "version", "x-21-category", "x-21-keywords"]
    manifest_info_field_missing = "Field '{}' is missing from the manifest file under the 'info' " \
                                  "section."

    price_fields = ["min", "max"]
    price_fields_missing = "Field '{}' is missing from the manifest file under the " \
                           "'x-21-total-price' section."
    scheme_missing = "You have to specify either HTTP or HTTPS for your endpoint under the " \
                     "`schemes` section."
    invalid_category = "'{}' is not a valid category for the 21 marketplace. Valid categories are " \
                       "{}."

    # publish-list
    my_apps = "Listing all the published apps by {}: "
    no_published_apps = click.style(
        "You haven't published any apps to the marketplace yet. Use ",
        fg="blue") + click.style(
            "21 publish -a {YOUR_APP_DIRECTORY}", bold=True, fg="blue") + click.style(
            " to publish your apps to the marketplace.", fg="blue")

    app_does_not_exist = "The specified id for the app ({}) does not match any app."

    # publish delete
    delete_confirmation = "Are you sure that you want to delete the app with id '{}' ?"
    delete_success = "App {} ({}) was successfully removed from the marketplace."

    # sell
    app_directory_valid = click.style("App Directory Valid...", fg="magenta")
    app_directory_invalid = click.style("App Directory Invalid. Please ensure \
your directory and it's contents are correct,\
refer to 21.co/app for futher instructions.", fg="red")
    installing_requirements = click.style(
        "Installing requirements...", fg="magenta")
    installed_requirements = click.style(
        "Successfully installed requirements...", fg="magenta")
    created_nginx_server = click.style(
        "Created default 21 nginx server...", fg="magenta")
    created_site_includes = click.style(
        "Created site-includes to host apps...",
        fg="magenta")
    created_systemd_file = click.style("Systemd file created...", fg="magenta")
    created_app_nginx_file = click.style("Nginx file created...", fg="magenta")
    hosted_app_location = click.style(
        "Your app is now hosted at http://0.0.0.0/{}",
        fg="magenta")
    listing_enabled_apps = click.style("Listing enabled apps...", fg="magenta")
    no_apps_currently_running = click.style(
            "No apps currently running, refer to 21.co/sell to host some...",
            fg="red")
    successfully_stopped_app = click.style(
        "Successfully stopped {}...",
        fg="magenta")
    app_not_enabled = click.style(
        "This app is not within your enabled apps.", fg="red")
    failed_to_destroy_app = click.style(
        "Failed to destroy app, please contact support@21.co", fg="red")
    check_or_create_manifest_file = click.style(
        "Checking or creating manifest file...", fg="magenta")
    success_manifest = click.style(
        "Successfully found or created manifest file...", fg="magenta")
    manifest_fail = click.style(
        "Failed to create manifest file, please contact support@21.co",
        fg="red")

    # search
    list_all = "Listing all the marketplace apps: "
    pagination = click.style("\nType id of the app for more info, ",
                             fg="blue") + click.style(
        "n", bold=True, fg="blue") + click.style(
        " for next page, ", fg="blue") + click.style(
        "p", bold=True,fg="blue") + click.style(
        " for the previous page, ", fg="blue") + click.style(
        "q", bold=True, fg="blue") + click.style(
        " to stop search", fg="blue")

    empty_listing = click.style("\nWe couldn't find any listings that match '{}'.\n",
                                fg='blue')
    # rate
    bad_rating = "an app rating must be between 1 to 5"
    rating_success = click.style("Giving a ") + click.style("{}/5", bold=True) + click.style(
            " rating to the app with id ") + click.style("{}", bold=True)

    rating_app_not_found = click.style("App with id {} does not exist in 21 marketplace. Use ",
                                       fg="red") + click.style("21 search", bold=True,
                                                               fg="red") + click.style(
        " to verify the id of the app", fg="red")
    rating_list = click.style("Listing all the apps that you have rated. \nNote that you can "
                              "always change your ratings by using ") + click.style("21 rate.\n",
                                                                                    bold=True)
    no_ratings = click.style("You haven't rated any apps yet.", fg="blue")

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
        retry_update_after_reboot = "Could not stop Wallet Daemon. Please reboot your system and retry 21 update."

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
