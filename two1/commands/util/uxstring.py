"""Strings for the two1 CLI and library."""
import logging

import click

# Creates a ClickLogger. This will not
# not work without the import!
from two1.commands.util.logger import ClickLogger
logging.setLoggerClass(ClickLogger)
logger = logging.getLogger(__name__)


def ux(name, *args, **kwargs):
    """Format the given ux string and print to the log.

    Instead of doing this:
    >>> logger.info(uxstring.UxString.foo.format(username, reward))

    You can do this:
    >>> ux('foo', username, reward)

    This simplifies much of the CLI UX.
    """
    mystr = getattr(UxString, name)
    if len(args) > 0:
        out = mystr.format(*args)
    else:
        out = mystr
    return logger.info(out, **kwargs)


class UxString:
    """ Class to namespace all user experience strings """

    # general
    update_required = click.style("You are using an old version of 21. Please update using the '21 "
                                  "update' command.",
                                  fg="red")
    bitcoin_computer_needed = click.style("You need a 21 Bitcoin Computer (21.co/buy) to access "
                                          "this service. If you believe you have received this "
                                          "message in error, please contact support@21.co.",
                                          fg="red")
    max_accounts_reached = click.style(
        "You have reached the maximum number of 21.co accounts that you can create. ", fg="red") +\
        click.style("Use ", fg="red") +\
        click.style("21 login ", fg="red", bold=True) +\
        click.style("to switch between your available accounts.", fg="red")
    default_price_denomination = "No amount unit provided, defaulting to satoshis. OK?"
    cancel_command = "Not running command."

    # account creation
    creating_account = "Creating 21.co account. Username: {}"
    missing_account = "Looks like you do not have a 21.co account. Let's create one..."
    already_have_account = "Do you already have a 21.co account?"
    please_login = "Please login by running {}".format(click.style("21 login", bold=True))

    account_failed = "Failed to create 21.co account."
    username_exists = "User {} already exists."
    email_exists = "Email {} already exists."
    enter_name = "Enter your full name"
    enter_username = "Enter a username for your 21.co account"
    enter_email = "Enter your email address"
    enter_username_retry = "Create a new username and retry."
    # wallet
    create_wallet = "You do not have a Bitcoin wallet configured. "\
        "Let's create one. Press any key ...\n"
    create_wallet_done = (
        "Wallet successfully created. "
        "You can recover the private key to your wallet using the "
        "following 12 words (in this order) :\n"
        "\n"
        "%s\n"
        "\n"
        "Write down and store these words in a safe place.\n"
        "\n"
        "Press any key ..."
    )

    wallet_daemon_started = "Started wallet daemon. To stop it, type 'wallet stopdaemon'."
    payout_address = "Setting default payout address to: {}"
    get_started = "Check out our introductory guide to learn the basics of 21: https://21.co/learn/intro-to-21/"
    analytics_optin = "\nWould you like to help 21.co collect usage analytics?\n"\
        "This will help us debug any issues and improve software quality."
    analytics_thankyou = "Thank you!\n"
    unconfirmed_email = "Before logging in, you must activate your 21 account using the " \
                        "email sent to you at {}. If you can't find the email, please visit 21.co/activation."

    flush_success = (
        click.style("Flush to Blockchain\n", fg='magenta') +
        "Your satoshis will be sent to you on the Blockchain in the next payout cycle.\n"
        "Estimated time of payout: ~20 minutes.\n"
        "To check progress:  https://blockexplorer.com/address/{}\n"
    )

    # username
    login_username = "\nUsername"
    login_password = "Password (typing will be hidden)"
    login_in_progress = "logging in {}"
    login_required = "Account login is required.\n\n\tRun {} first.".format(click.style("21 login", bold=True))
    incorrect_password = click.style("The username and password that you entered "
                                     "do not match. If you need to reset your "
                                     "password, go to 21.co/reset-password/",
                                     fg="red")

    # sign up
    signin_title = click.style(
        "\nIf you don't have a 21 account, visit 21.co/signup to create one. ", fg="blue")

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

    short_password = "Password must be at least 8 characters long."
    capitalize_password = "Password must contain mix of uppercase or lowercase characters."

    # status
    status_exit_message = "\nUse {} to buy API calls for bitcoin from 21.co.\nFor help, do {}."
    status_empty_wallet = "\nUse {} to get some bitcoin from 21.co."

    status_account = click.style("Logged in as: ", fg='magenta') + "{}\n"

    status_mining = mining = click.style("Mining", fg='magenta') + "\n" +\
        "    Status           : {}\n" +\
        "    Hashrate         : {}\n" +\
        "    Mined (all time) : {} satoshis\n\n" +\
        "Type " +\
        click.style("21 mine --dashboard", bold=True) +\
        " to see a detailed view. Hit q to exit.\n"

    status_wallet = click.style("Total Balance", fg='magenta') + """
    Your spendable buffer at 21.co [1]                        : {twentyone_balance} satoshis
    Your spendable balance on the Blockchain [2]              : {onchain} satoshis
    Your spendable balance in Payment Channels                : {channels_balance} satoshis
    Amount flushing from 21.co buffer to Blockchain balance   : {flushing} satoshis

    [1]: Available for off-chain transactions
    [2]: Available for on-chain and payment channel transactions
    (See 21.co/micropayments for more details)
    """

    status_mining_file_not_found = "Run {} to start mining".format(click.style("21 mine", bold=True))
    status_mining_timeout = "A TimeoutError occurred while getting the hashrate"
    status_mining_success = "A 21 mining chip is running (/run/minerd.pid)"
    status_mining_hashrate = "{:.1f} GH/s"
    status_mining_hashrate_unknown = "~50 GH/s (warming up)"

    status_balance_by_username_header = "Off-chain Buffers by Username \n"
    status_balance_by_username_table_headers = ["Username", "Buffer"]
    status_wallet_detail_off = """\
    To see all wallet addresses and open payment channels, use '21 status --detail'"""

    status_wallet_detail_on = """\
    Addresses:\n{addresses}
    Channels:\n{channels}"""

    status_wallet_address = "\t{}: {} (confirmed), {} (total)\n"
    status_wallet_channel = "\t{}://{}/ {}, {} satoshis, {}\n"
    status_wallet_channels_none = "\tNo payment channels have been created yet.\n"

    # buy
    buy_channel_warning = "Note: The default payment channel size is " + \
        "{} satoshis. \nIn order to open this channel you’ll need to " + \
        "spend a small amount extra to cover transaction fees.\n" + \
        "Read more at (https://21.co/micropayments/)\n" + \
        "Proceed?"
    buy_bad_payment_method = "'{}' is not a supported payment method."
    buy_bad_uri_scheme = "Please provide a valid scheme for the request, such as `http://` and `https://`."
    buy_bad_uri_host = "Please provide a valid hostname for the request, such as `mkt.21.co`."
    buy_channel_aborted = "Payment aborted."
    buy_bad_data_format = "Unknown data format."
    buy_balances = "\nYou spent: {} satoshis. Remaining {} balance: {} satoshis."

    # doctor
    doctor_start = click.style("21 doctor", fg='green') + "\n\n" + \
        click.style("Checking health..", fg='magenta') + "\n"
    doctor_general = click.style("Checking general settings..", fg='yellow')
    doctor_dependencies = click.style("Checking dependencies..", fg='yellow')
    doctor_servers = click.style("Checking servers..", fg='yellow')
    doctor_BC = click.style("Checking Bitcoin Computer dependencies..", fg='yellow')
    doctor_error = click.style("    Error: ", fg='red')
    doctor_total = click.style("Summary", fg='yellow')

    # buybitcoin
    minimum_bitcoin_purchase = click.style("The minimum bitcoin purchase is $2.", fg="red")
    exchange_info_header = click.style("\nExchange Info", fg="magenta")
    exchange_info = "    Exchange Name          : {}\n" \
                    "    Exchange Username      : {}\n" \
                    "    Linked Exchange Wallet : {}\n" \
                    "    Linked Payment Method  : {}\n"
    buybitcoin_instruction_header = click.style("Buying Bitcoin:", fg="magenta")
    buybitcoin_instructions = "    Use " + click.style("21 buybitcoin", bold=True) +\
                              " to buy k satoshis from {}.\n" +\
                              "    Purchased bitcoin will automatically appear in your 21 wallet.\n\n"
    buybitcoin_pairing = \
        "To buy bitcoin, you need to pair your 21 and {} account.\n\n" + \
        "If you haven't done this yet, create a password for your account by " \
        "executing " + click.style("21 login --setpassword", bold=True) + \
        "\nThen go to http://21.co/{}/config/coinbase/ in your " + \
        "browser to complete the pairing.\n"
    buybitcoin_no_payment_method = \
        "To add a payment method to {}, go to {}."
    buybitcoin_confirmation = "\nYou are about to withdraw {} from the bank connected to your " \
                              "Coinbase account to buy {}.\n" \
                              "{} includes {}\n" \
                              "Your bitcoin will be deposited to your local wallet.\n"
    buybitcoin_confirmation_prompt = "Are you sure you want to continue with this purchase?"
    buybitcoin_error = click.style("Error:", bold=True, fg="red") + " {}"
    buybitcoin_success = click.style("\nYou have successfully bought ", fg="magenta") +\
        click.style("{} ", fg="magenta", bold=True) +\
        click.style("for", fg="magenta") +\
        click.style(" {}.\n", bold=True, fg="magenta")

    buybitcoin_success_payout_time = "Your bitcoin will be deposited to your 21 wallet on {}."
    buybitcoin_success_instant = "Your bitcoin will be deposited to your 21 wallet in the next " \
                                 "few minutes."

    coinbase_purchase_in_progress = "\nPurchasing bitcoin from Coinbase...\n"

    coinbase_deposit_type_mapping = {"WALLET": "your Blockchain balance",
                                     "TO_BALANCE": "your 21.co buffer"}
    coinbase_wallet_completed = "The bitcoin you bought at Coinbase was deposited to your wallet on {}"
    coinbase_21_completed = "The bitcoin you bought at Coinbase was added to your on-chain balance. " \
                            "Around {}, {} BTC amount were withdrawn from your " \
                            "Coinbase wallet for this purchase."

    coinbase_wallet_pending = "The bitcoin you bought at Coinbase will be deposited to your wallet around {}"
    coinbase_21_pending = "The bitcoin you bought at Coinbase was added to your on-chain balance immediately. " \
                          "Around {}, {} BTC will be withdrawn from your Coinbase wallet for this " \
                          "purchase."

    coinbase_history_title = click.style("[21 Bitcoin Purchase History]\n", bold=True, fg="magenta")
    coinbase_no_bitcoins_purchased = "[No purchases yet]"
    coinbase_history = click.style(
        "{} : {} bitcoin from your Coinbase to {}.\n",
        fg="cyan") + "Description: {}"
    coinbase_quote_price_satoshis = "The current price for {} {} is {} {}."
    coinbase_quote_price_dollars = "You can get {} {} for {} {}."
    coinbase_max_buy_reached = click.style(
        "You have reached the daily maximum for Bitcoin purchases. Please try again in a few "
        "hours.", fg="red")
    coinbase_needs_photo_id = click.style(
        "You need to supply a photo ID to Coinbase. "
        "Please do this at: https://www.coinbase.com/photo-id", fg="red")
    coinbase_needs_username = click.style(
        "You need to set a username for your Coinbase profile. "
        "Please do this at: https://www.coinbase.com/settings", fg="red")
    coinbase_amount_too_high = click.style(
        "The amount you entered is too high. The maximum daily bitcoin purchase limit "
        "is 100 USD.", fg="red")

    # earning
    use_21_earn_instead = "Try 21 earn instead. 21 mine only works on a 21 Bitcoin Computer."
    earn_start = "Earn bitcoin by doing microtasks."
    earn_task_notyet = "Only the 'faucet' task is currently available. Check back for the '{}' microtask soon."
    earn_task_use_faucet = "This option will be available soon. Use 21 faucet to request bitcoin."

    # earning - faucet
    earn_faucet_banner = "Request bitcoin from the 21.co faucet"
    earn_faucet_ineligible = "Sorry, you can't hit the 21.co faucet now. Try again later."
    earn_faucet_start = "{}, you are requesting {} satoshis from 21.co\n" \
        "This requires you to do some CPU proof-of-work, which will take a little while...\n"
    earn_faucet_success = "\n{}, you got {} satoshis in {:.1f} seconds!"
    earn_faucet_status = "\nHere's the new status of your balance after hitting the faucet:\n"
    earn_faucet_finish = "\nView your balance with {}, or spend with {}."
    earn_limit_reached = "\nFurther earning advances are not possible at this time. " \
                         "Please try again in a few hours."
    lifetime_earn_limit_reached = "You have reached the faucet earning limit for your account. " \
                                  "Please visit 21.co/learn to discover new ways you can earn " \
                                  "bitcoin."

    no_earn_allocations = (
        "Please enable the faucet by connecting a social network to your 21 account at {}/{}/config/social."
    )

    # mining
    mining_show_dashboard_prompt = "About to show the 21 mining dashboard!\n\n" + \
        "Hit any key to launch the dashboard. "
    mining_show_dashboard_context = "\nDo " + click.style("21 mine --dashboard", bold=True) + \
        " to see a mining dashboard.\n" + \
        "Do " + click.style("21 log", bold=True) + " to see more aggregated stats.\n" + \
        "Or just do " + click.style("21 status", bold=True) + " to see your mining progress."
    mining_dashboard_no_bc = click.style("The mining dashboard is only available on the Bitcoin Computer.")

    mining_chip_start = "21 Bitcoin Chip detected, trying to (re)start miner..."
    mining_chip_running = "Your 21 Bitcoin Chip is already running!\n" + \
        "You should now receive a steady stream of satoshis."
    mining_start = "\n{}, you are mining {} satoshis from 21.co\n" \
                   "This may take a little while...\n"
    mining_dashboard_no_chip = "Without a 21 mining chip, we can't show you a mining dashboard.\n"\
        "If you want to see this dashboard, run this command on a 21 Bitcoin Computer."
    mining_success = "\n{}, you mined {} satoshis in {:.1f} seconds!"
    mining_status = "\nHere's the new status of your balance after mining:\n"
    mining_finish = "\nView your balance with {}, or spend with {}."

    daily_mining_limit_reached = "\nFurther mining advances are not possible at this time. " \
                                 "Please try again in a few hours."

    mining_bitcoin_computer_needed = click.style(
        "You need a 21 Bitcoin Computer (21.co/buy) to access this service. \nYou can use ", fg="red") +\
        click.style("21 buybitcoin", bold=True, fg="red") +\
        click.style(" to add Bitcoins to your account instead. \nIf you believe you have received this ", fg="red") +\
        click.style("message in error, please contact support@21.co.", fg="red")

    # uninstall
    uninstall_init = "Uninstalling 21's software libraries and tools."
    uninstall_success = "21 has been successfully uninstalled."

    superuser_password = "You might need to enter your superuser password."

    # flush
    flush_status = "\n* Your flushed amount of %s satoshis will appear " \
                   "in your wallet balance as soon as they appear on the Blockchain."

    flush_insufficient_earnings = "You need to flush a minimum of 20000 satoshis."

    flush_not_enough_earnings = "You don't have enough balance to flush {} satoshis."

    flush_invalid_address = click.style(
        "The Bitcoin address you specified is not a valid Bitcoin address.", fg="red")
    # ad
    buy_ad = click.style("Get a 21 Bitcoin Computer at https://21.co/buy", fg="magenta")

    # inbox
    reasons = {
        "CLI": "You just received a little bit of bitcoin.",
        "Shares": "You submitted work through the 21 Bitcoin Computer.",
        "flush_payout": "You performed 21 flush to move your earnings to the "
                        "Blockchain.",
        "earning_payout": "This is a periodic payout of your mining earnings to "
                          "the Blockchain.",
        "BC": "Your bitcoin bonus for booting the 21 Bitcoin Computer.",
        "coinbase_purchase": "You bought and transferred bitcoin to your account through "
                             "Coinbase.",
        "linkedin_connection": "You connected your Linkedin profile to your 21 account."
    }

    empty_logs = "[No events yet]"

    notification_intro = click.style("[Account Notifications]\n\n", bold=True,
                                     fg="magenta")

    log_intro = click.style("[21 Activity Log]\n\n", bold=True, fg="magenta")

    debit_message = "{} : {:+d} satoshis to your 21.co balance"
    blockchain_credit_message = "{} : {:+d} satoshis from your 21.co balance, " \
                                "{:+d} satoshis to your Blockchain balance"
    credit_message = "{} : {:+d} satoshis from your 21.co balance"

    buy_message = "You bought '{}' from {}"
    sell_message = "You sold '{}' to {}"

    unread_notifications = click.style("\nYou have {} unread notifications. Type ", fg="blue") +\
        click.style("21 inbox", bold=True, fg="blue") +\
        click.style(" to view your notifications.", fg="blue")

    # join
    successful_join = "Joined network {}. It may take a few seconds for joining " \
                      "to take effect.\nRun " +\
                      click.style("21 join --status", bold=True, fg="blue") +\
                      " to verify you have successfully joined."
    invalid_network = "Invalid network specified, please verify the network name."
    join_cmd = click.style("21 join", bold=True, reset=False)

    no_network = click.style("You are not part of any network. Run: 21 join", fg="blue")
    install_zerotier = click.style("To join a network you must have zerotier-one installed.\n"
                                   "See installation instructions at:\n"
                                   "\n\thttps://www.zerotier.com/product-one.shtml\n")

    join_network_beta_warning = """
21 is in Beta: warning
----------------------
Note that by executing this command you make it possible for others
to directly connect to you in order to buy your digital goods for
bitcoin. You can stand up a bitcoin-payable server instantly on any
machine that others can buy from.  As such, please remember that the
21 software is in beta and not ready for commercial release.  WE ARE
PROVIDING THE 21 SOFTWARE AS-IS, AND YOU ASSUME ALL RISK OF USING
21 WHILE IN BETA.  To help protect the security of your systems when
using 21 while in beta, we recommend you running the software on an
EC2 instance, an old laptop, or a small standalone machine like a 21
Bitcoin Computer (21.co/buy) or DIY Bitcoin Computer (21.co/diy).
"""
    join_network_beta_exit = "OK, understood. Check out 21.co/buy or 21.co/diy to set up a standalone machine."

    # publish
    publish_docs_url = click.style("https://21.co/learn/21-publish/", bold=True)
    publish_instructions = "For instructions on publishing your app, please refer to {}".format(publish_docs_url)

    manifest_missing = click.style("Could not find the manifest file at {}.", fg="red")

    bad_manifest = "{}{}".format("The following error occurred while reading your manifest file at {}:\n{}\n\n",
                                 publish_instructions)

    malformed_yaml = click.style("Your manifest file at {} is not valid YAML.", fg="red")
    large_manifest = click.style("The size of the manifest file at {} exceeds the maximum limit of 2MB.", fg="red")

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

    app_url_claimed = "The endpoint {} specified in your manifest has already been registered in " \
                      "the marketplace by another user.\nPlease check your manifest file and make " \
                      "sure your 'host' field is correct.\nIf the problem persists please contact " \
                      "support@21.co."

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
    manifest_contact_field_missing = click.style(
        "Field '{}' is missing from the manifest file under the 'contact' section.", fg="red")

    price_fields = ["min", "max"]
    price_fields_missing = click.style("Field '{}' is missing from the manifest file under the "
                                       "'x-21-total-price' section.",
                                       fg="red")
    scheme_missing = click.style("You have to specify either HTTP or HTTPS for your endpoint under the "
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
    app_directory_valid = click.style("App directory valid...", fg="magenta")
    app_directory_invalid = click.style("App directory is invalid. Please ensure" +
                                        "your directory and its contents are correct, " +
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
    send_success = ("Successfully sent {0} satoshis to {1}.\ntxid: {2}\n"
                    "To see on the blockchain: https://blockexplorer.com/tx/{2}")
    send_success_verbose = ("Successfully sent {0} satoshis to {1}.\ntxid: {2}\ntxn: {3}\n"
                            "To see on the blockchain: https://blockexplorer.com/tx/{2}")
    send_insufficient_confirmed = ("Insufficient confirmed balance. However, you can use unconfirmed"
                                   " transactions with --use-unconfirmed. ")
    send_insufficient_blockchain_21bc = (
        "Insufficient Blockchain balance of {} satoshis.\nCannot send {} satoshis to {}.\n"
        "Run %s, then %s to increase your on-chain balance." %
        (click.style("21 mine", bold=True), click.style("21 flush", bold=True)))
    send_insufficient_blockchain_free = (
        "Insufficient Blockchain balance of {} satoshis.\nCannot send {} satoshis to {}.\n"
        "Run %s, then %s to increase your on-chain balance." %
        (click.style("21 earn", bold=True), click.style("21 flush", bold=True)))
    send_rejected = ("Transaction rejected.\nYou may have to wait for other transactions to confirm.")

    # logger
    lib_import_warning = click.style(
        "\n".join((
            "#" * 80,
            "Warning: two1.lib.* packages have been moved to two1.*",
            "Update your imports immediately!",
            "",
            "For example:",
            "-from two1.lib.wallet import Wallet",
            "+from two1.wallet import Wallet",
            "#" * 80
        )),
        fg="yellow")

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

        invalid_username = "Invalid username. Username must be alphanumeric and between 5-32 characters."
        invalid_email = "Invalid email address."
        account_failed = "Could not create a 21 account. Please contact support at support@21.co"
        suspended_account = "Your account has been suspended for suspicious behavior. Please " \
                            "contact support@21.co for details."

        # version errors
        resource_price_greater_than_max_price = "{} \nPlease use --maxprice to adjust the maximum price."
        insufficient_funds_mine_more = str(
            "Insufficient satoshis for off-chain (zero-fee) transaction. Type {} to view your balance. "
            "Type {} to get more satoshis.\n\nYou may also"
            " use your on-chain balance for this transaction. It will include a small tx fee. To use "
            "on-chain balance add {} to your buy command."
        ).format(click.style("21 status", bold=True), click.style("21 earn", bold=True),
                 click.style("-p onchain", bold=True))
        insufficient_funds_earn_more = str(
            "Insufficient satoshis for off-chain (zero-fee) transaction. Type {} to view your balance. "
            "Type {} to get more satoshis.\n\nYou may also"
            " use your on-chain balance for this transaction. It will include a small tx fee. To use "
            "on-chain balance add {} to your buy command."
        ).format(click.style("21 status", bold=True), click.style("21 earn", bold=True),
                 click.style("-p onchain", bold=True))

        # account errors
        login_error_username = "Can not log into account, username not set"
        login_error_mining_auth_pubkey = "Can not log into account, username not set"

        # sell creation errors
        url_not_supported = "URL type is not supported"
        repo_clone_fail = "Failed to clone repo {}"
