""" 21 sell CLI helper methods.

Helper methods for interactive CLI commands.

"""
# python standard imports
import os
import re
import time
import json

import sys
import yaml
import logging
import threading
import subprocess
from collections import namedtuple

# 3rd party imports
import click

# two1 imports
from two1 import wallet
import two1.channels as channels
from two1.wallet import Two1Wallet
from two1 import TWO1_HOST as TWO1_HOST
from two1.server import machine_auth_wallet
from two1.blockchain import TwentyOneProvider
from two1.sell.installer import InstallerAWSUbuntuDebian
from two1.sell.machine import Two1Machine, Two1MachineVirtual
from two1.sell.composer import Two1Composer
from two1.sell.util.stats_db import Two1SellDB
from two1.server import rest_client as _rest_client
from two1.commands.util.exceptions import ServerRequestError

logger = logging.getLogger(__name__)

MENU_COLOR = "blue"
TITLE_COLOR = "cyan"
PROMPT_COLOR = "yellow"
WIDTH = 35

VmConfiguration = namedtuple('VmConfiguration', ['disk_size',
                                                 'vm_memory',
                                                 'server_port',
                                                 'network_interface'])


def start_long_running(text, long_running_function, *args, **kwargs):
    """ Start a thread for a background job.
    """
    results = []
    args = list(args)
    long_running_thread = threading.Thread(target=run_long_running,
                                           args=tuple([long_running_function, results] + args),
                                           kwargs=kwargs)
    spin_thread = threading.Thread(target=dots, args=(text, long_running_thread))

    long_running_thread.start()
    spin_thread.start()
    long_running_thread.join()
    spin_thread.join()

    result = results[0]
    if isinstance(result, Exception):
        raise result
    else:
        return result


def run_long_running(long_running_function, results, *args, **kwargs):
    try:
        result = long_running_function(*args, **kwargs)
    except Exception as e:
        results.append(e)
    else:
        results.append(result)


def dots(text, long_thread):
    """ Print dots to terminal during long running job.
    """
    logger.info(click.style(text), fg=TITLE_COLOR, nl=False)
    while True:
        if long_thread not in threading.enumerate():
            logger.info(click.style('...', fg=TITLE_COLOR))
            return
        for i in range(4):
            logger.info(click.style('.' * i, fg=TITLE_COLOR), nl=False)
            time.sleep(.3)
            logger.info('\b' * i, nl=False)
            logger.info(' ' * i, nl=False)
            logger.info('\b' * i, nl=False)


def install_missing_dependencies(dependencies_list, installer):
    """ Install missing dependencies.
    """
    if False in [docker_dep[1] for docker_dep in dependencies_list if
                 docker_dep[0] in installer.DOCKER_TOOLS]:
        subprocess.check_output(["sudo", "-k"])
        subprocess.check_output(["sudo", "-S", "whoami"])
        docker_installed = start_long_running("Installing Docker Tools",
                                              installer.install_docker_tools)
        print_str("Docker",
                  ["Installed" if docker_installed else "Not installed"],
                  "TRUE" if docker_installed else "FALSE",
                  docker_installed)
        if [vb_dep[1] for vb_dep in dependencies_list if vb_dep[0] == "Zerotier"][0] is False:
            zerotier_installed = start_long_running("Installing ZeroTier",
                                                    installer.install_zerotier)
            print_str("ZeroTier",
                      ["Installed" if zerotier_installed else "Not installed"],
                      "TRUE" if zerotier_installed else "FALSE",
                      zerotier_installed)
        installed = installer.check_dependencies()
        return package_check(installed, True)
    else:
        return True


def check_needs_logout(generic_installer):
    """ Require logout if AWS docker user group not yet updated.

        Returns: (bool) True:  if user does not need to restart
                 (bool) False:
    """
    if isinstance(generic_installer.installer, InstallerAWSUbuntuDebian):
        if not generic_installer.installer.already_in_group():
            logger.info(click.style(
                "Docker installation requires a user to log out and log "
                "back in. Please do so and re-run this command.", fg="magenta"))
            return True
    return False


def get_user_credentials(two1_dir="~/.two1/two1.json"):
    """ Collect user credentials at CLI.
    """

    with open(os.path.expanduser(two1_dir), "r") as f:
        username = json.load(f)["username"]
    try:
        w = wallet.Wallet()
    except:
        logger.info(click.style("A technical error occured. Please try the previous command again.", fg="magenta"))
        sys.exit()
    machine_auth = machine_auth_wallet.MachineAuthWallet(w)
    rest_client = _rest_client.TwentyOneRestClient(TWO1_HOST, machine_auth, username)
    address = w.current_address

    correct_password = False
    pw = click.prompt(click.style("Please enter your 21 password", fg=PROMPT_COLOR), hide_input=True)

    while not correct_password:
        try:
            resp = rest_client.login(payout_address=address, password=pw)
            correct_password = True
        except Exception:
            pw = click.prompt(click.style("Incorrect 21 password. Please try again", fg="magenta"),
                              hide_input=True)

    return (username, pw)


def get_vm_options():
    """ Get user-selected config options for the 21 VM.
    """

    logger.info(click.style("Configure 21 virtual machine:", fg=TITLE_COLOR))
    logger.info("Press return to accept defaults.")

    default_disk = Two1MachineVirtual.DEFAULT_VDISK_SIZE
    default_memory = Two1MachineVirtual.DEFAULT_VM_MEMORY
    default_port = Two1MachineVirtual.DEFAULT_SERVICE_PORT
    default_network = Two1MachineVirtual.DEFAULT_ZEROTIER_INTERFACE

    disk_size = click.prompt("  Virtual disk size in MB (default = %s)" % default_disk,
                             type=int, default=default_disk, show_default=False)
    vm_memory = click.prompt("  Virtual machine memory in MB (default = %s)" % default_memory,
                             type=int, default=default_memory, show_default=False)
    server_port = click.prompt("  Port for micropayments server (default = %s)" % default_port,
                               type=int, default=default_port, show_default=False)
    network_interface = click.prompt("  Network interface (default = %s)" % default_network,
                                     default=default_network, show_default=False)

    return VmConfiguration(disk_size=disk_size,
                           vm_memory=vm_memory,
                           server_port=server_port,
                           network_interface=network_interface)


def write_machine_config(vm_dict):
    with open(Two1Machine.MACHINE_CONFIG_FILE, "w") as f:
        json.dump(vm_dict, f)


def get_server_port():
    """ Get user-selected server port.

    This is used for native docker engine on AWS.

    """

    logger.info(click.style("Configure 21 micropayments server:", fg=TITLE_COLOR))
    logger.info("Press return to accept default.")

    default_port = Two1Machine.DEFAULT_SERVICE_PORT

    server_port = click.prompt("  Port for micropayments server (default = %s)" % default_port,
                               type=int, default=default_port, show_default=False)

    return server_port


def print_str(title, message, status_text, status_state, force=False):
    """ Print formatted string.
    """

    width = WIDTH
    if status_state:
        color = "green"
    else:
        color = "red"
    if force:
        grouped = message
    else:
        grouped = []
        for line in message:
            split = line.split()
            pre_add = ""
            i = 0
            while i < len(split):
                word = split[i]
                if len(word) > width:
                    grouped.append(word)
                    i += 1
                    continue
                post_add = pre_add + word + " "
                if len(post_add) > width:
                    grouped.append(pre_add)
                    pre_add = ""
                else:
                    i += 1
                    pre_add = post_add
            grouped.append(pre_add)
    logger.info("  {0: <{width}}->  {1: <{width}}  [{2}]".format(
                title,
                grouped[0] if len(message) != 0 else "",
                click.style(str(status_text), fg=color),
                width=width))
    if len(grouped) > 1:
        for group in grouped[1:]:
            logger.info(41*" " + "{0: <{width}}".format(
                        group,
                        width=width))


def print_str_no_stat(message):
    logger.info(37*" " + "->  " + "{0: <{width}}".format(
                message[0],
                width=WIDTH))
    if len(message) > 1:
        for line in message[1:]:
            logger.info(41*" " + "{0: <{width}}".format(
                        line,
                        width=WIDTH))


def package_check(package_stats, log_messages):
    """ Check for installed packages.
    """
    if sum([i[1] for i in package_stats]) == len(package_stats):
        if log_messages:
            print_str("Dependencies",
                      ["Installed"],
                      "TRUE",
                      True)
        all_installed = True
    else:
        if log_messages:
            for package in package_stats:
                print_str("%s" % package[0].title(),
                          ["Installed" if package[1] else "Not installed"],
                          "TRUE" if package[1] else "FALSE",
                          package[1])
        all_installed = False
    return all_installed


def vm_running_check(vm_up_status, log_not_running=False):
    """ Check if 21 virtual machine is running.
    """
    if vm_up_status:
        print_str("Virtual machine",
                  ["Running"],
                  "TRUE",
                  True)
    elif log_not_running:
        print_str("Virtual machine",
                  ["Not running"],
                  "FALSE",
                  False)
    return True if vm_up_status else False


def zerotier_service_check(zt_status, log_not_running=False):
    """ Check if ZeroTier One network service running.
    """
    if zt_status:
        print_str("ZeroTier",
                  ["Running"],
                  "TRUE",
                  True)
    elif log_not_running:
        print_str("ZeroTier",
                  ["Not running"],
                  "FALSE",
                  False)
    return zt_status


def market_connected_check(mkt_network_status, log_not_running=False):
    """ Check if 21market network connected.
    """
    if mkt_network_status.lower() != "":
        print_str("21 Marketplace",
                  ["Connected", "Your IP: %s" % mkt_network_status.lower()],
                  "TRUE",
                  True)
    elif log_not_running:
        print_str("21 Marketplace",
                  ["Not connected"],
                  "FALSE",
                  False)
    return True if mkt_network_status.lower() != "" else False


def router_running_check(router_status, log_not_running=False):
    """ Check if router service is running.
    """
    if router_status.lower() == "running":
        print_str("Router",
                  ["Running"],
                  "TRUE",
                  True)
    elif log_not_running:
        print_str("Router",
                  ["Not running"],
                  "FALSE",
                  False)
    return True if router_status.lower() != "" else False


def payments_server_running_check(payments_server_status, log_not_running=False):
    """ Check if payments server service is running.
    """
    if payments_server_status.lower() == "running":
        print_str("Payments",
                  ["Running"],
                  "TRUE",
                  True)
    elif log_not_running:
        print_str("Payments",
                  ["Not running"],
                  "FALSE",
                  False)
    return True if payments_server_status.lower() != "" else False


def service_status_check(start_stats, print_earnings=True):
    """ Check status of services.
    """
    rest_client = get_rest_client()
    dollars_per_sat = rest_client.quote_bitcoin_price(1).json()["price"]

    services_list = [i[0] for i in start_stats]

    earnings = get_earnings(services_list)

    for service_info in start_stats:
        service = service_info[0]
        if print_earnings:
            request_count = earnings[service]["request_count"]

            total_earnings = (earnings[service]["buffer"] +
                              earnings[service]["wallet"] +
                              earnings[service]["channels"])
            usd_earnings = total_earnings * dollars_per_sat

            message = [service_info[2],
                       "[Totals]",
                       "Requests:   %d" % request_count,
                       "Earnings: $%.4f" % usd_earnings]
        else:
            message = [service_info[2]]
        print_str(service,
                  message,
                  "TRUE" if service[1] else "FALSE",
                  service[1])


def get_example_usage(services, host, port):
    """ Gets example usage of given services.
    """
    example_usages = {}
    for service in services:
        if service.lower() == 'ping':
            example_usages[service] = "21 buy '{}:{}/ping/?uri=21.co'".format(host, port)
    return example_usages


def service_status_check_detailed(start_stats, host, port):
    """ Gives detailed status of services.
    """
    rest_client = get_rest_client()
    dollars_per_sat = rest_client.quote_bitcoin_price(1).json()["price"]

    services_list = [i[0].lower() for i in start_stats]
    balances = get_balances(services_list, rest_client)
    earnings = get_earnings(services_list)
    example_usages = get_example_usage(services_list, host, port)

    for service_info in start_stats:
        service = service_info[0].lower()
        request_count = earnings[service]["request_count"]

        buffer_earn_sat = earnings[service]["buffer"]
        wallet_earn_sat = earnings[service]["wallet"]
        channels_earn_sat = earnings[service]["channels"]

        buffer_bal_sat = balances[service]["buffer"]
        wallet_bal_sat = balances[service]["wallet"]
        channels_bal_sat = balances[service]["channels"]

        print_str(service.title(),
                  [service_info[2]],
                  "TRUE" if service_info[1] else "FALSE",
                  service_info[1])

        print_str_no_stat(["Requests: %s" % str(request_count).rjust(10)])
        print_str_no_stat(["Lifetime Earnings:",
                           build_detail_line("buffer", buffer_earn_sat, dollars_per_sat),
                           build_detail_line("wallet", wallet_earn_sat, dollars_per_sat),
                           build_detail_line("channels", channels_earn_sat, dollars_per_sat)])

        print_str_no_stat(["Current Balances:",
                           build_detail_line("buffer", buffer_bal_sat, dollars_per_sat),
                           build_detail_line("wallet", wallet_bal_sat, dollars_per_sat),
                           build_detail_line("channels", channels_bal_sat, dollars_per_sat)])
        if service in example_usages:
            print_str_no_stat(["Example Usage:",
                               example_usages[service]])


def build_detail_line(btc_type, satoshi, exchange_rate):
    line_form = "- %s %s %s"
    btc_formatted = ("%s " % btc_type.title()).ljust(9)
    satoshi_formatted = str(satoshi).rjust(9)
    usd_formatted = ("($%0.4f)" % (satoshi*exchange_rate)).rjust(10)
    detail_line = line_form % (btc_formatted, satoshi_formatted, usd_formatted)
    return "- " + btc_formatted + satoshi_formatted + usd_formatted


def get_balances(services, client):
    """ Gets wallet balances of given services.
    """
    buffer_balance = get_buffer_balance(client)
    with open(Two1Composer.SERVICES_WALLET_FILE, "r") as f:
        services_info = json.load(f)

    provider = TwentyOneProvider()
    balances = {}
    for service in services:
        template = {"buffer": None,
                    "wallet": None,
                    "channels": None}
        template["buffer"] = buffer_balance
        try:
            service_mnemonic = services_info.get(service).get("mnemonic")

            wallet = Two1Wallet.import_from_mnemonic(provider, service_mnemonic)
            template["wallet"] = wallet.balances["total"]

            channel_client = channels.PaymentChannelClient(wallet)
            channel_client.sync()
            channel_urls = channel_client.list()
            channels_balance = sum(s.balance for s in (channel_client.status(url) for url in channel_urls) if s.state == channels.PaymentChannelState.READY)
            template["channels"] = channels_balance
        except AttributeError:
            template["wallet"] = 0
            template["channels"] = 0

        balances[service] = template
    return balances


def get_buffer_balance(client):
    """ Gets 21 buffer balance of user associated with client.
    """
    return client.get_earnings()["total_earnings"]


def get_earnings(services):
    """ Gets earnings of given services.
    """
    db = Two1SellDB()

    earnings = {}
    for service in services:
        service_earnings = db.get_earnings(service.lower())
        earnings[service] = {"wallet": service_earnings["wallet_earnings"],
                             "buffer": service_earnings["buffer_earnings"],
                             "channels": service_earnings["channel_earnings"],
                             "request_count": service_earnings["request_count"]}
    return earnings


def get_rest_client():
    """ Helper method to create rest_client.
    """
    with open(os.path.expanduser("~/.two1/two1.json"), "r") as f:
        username = json.load(f)["username"]

    try:
        w = wallet.Wallet()
    except:
        logger.info(click.style("A technical error occured. Please try the previous command again.", fg="magenta"))
        sys.exit()

    machine_auth = machine_auth_wallet.MachineAuthWallet(w)
    rest_client = _rest_client.TwentyOneRestClient(TWO1_HOST, machine_auth, username)
    return rest_client


def get_published_apps():
    with open(os.path.expanduser("~/.two1/two1.json"), "r") as f:
        username = json.load(f)["username"]

    rest_client = get_rest_client()
    first_page = rest_client.get_published_apps(username, 0).json()
    if first_page["total_pages"] == 0:
        return []

    url_service_pattern = re.compile(r"""^http(s|)://(?P<zt_ip>((\d){1,3}.){3}(\d){1,3}):(?P<port>\d*)/(?P<service>(\w*))""")

    published_app_urls = []
    for app in first_page["results"]:
        match = url_service_pattern.search(app["app_url"])
        if match is not None:
            published_app_urls.append("%s:%s/%s" % (match.group("zt_ip"), match.group("port"), match.group("service").lower()))

    for i in range(1, first_page["total_pages"]):
        page = rest_client.get_published_apps(username, i).json()
        for app in page["results"]:
            match = url_service_pattern.search(app["app_url"])
            if match is not None:
                published_app_urls.append("%s:%s/%s" % (match.group("zt_ip"), match.group("port"), match.group("service").lower()))
    return published_app_urls


def prompt_to_publish(start_stats, manager):
    zt_ip = manager.get_market_address()
    port = manager.get_server_port()

    published_apps = get_published_apps()
    started_apps = ["%s:%s/%s" % (zt_ip, port, i[0].lower()) for i in start_stats if i[1]]
    not_published = [i for i in started_apps if i not in published_apps]
    not_published_names = [i.split("/")[1] for i in not_published]

    if len(not_published) == 0:
        return []
    if click.confirm(click.style("Would you like to publish the sucessfully started services?", fg=PROMPT_COLOR)):
        time.sleep(2)
        published = start_long_running("Publishing services",
                                       publish_started,
                                       not_published_names,
                                       zt_ip,
                                       port,
                                       manager)
        return published
    else:
        return []


def publish_started(not_published, zt_ip, port, manager):
    rest_client = get_rest_client()

    publish_stats = []
    for service in not_published:
        manifest_path = os.path.join(Two1Composer.SERVICES_DIR,
                                     service,
                                     "manifest.yaml")
        with open(manifest_path, "r") as f:
            manifest_json = yaml.load(f)

        manifest_json["basePath"] = "/%s" % service
        manifest_json["host"] = "%s:%s" % (zt_ip, port)
        manifest_json["info"]["x-21-quick-buy"] = manifest_json["info"]["x-21-quick-buy"] % (zt_ip, port, service)

        manifest_write_path = os.path.join(os.path.dirname(Two1Composer.COMPOSE_FILE), "%s_manifest.yaml" % service)

        with open(manifest_write_path, "w") as f:
            yaml.dump(manifest_json, f)

        try:
            resp = rest_client.publish({"manifest": manifest_json,
                                        "marketplace": "21market"})
            if resp.status_code == 201:
                publish_stats.append((service.title(), True, ["Published"]))
            else:
                publish_stats.append((service.title(), False, ["Failed to publish"]))
        except ServerRequestError as e:
            if e.status_code == 403 and e.data.get("error") == "TO600":
                publish_stats.append((service.title(), False, ["Endpoint already published"]))
            else:
                publish_stats.append((service.title(), False, ["Failed to publish"]))
        except Exception:
            publish_stats.append((service.title(), False, ["An unknown error occurred"]))

    return publish_stats


def start_dict_to_list(start_dict):
    start_stats_list = sorted(start_dict.items(), key=lambda k: k[1]["order"])
    formatted_stats = [("%s" % service[0].title(), service[1]["started"], service[1]["message"])
                       for service in start_stats_list]
    return formatted_stats


def stop_dict_to_list(stop_dict):
    stop_stats_list = sorted(stop_dict.items(), key=lambda k: k[1]["order"])
    formatted_stats = [("%s" % service[0].title(), service[1]["stopped"], service[1]["message"])
                       for service in stop_stats_list]
    return formatted_stats


def service_earning_check(services, detailed_view):
    rest_client = get_rest_client()
    dollars_per_sat = rest_client.quote_bitcoin_price(1).json()["price"]
    earnings = get_earnings(services)

    for service in services:
        request_count = earnings[service]["request_count"]
        buffer_earn = earnings[service]["buffer"]
        wallet_earn = earnings[service]["wallet"]
        channels_earn = earnings[service]["channels"]
        if detailed_view:
            message = ["Requests: %s" % request_count,
                       build_detail_line("buffer", buffer_earn, dollars_per_sat),
                       build_detail_line("onchain", wallet_earn, dollars_per_sat),
                       build_detail_line("channels", channels_earn, dollars_per_sat)]

        else:
            total_earnings = buffer_earn + wallet_earn + channels_earn
            message = ["Requests: %s" % request_count,
                       "Earnings: $%.4f" % (total_earnings * dollars_per_sat)]
        print_str_no_label(service, message)


def service_balance_check(services):
    rest_client = get_rest_client()
    dollars_per_sat = rest_client.quote_bitcoin_price(1).json()["price"]

    provider = TwentyOneProvider()
    payments_server_balance = get_payments_server_balance(provider)
    balances = get_balances(services, rest_client)

    for service in services:
        bal = balances[service]["wallet"]
        print_str_no_label(service, [build_detail_line("onchain", bal, dollars_per_sat)])

    payments_onchain = payments_server_balance["onchain"]
    payments_channels = payments_server_balance["channels"]
    print_str_no_label("payments", [build_detail_line("onchain", payments_onchain, dollars_per_sat),
                                    build_detail_line("channels", payments_channels, dollars_per_sat)])


def get_payments_server_balance(provider):
    with open(Two1Composer.PAYMENTS_WALLET_FILE, "r") as f:
        info = json.load(f)

    mnemonic = info["mnemonic"]
    wallet = Two1Wallet.import_from_mnemonic(provider, mnemonic)

    balances = {"onchain": None,
                "channels": None}

    balances["onchain"] = wallet.balances["total"]

    channel_client = channels.PaymentChannelClient(wallet)
    channel_client.sync()
    channel_urls = channel_client.list()
    channels_balance = sum(s.balance for s in (channel_client.status(url) for url in channel_urls) if s.state == channels.PaymentChannelState.READY)

    balances["channels"] = channels_balance

    return balances


def print_str_no_label(title, message):
    logger.info("  {0: <{width}}->  {1: <{width}}".format(
                title.title(),
                message[0],
                width=WIDTH))
    if len(message) > 1:
        for line in message[1:]:
            logger.info(41*" " + "{0: <{width}}".format(
                        line,
                        width=WIDTH))


def print_example_usage(services, host, port):
    usage = get_example_usage(services, host, port)
    for service in services:
        print_str_no_label(service, [usage[service]])
