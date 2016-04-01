"""
Strings for the two1 CLI user interface
"""
import click


class UxString:
    """ Class to namespace all user experience strings """

    # general
    update_required = click.style("You are using an old version of 21 CLI. Please update using the '21 " \
                                  "update' command.",
                                  fg="red")
    bitcoin_computer_needed = click.style("You need a 21 Bitcoin Computer (21.co/buy) to access " \
                                          "this service. If you believe you have received this " \
                                          "message in error, please contact support@21.co.",
                                          fg="red")
    max_accounts_reached = click.style("You have reached the maximum number of 21.co accounts that you can create. ", fg="red") +\
                           click.style("Use ", fg="red") +\
                           click.style("21 login ", fg="red", bold=True) +\
                           click.style("to switch between your available accounts.", fg="red")

    # account creation
    creating_account = "Creating 21.co account. Username: {}"
    missing_account = "Looks like you do not have a 21.co account. Let's create one..."

    account_failed = "Failed to create 21.co account."
    username_exists = "User {} already exists."
    email_exists = "Email {} already exists."
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
    payout_address = "Setting mining payout address: {}"
    analytics_optin = "\nWould you like to help 21.co collect usage analytics?\n"\
        "This may help us debug any issues and improve software quality."
    analytics_thankyou = "Thank you!\n"
    unconfirmed_email = "Before logging in, you must activate your 21 account using the email sent to you at ali@21.co. If you can't find the email, please visit 21.co/activation."

    flush_success = "{}\n"\
        "Your mined Satoshis will be sent to you on the "\
        "Blockchain in the next payout cycle.\n"\
        "Estimated time of payout: ~20 minutes.\n"\
        "To check progress:  https://blockexplorer.com/address/{}\n"\
        "To get more bitcoin, use {}."

    # username
    login_username = "\nUsername (Case sensitive)"
    login_password = "Password (Typing will be hidden)"
    login_in_progress = "logging in {}."
    login_required = "Account login is required.\n\n\tRun {} first.".format(click.style("21 login", bold=True))
    incorrect_password = click.style("The username and password that you entered do not match.",
                                     fg="red")

    # sign up
    signin_title = click.style(
        "\nIf you don't have a 21 account, visit https://21.co/signup to create one. ", fg="blue")

    # account recovery
    registered_usernames_title = "\nRegistered usernames: \n"
    login_prompt = "\nPlease select the number associated with the username you want to " \
                   "log in with"
    login_prompt_invalid_user = "Please select a number between {} and {} to select the " \
                                "corresponding username"
    login_prompt_user_does_not_exist = "User {} does not exist or is not authorized for this wallet.\n"

    existing_account = click.style("There is already a username associated with your current wallet. Use ", fg="red") +\
                       click.style("21 login -u {}", bold=True, fg="red") +\
                       click.style(" to login.", fg="red")

    set_new_password = "Please set a password for" +\
                       click.style(" {}.", bold=True) +\
                       click.style(" (typing will be hidden)")

    no_account_found = "You have not created any accounts yet. Use " +\
                       click.style("21 login", bold=True) +\
                       " to create an account first."

    short_password = "Password must be at least 5 characters long."
    capitalize_password = "Password must contain mix of uppercase or lowercase letters."
    numbers_in_password = "Password must contain at least a digit."

    # status
    status_exit_message = "\nUse {} to buy API calls for bitcoin from 21.co.\nFor help, do {}."
    status_empty_wallet = "\nUse {} to get some bitcoin from 21.co."

    status_account = click.style("Logged in as: ", fg='magenta') + "{}\n"

    status_mining = mining = click.style("Mining", fg='magenta') + "\n" +\
                             "    Status           : {}\n" +\
                             "    Hashrate         : {}\n" +\
                             "    Mined (all time) : {} Satoshis\n\n" +\
                             "Type " +\
                             click.style("21 mine --dashboard", bold=True) +\
                             " to see a detailed view. Hit q to exit.\n"

    status_wallet = click.style("Total Balance", fg='magenta') + """
    Your spendable balance at 21.co [1]                       : {twentyone_balance} Satoshis
    Your spendable balance on the Blockchain [2]              : {onchain} Satoshis
    Your spendable balance in Payment Channels                : {channels_balance} Satoshis
    Amount flushing from 21.co balance to Blockchain balance  : {flushing} Satoshis

    [1]: Available for off-chain transactions
    [2]: Available for on-chain and payment channel transactions
    (See 21.co/micropayments for more details)
    """

    status_mining_file_not_found = "Run {} to start mining".format(click.style("21 mine", bold=True))
    status_mining_timeout = "TimeoutError occured while getting hashrate"
    status_mining_success = "21 mining chip running (/run/minerd.pid)"
    status_mining_hashrate = "{:.1f} GH/s"
    status_mining_hashrate_unknown = "~50 GH/s (warming up)"

    status_balance_by_username_header = "Off-chain Balances by Username \n"
    status_balance_by_username_table_headers = ["Username", "Balance"]
    status_wallet_detail_off = """\
    To see all wallet addresses and open payment channels, use '21 status --detail'\n"""

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
        "spend a small amount extra to cover transaction fees.\n" + \
        "Read more at (https://21.co/micropayments/)\n" + \
        "Proceed?"
    buy_bad_payment_method = "'{}' is not a supported payment method."
    buy_bad_uri_scheme = "Please provide a valid scheme for the request, such as `http://` and `https://`."
    buy_bad_uri_host = "Please provide a valid hostname for the request, such as `market.21.co`."
    buy_channel_aborted = "Payment aborted."
    buy_bad_data_format = "Unknown data format."
    buy_balances = "\nYou spent: {} Satoshis. Remaining {} balance: {} Satoshis."

    # doctor
    doctor_start = click.style("21.co Doctor", fg='green') + "\n\n" + \
        click.style("Checking health..", fg='magenta') + "\n"
    doctor_general = click.style("Checking general settings..", fg='yellow')
    doctor_dependencies = click.style("Checking dependencies..", fg='yellow')
    doctor_demo_endpoints = click.style("Checking demo endpoints..", fg='yellow')
    doctor_servers = click.style("Checking servers..", fg='yellow')
    doctor_error = click.style("    Error: ", fg='red')
    doctor_total = click.style("Summary", fg='yellow')

    # buybitcoin
    deposit_type_question = "\nWhere do you want your Bitcoins to be deposited to ?"
    deposit_type_on_chain = "Your balance on the Blockchain [2]"
    deposit_type_off_chain = "Your balance at 21.co [1]"
    deposit_type_explanation = "\n[1] Available for off-chain transactions. " \
                               "\n[2] Available for on-chain and payment channel transactions." \
                               "\nYou can always move your balance at 21.co to the Blockchain by " \
                               "issuing the" + click.style(" 21 flush ", bold=True) + "command"

    deposit_type_invalid_index = "Please select a number between {} and {} to select the " \
                                 "corresponding deposit type"

    deposit_type_prompt = "\nPlease select the number associated with the deposit option you " \
                          "would like to use"

    exchange_info_header = click.style("\nExchange Info", fg="magenta")
    exchange_info = "    Exchange Name          : {}\n" \
                    "    Exchange Username      : {}\n" \
                    "    Linked Exchange Wallet : {}\n" \
                    "    Linked Payment Method  : {}\n"
    buybitcoin_instruction_header = click.style("Buying Bitcoin:", fg="magenta")
    buybitcoin_instructions = "    Use " + click.style("21 buybitcoin", bold=True) +\
                              " to buy k Satoshis from {}.\n" +\
                              "    The bought Bitcoins will automatically appear into your 21 wallet\n\n"
    buybitcoin_pairing = \
        "To buy bitcoin, you need to pair your 21 and {} account.\n\n" + \
        "If you already haven't, create a password for your account by " \
        "doing " + click.style("21 login -setpassword",
                               bold=True) + "\nThen go to http://21.co/{}/buybitcoin in your " \
                                            "browser to complete the pairing\n"
    buybitcoin_no_payment_method = \
        "To add a payment method to {}, go to {}."
    buybitcoin_confirmation = "\nYou are about to withdraw {} from the bank connected to your " \
                              "Coinbase account to buy {}.\n" \
                              "From {}, {} will be spent on fees. \n" \
                              "Your Bitcoins will be deposited to your {}.\n"
    buybitcoin_confirmation_prompt = "Are you sure you want to continue with this purchase ?"
    buybitcoin_error = click.style("Error:", bold=True, fg="red") + " {}"
    buybitcoin_success = click.style("\nYou have successfully bought ", fg="magenta") +\
                         click.style("{} ", fg="magenta", bold=True) +\
                         click.style("for", fg="magenta") +\
                         click.style(" {}.\n", bold=True, fg="magenta")

    buybitcoin_success_payout_time = "The Bitcoins will be deposited to your 21 wallet on {}."
    buybitcoin_success_instant = "The Bitcoins will be deposited to your 21 wallet in the next " \
                                 "couple of minutes."

    buybitcoin_21_balance_success = "The Bitcoins will be deposited to your 21.co balance in the " \
                                    "next couple of minutes."
    buybitcoin_21_balance_time = "\nOn {}, {} {} will be withdrawn from your Coinbase wallet " \
                                 "for this purchase."

    coinbase_purchase_in_progress = "\nPurchasing Bitcoins From Coinbase...\n"

    coinbase_deposit_type_mapping = {"WALLET": "your Blockchain balance",
                                     "TO_BALANCE": "your 21.co balance"}
    coinbase_wallet_completed = "The Bitcoins were deposited to your wallet on {}"
    coinbase_21_completed = "The Bitcoins were added to your balance immediately. " \
                            "Around {}, {} BTC amount were withdrawn from your " \
                            "Coinbase wallet for this purchase."

    coinbase_wallet_pending = "The Bitcoins will be deposited to your wallet around {}"
    coinbase_21_pending = "The Bitcoins were added to your balance immediately. " \
                          "Around {}, {} BTC will be withdrawn from your Coinbase wallet for this " \
                          "purchase."

    coinbase_history_title = "Your Bitcoin Purchase History. \n"
    coinbase_no_bitcoins_purchased = "[No purchases yet]"
    coinbase_history = click.style(
        "{} : {} Satoshis from your Coinbase wallet to {}\n", fg="cyan") + "Description: {}"

    # mining
    mining_show_dashboard_prompt = "About to show mining dashboard.\n\n" + \
        "Hit any key to launch the dashboard. "
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
        "If you want to see this dashboard, run this command on a 21 Bitcoin Computer."
    mining_success = "\n{}, you mined {} Satoshis in {:.1f} seconds!"
    mining_status = "\nHere's the new status of your balance after mining:\n"
    mining_finish = "\nView your balance with {}, or spend with {}."

    mining_limit_reached = "\nFurther mining advances are not possible at this time. " \
                           "Please try again in a few hours"

    mining_bitcoin_computer_needed = click.style("You need a 21 Bitcoin Computer (21.co/buy) to access this service. \nYou can use ", fg="red") +\
                                     click.style("21 buybitcoin", bold=True, fg="red") +\
                                     click.style(" to add Bitcoins to your account instead. \nIf you believe you have received this ", fg="red") +\
                                     click.style("message in error, please contact support@21.co.", fg="red")

    # updater
    update_check = "Checking for application updates..."
    update_package = "Updating to version {}..."
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
        "CLI": "You just received a little bit of bitcoin.",
        "Shares": "You submitted work through the 21 Bitcoin Computer.",
        "flush_payout": "You performed 21 flush to move your earnings to the "
                        "Blockchain.",
        "earning_payout": "This is a periodic payout of your mining earnings to "
                          "the Blockchain.",
        "BC": "Your bitcoin bonus for booting the 21 Bitcoin Computer.",
        "coinbase_purchase": "You bought and transferred Bitcoins to your account through "
                             "Coinbase."
    }

    empty_logs = "[No events yet]"

    notification_intro = click.style("[Account Notifications]\n\n", bold=True,
                                     fg="magenta")

    log_intro = click.style("[21 Activity Log]\n\n", bold=True, fg="magenta")

    debit_message = "{} : {:+d} Satoshis to your 21.co balance"
    blockchain_credit_message = "{} : {:+d} Satoshis from your 21.co balance, " \
                                "{:+d} Satoshis to " \
                                "your " \
                                "Blockchain balance"
    credit_message = "{} : {:+d} Satoshis from your 21.co balance"

    buy_message = "You bought {} from {}"
    sell_message = "You sold {} to {}"

    unread_notifications = click.style("\nYou have {} unread notifications. Type ", fg="blue") +\
                           click.style("21 inbox", bold=True, fg="blue") +\
                           click.style(" to view your notifications.", fg="blue")

    # join
    successful_join = "Joined network {}. It may take a few seconds for joining " \
                      "to take effect."
    invalid_network = "Invalid network specified, please verify the network name."
    join_cmd = click.style("21 join", bold=True, reset=False)

    no_network = click.style("You are not part of any network.", fg="blue")
    install_zerotier = click.style("To join network you must have zerotier-one installed.\n" \
                                   "See installation instructions at:\n" \
                                   "\n\thttps://www.zerotier.com/product-one.shtml\n")

    # publish
    publish_docs_url = click.style("https://21.co/learn/21-publish/", bold=True)
    publish_instructions = "For instructions on publishing your app, please refer to {}".format(publish_docs_url)

    manifest_missing = click.style("Could not find the manifest file at {}.", fg="red")

    bad_manifest = "{}{}".format("The following error occurred while reading your manifest file at {}:\n{}\n\n",
                                 publish_instructions)

    malformed_yaml = click.style("Your manifest file at {} is not valid YAML.", fg="red")
    large_manifest = click.style("Size of the manifest file at {} exceeds the maximum limit of 2MB.", fg="red")

    manifest_is_directory = click.style("{} is a directory. Please enter the direct path to the manifest file.",
                                        fg="red")
    no_zt_network = click.style("You are not part of the {}. Use {} to join the market.".format("{}", join_cmd),
                                fg="red")
    invalid_parameter = "Manifest parameter overrides should be in the form 'key1=\"value1\" " \
                        "key2=\"value2\"."

    invalid_price_format = "Price should be a non-negative integer."
    invalid_port_format = "Port should be an integer between 0 and 65536."

    wrong_ip = click.style("It seems that the IP address that you put in your manifest file (") +\
               click.style("{}", bold=True) +\
               click.style(") is different than your current 21market IP (") +\
               click.style("{}", bold=True) +\
               click.style(")\nAre you sure you want to continue publishing with ") +\
               click.style("{}", bold=True) +\
               click.style("?")

    switch_host = click.style("Please edit ") +\
                  click.style("{}", bold=True) +\
                  click.style(" and replace ") +\
                  click.style("{}", bold=True) +\
                  click.style(" with ") +\
                  click.style("{}.", bold=True)

    publish_start = click.style("Publishing {} at ") + click.style(
        "{}", bold=True) + click.style(" to {}.")

    publish_success = click.style(
        "{} successfully published to {}. It may take a couple of minutes for your app "
        "to show up in the marketplace.\nYou can view your app at https://21.co/mkt.", fg="magenta")

    valid_app_categories = {'blockchain', 'entertainment', 'social', 'markets', 'utilities', 'iot'}

    valid_top_level_manifest_fields = ["schemes", "host", "basePath", "x-21-manifest-path", "info"]
    top_level_manifest_field_missing = click.style("Field '{}' is missing from the manifest file.", fg="red")
    manifest_info_fields = ["contact",
                            "title",
                            "description",
                            "x-21-total-price",
                            "x-21-quick-buy",
                            "x-21-category"]
    manifest_info_field_missing = click.style("Field '{}' is missing from the manifest file under the 'info' section.",
                                              fg="red")

    manifest_contact_fields = {"name", "email"}
    manifest_contact_field_missing = click.style("Field '{}' is missing from the manifest file under the 'contact' section.",
                                                 fg="red")

    price_fields = ["min", "max"]
    price_fields_missing = click.style("Field '{}' is missing from the manifest file under the " \
                                       "'x-21-total-price' section.",
                                       fg="red")
    scheme_missing = click.style("You have to specify either HTTP or HTTPS for your endpoint under the " \
                                 "`schemes` section.",
                                 fg="red")
    invalid_category = click.style("'{}' is not a valid category for the 21 marketplace. Valid categories are {}.",
                                   fg="red")

    # publish-list
    my_apps = "Listing all the published apps by {}: "
    no_published_apps = click.style("You haven't published any apps to the marketplace yet. Use ", fg="blue") +\
                        click.style("21 publish submit {PATH_TO_MANIFEST_FILE}", bold=True, fg="blue") +\
                        click.style(" to publish your apps to the marketplace.", fg="blue")

    app_does_not_exist = "The specified id for the app ({}) does not match any apps in the " \
                         "marketplace."

    # publish delete
    delete_confirmation = "Are you sure that you want to delete the app with id '{}'?"
    delete_success = "App {} ({}) was successfully removed from the marketplace."
    delete_app_not_exist = "The app with id '{}' does not exist in the marketplace."
    delete_app_no_permissions = "You don't have permission to delete the app with id '{}'. You " \
                                "can only delete apps that you have published."

    # sell
    unsupported_package_manager = click.style("Sorry your package manager is not supported. ", fg="red") +\
                                  click.style("Currently two1 only suports: {}", fg="red")
    install_brew = "Please install brew to continue, visit http://brew.sh/"
    unsupported_platform = "Unsupported platform"
    enabling_endpoints = click.style("Enabling endpoints...")
    hosted_market_app_revenue = "- 21.co/{} at {} cents/request...\t" + click.style("[LIVE]", fg="green")
    estimated_daily_revenue = click.style("Estimated revenue: {} cents/day")
    unsuccessfull_python_requirements = click.style("Unsuccessfully installed python requirements: {}", fg="red")
    unsuccessfull_server_requirements = click.style("Unsuccessfully installed server requirements: {}", fg="red")
    app_directory_valid = click.style("App Directory Valid...", fg="magenta")
    app_directory_invalid = click.style("App Directory Invalid. Please ensure" +
                                        "your directory and it's contents are correct, " +
                                        "refer to 21.co/app for futher instructions.", fg="red")
    installing_requirements = click.style("Installing requirements...", fg="magenta")
    installed_requirements = click.style("Successfully installed requirements...", fg="magenta")
    created_nginx_server = click.style("Created default 21 nginx server...", fg="magenta")
    failed_configuring_nginx = "Failed to configure nginx {}"
    created_site_includes = click.style("Created site-includes to host apps...", fg="magenta")
    created_systemd_file = click.style("Systemd file created...", fg="magenta")
    created_app_nginx_file = click.style("Nginx file created...", fg="magenta")
    hosted_app_location = click.style("Your app is now hosted at http://0.0.0.0/{}", fg="magenta")
    listing_enabled_apps = click.style("Listing enabled apps...", fg="magenta")
    no_apps_currently_running = click.style("No apps currently running, refer to 21.co/sell to host some...", fg="red")
    successfully_stopped_app = click.style("Successfully stopped {}...", fg="magenta")
    app_not_enabled = click.style("This app is not within your enabled apps.", fg="red")
    failed_to_destroy_app = click.style("Failed to destroy app, please contact support@21.co", fg="red")
    check_or_create_manifest_file = click.style("Checking or creating manifest file...", fg="magenta")
    success_manifest = click.style("Successfully found or created manifest file...", fg="magenta")
    manifest_fail = click.style("Failed to create manifest file, please contact support@21.co", fg="red")

    # search
    list_all = "Listing all apps in the 21 Marketplace: "
    pagination = click.style("\nEnter the id of the app for more info, ", fg="blue") +\
                 click.style("n", bold=True, fg="blue") +\
                 click.style(" for next page, ", fg="blue") +\
                 click.style("p", bold=True, fg="blue") +\
                 click.style(" for the previous page, ", fg="blue") +\
                 click.style("q", bold=True, fg="blue") +\
                 click.style(" to stop search.", fg="blue")

    empty_listing = click.style("\nCouldn't find any listings that match: '{}'.\n", fg='blue')
    no_app_in_marketplace = click.style("\nThere are currently no apps in the marketplace.", fg="blue")
    # rate
    bad_rating = "App ratings must be between 1 to 5."
    rating_success = click.style("Giving a ") +\
                     click.style("{}/5", bold=True) +\
                     click.style(" rating to the app with id ") +\
                     click.style("{}.", bold=True)

    rating_app_not_found = click.style("App with id {} does not exist in 21 marketplace. Use ", fg="red") +\
                           click.style("21 search", bold=True, fg="red") +\
                           click.style(" to verify the id of the app.", fg="red")

    rating_list = click.style("Listing all the apps that you have rated. \nNote that you can "
                              "update your ratings at anytime with ") + click.style("21 rate\n",
                                                                                    bold=True) + click.style(".")
    no_ratings = click.style("You haven't rated any apps yet.", fg="blue")

    # send

    send_success = ("Successfully sent {0} satoshis to {1}.\ntxid: {2}\ntxn: {3}\n"
                    "To see on the blockchain: https://blockexplorer.com/tx/{2}")
    send_insufficient_confirmed = (
        "Insufficient confirmed balance. However, you can use unconfirmed transactions with --use-unconfirmed.")
    send_insufficient_blockchain = (
        "Insufficient Blockchain balance of {} satoshis.\nCannot send {} satoshis to {}.\n"
        "Run %s, then %s to increase your Blockchain balance." %
        (click.style("21 mine", bold=True), click.style("21 flush", bold=True)))
    send_rejected = ("Transaction rejected.\nYou may have to wait for other transactions to confirm.")

    # logger
    less_env = '-RPpress h for help, q for quit'
    lib_import_warning = click.style(
        "{}\n{: ^80}\n{}".format("#" * 80,
                                 "Warning: two1.lib* pakages have been moved under two1. Update your imports asap!",
                                 "#" * 80), fg="yellow")

    class Error:
        """ Put all Error type uxstrings here """
        # network errors
        connection = click.style("Error: Cannot connect to {}. Please check your Internet connection.", fg="red")
        connection_cli = "An internet connection is required to run this command."
        timeout = "Error: Connection to %s timed out."
        request = click.style("Error: Server request error occurred", fg="red")

        # 500 unknown error
        server_err = click.style("You have experienced a technical error. "
                                 "We are working to correct this issue.",
                                 fg="red")
        non_existing_user = "Error: Username %s does not exist."

        # 403 errors
        server_403 = click.style("Received forbidden error (403). Login in with ", fg="red") +\
                     click.style("21 login ", bold=True, fg="red") +\
                     click.style("and try again.", fg="red")

        # wallet errors
        create_wallet_failed = "Error: Could not create wallet."

        # data unavailable
        data_unavailable = "[ Unavailable ]"

        # file errors
        file_load = "file %s does not exist"
        file_decode = "There was an error loading {}. It may be a corrupt or poorly formatted file."

        # Updater
        update_failed = click.style("Error occurred during update process. Please run a manual update.", fg="red")
        version_not_found = click.style("Could not determine latest two1 version.", fg="red")
        version_does_not_exist = click.style("Version {} doesn't exist. Latest version is {}", fg="red")
        retry_update_after_reboot = "Could not stop wallet daemon. Please reboot your system and retry 21 update."
        invalid_username = "Invalid username. Username must be alphanumeric and between 5-32 characters."
        invalid_email = "Invalid email address."
        update_server_connection = click.style("Could not connect to the update server. Please try again later.",
                                               fg="red")
        account_failed = "Could not create a 21 account. Please contact support at support@21.co"

        # version errors
        version_not_detected = click.style("Could not properly detect your version of 21. "\
                                           "Try reinstalling or contact support@21.co.",
                                           fg="red")
        resource_price_greater_than_max_price = "{} \nPlease use --maxprice to adjust the maximum price."
        insufficient_funds_mine_more = str("Insufficient satoshis for off-chain (zero-fee) transaction. " +\
                                           "Type {} to get more.*\n\n" +\
                                           "You may also use your on-chain balance for this transaction. It will include a {} satoshi tx fee." +\
                                           "To use on-chain balance add {} to your buy command*").format(click.style("21 mine", bold=True),
                                                                                                         {},
                                                                                                         click.style("-p onchain", bold=True))
        # account errors
        login_error_username = "Can not log into account, username not set"
        login_error_mining_auth_pubkey = "Can not log into account, username not set"

        # sell creation errors
        url_not_supported = "Url type is not supported"
        repo_clone_fail = "Failed to clone repo {}"
