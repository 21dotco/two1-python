""" Sell web services for micropayments.
"""
# standard python imports
import sys
import json
import logging

# 3rd party imports
import click

# two1 imports

import two1.commands.util.decorators as decorators

from two1.sell.machine import VmState
from two1.sell.machine import Two1MachineVirtual
from two1.sell.composer import Two1Composer
from two1.sell.manager import get_manager
from two1.sell.installer import Two1SellInstaller
from two1.sell.util.client_helpers import get_platform
from two1.sell.util import cli_helpers as cli_helpers
from two1.sell.exceptions.exceptions_sell import Two1SellNotSupportedException
from two1.sell.exceptions.exceptions_machine import (Two1MachineStartException,
                                                     Two1MachineNetworkStartException,
                                                     Two1MachineCreateException,
                                                     Two1MachineDeleteException,
                                                     Two1MachineStopException)

from two1.wallet import Two1Wallet
from two1.wallet import fees as txn_fees
from two1.wallet.exceptions import WalletBalanceError, DustLimitError
from two1.blockchain import TwentyOneProvider

# create click logger
from two1.wallet.utxo_selectors import _fee_calc

logger = logging.getLogger(__name__)


@click.group(invoke_without_command=True)
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def sell(ctx, **options):
    """
Start local server to sell APIs for bitcoin.

\b
Usage
_____
List services available to sell.
$ 21 sell list

\b
Start selling a single service.
$ 21 sell start <service_name>

\b
Stop selling a single service.
$ 21 sell stop <service_name>

\b
Start selling all available services.
$ 21 sell start --all

\b
Get status on all running services.
$ 21 sell status

\b
Stop all running services.
$ 21 sell stop --all

\b
Get additional information on commands.
$ 21 sell start --help
$ 21 sell status --help
$ 21 sell stop --help
"""

    try:
        sysdata = get_platform()
        manager = get_manager(sysdata)
        installer = Two1SellInstaller(sysdata.detected_os, sysdata.detected_distro)
    except Two1SellNotSupportedException:
        try:
            logger.info(click.style(sysdata.help_message, fg="magenta"))
        except Exception:
            logger.info(click.style("This system is not yet supported.", fg="magenta"))
        sys.exit()
    except Exception:
        logger.info(click.style("An unknown error occurred.  Please contact support@21.co.",
                                fg="magenta"))
        sys.exit()
    else:
        if ctx.invoked_subcommand is None:
            logger.info(ctx.command.get_help(ctx))

    # pass Two1Manager & platform data down in context
    ctx.obj['manager'] = manager
    ctx.obj['installer'] = installer


@sell.command()
@click.argument('services',
                required=False,
                nargs=-1)
@click.option('-a', '--all',
              is_flag=True)
@click.option('-w', '--wait-time',
              type=int, default=10)
@click.option('--no-vm', is_flag=True, default=False)
@click.pass_context
def start(ctx, services, all, wait_time, no_vm):
    """
Start selling a containerized service.

\b
Start selling a single service.
$ 21 sell start <service_name>

\b
Start selling all available services.
$ 21 sell start --all
"""

    # display help command if no args
    if len(services) == 0 and all is False:
        logger.info(ctx.command.get_help(ctx))
        sys.exit()

    # no-vm version coming soon
    if no_vm:
        logger.info(click.style("This mode is not yet supported.", fg="magenta"))
        sys.exit()

    # assign manager and installer from context
    manager = ctx.obj['manager']
    installer = ctx.obj['installer']

    logger.info(click.style("Checking dependencies...", fg=cli_helpers.TITLE_COLOR))
    deps_list = installer.check_dependencies()
    all_deps_installed = cli_helpers.package_check(deps_list, True)

    # install virtualbox, docker, and zerotier deps
    if not all_deps_installed:
        if click.confirm(click.style("Would you like to install the missing packages?",
                                     fg=cli_helpers.PROMPT_COLOR)):
            logger.info(click.style("Installing missing dependencies...", fg=cli_helpers.TITLE_COLOR))
            all_installed = cli_helpers.install_missing_dependencies(deps_list,
                                                                     installer)
            if not all_installed:
                sys.exit()
        else:
            sys.exit()

    # pick up docker group permissions by force logout (via user prompt)
    if cli_helpers.check_needs_logout(installer):
        sys.exit()

    # connect to zerotier virtual network
    if not manager.status_networking():
        if click.confirm(click.style(
                "ZeroTier One virtual network service is not running. Would you like to start "
                "the service?", fg=cli_helpers.PROMPT_COLOR)):
            try:
                manager.start_networking()
                cli_helpers.print_str("ZeroTier One", ["Started"], "TRUE", True)
            except Two1MachineNetworkStartException:
                cli_helpers.print_str("ZeroTier One", ["Not started"], "FALSE", False)
        else:
            sys.exit()

    # join the 21market network
    if manager.get_market_address() == "":
        if click.confirm(click.style(
                "21market network not connected. Would you like to join 21market?", fg=cli_helpers.PROMPT_COLOR)):
            logger.info("You might need to enter your superuser password.")
            manager.connect_market(ctx.obj['client'])
            if manager.get_market_address() == "":
                cli_helpers.print_str("21market", ["Joined"], "TRUE", True)
            else:
                cli_helpers.print_str("21market", ["Unable to join"], "FALSE", False)
        else:
            sys.exit()
    else:
        cli_helpers.print_str("21market", ["Joined"], "TRUE", True)

    if isinstance(manager.machine, Two1MachineVirtual):
        logger.info(click.style("Checking virtual machine status...", fg=cli_helpers.TITLE_COLOR))
        just_started = False
        vm_status = manager.status_machine()
        if vm_status == VmState.NOEXIST:
            if click.confirm(click.style("  21 virtual machine does not exist. "
                                         "Would you like to create it?",
                                         fg=cli_helpers.PROMPT_COLOR)):
                vm_config = cli_helpers.get_vm_options()
                try:
                    cli_helpers.start_long_running("Creating machine (this may take a few minutes)",
                                                   manager.create_machine,
                                                   "21",
                                                   vm_config.disk_size,
                                                   vm_config.vm_memory,
                                                   vm_config.server_port,
                                                   vm_config.network_interface)
                    cli_helpers.write_machine_config(vm_config._asdict())
                    cli_helpers.print_str("21 virtual machine", ["Created"], "TRUE", True)

                except Two1MachineCreateException:
                    cli_helpers.print_str("21 virtual machine", ["Not created"], "FALSE", False)

                vm_status = manager.status_machine()
            else:
                sys.exit()

        if vm_status != VmState.RUNNING:
            if not manager.status_networking():
                if click.confirm(click.style(
                        "ZeroTier One virtual network service is not running. "
                        "Would you like to start the service?", fg=cli_helpers.PROMPT_COLOR)):
                    try:
                        manager.start_networking()
                        cli_helpers.print_str("ZeroTier One", ["Started"], "TRUE", True)
                    except Two1MachineNetworkStartException:
                        cli_helpers.print_str("ZeroTier One", ["Not started"], "FALSE", False)
                else:
                    sys.exit()
            try:
                cli_helpers.start_long_running("Starting machine (this may take a few minutes)",
                                               manager.start_machine)
                just_started = True
            except Two1MachineStartException:
                cli_helpers.print_str("21 virtual machine", ["Not started"], "FALSE", False)
                sys.exit()
            vm_status = manager.status_machine()

        # check if machine running
        if vm_status == VmState.RUNNING:
            if just_started:
                cli_helpers.print_str("21 virtual machine", ["Started"], "TRUE", True)
            else:
                cli_helpers.print_str("21 virtual machine", ["Running"], "TRUE", True)
        else:
            sys.exit()
    else:
        server_port = cli_helpers.get_server_port()
        cli_helpers.write_machine_config({"server_port": server_port})

    # write user credentials info to environment file
    username, pw = cli_helpers.get_user_credentials()
    status_env = manager.write_global_services_env(username, pw)

    # build service images
    try:
        payment_wallet = cli_helpers.start_long_running("Building base services (this may take a few minutes)",
                                                        manager.build_base_services)
    except:
        cli_helpers.print_str("Services", ["Not built"], "FALSE", False)
        sys.exit()
    else:
        cli_helpers.print_str("Services", ["Built"], "TRUE", True)

    if payment_wallet["created"]:
        logger.info(click.style("A wallet has been generated for the payment container,\nplease write down its wallet mnemonic and store it in a safe place:\n"
                                "    {}".format(payment_wallet['mnemonic']), fg="magenta"))
        click.pause()

    if all:
        valid_services = manager.get_all_services_list()
    else:
        valid_services = services

    # build service images
    try:
        wallets_dict = cli_helpers.start_long_running("Building market services (this may take a few minutes)",
                                                      manager.build_market_services,
                                                      valid_services)
    except:
        cli_helpers.print_str("Services", ["Not built"], "FALSE", False)
        sys.exit()
    else:
        cli_helpers.print_str("Services", ["Built"], "TRUE", True)

    for service, wallet_template in wallets_dict.items():
        if wallet_template["created"]:
            logger.info(click.style("A wallet has been generated for the service \"{}\",\nplease write down its wallet mnemonic and store it in a safe place:\n"
                                    "    {}".format(service, wallet_template['mnemonic']), fg="magenta"))
            click.pause()

    # start container services
    start_stats = cli_helpers.start_long_running("Starting services (this may take a few minutes)",
                                                 manager.start_services,
                                                 valid_services)
    formatted_stats = cli_helpers.start_dict_to_list(start_stats)
    cli_helpers.service_status_check(formatted_stats, False)
    published_stats = cli_helpers.prompt_to_publish(formatted_stats, manager)
    for stat in published_stats:
        cli_helpers.print_str(stat[0],
                              stat[2],
                              "TRUE" if stat[1] else "FALSE",
                              stat[1])
    # help tip message
    logger.info(click.style("\nTip: run ", fg=cli_helpers.PROMPT_COLOR) +
                click.style("`21 sell status --detail`", bold=True, fg=cli_helpers.PROMPT_COLOR) +
                click.style(" to see your microservice balances.", fg=cli_helpers.PROMPT_COLOR))


@sell.command()
@click.argument('services',
                required=False,
                nargs=-1)
@click.option('-a', '--all',
              is_flag=True)
@click.option('--stop-vm', is_flag=True,
              default=False)
@click.option('--delete-vm', is_flag=True,
              default=False)
@click.pass_context
def stop(ctx, services, all, stop_vm, delete_vm):
    """
Stop selling a containerized service.

\b
Stop selling a single service.
$ 21 sell stop <service_name>

\b
Stop selling all services.
$ 21 sell stop --all
"""

    if len(services) == 0 and all is False and stop_vm is False and delete_vm is False:
        logger.info(ctx.command.get_help(ctx))
        sys.exit()

    # pass Two1SellSell_Client down in context
    manager = ctx.obj['manager']

    if all:
        valid_services = manager.get_all_services_list()
    else:
        valid_services = services

    if manager.status_machine() == VmState.NOEXIST:
        if isinstance(manager.machine, Two1MachineVirtual):
            cli_helpers.print_str("Virtual machine", ["Does not exist"], "TRUE", True)
            sys.exit()
        else:
            if stop_vm or delete_vm:
                logger.info(click.style("Your services are running natively: "
                                        "run 21 sell stop --all to stop services", fg="magenta"))
                sys.exit()

            services_status = manager.status_services(valid_services, 1)
            running_exists = False
            for service in services_status:
                if (services_status[service]["status"].lower() == "running" or
                        services_status[service]["status"].lower() == "unable to contact"):
                    running_exists = True
                    break
            if running_exists:
                stop_stats = cli_helpers.start_long_running("Stopping services",
                                                            manager.stop_services,
                                                            valid_services)
                formatted_stats = cli_helpers.stop_dict_to_list(stop_stats)
                cli_helpers.service_status_check(formatted_stats)
            else:
                cli_helpers.print_str("Services", ["None found running"], "TRUE", True)

    if manager.status_machine() == VmState.STOPPED:
        if stop_vm:
            cli_helpers.print_str("Virtual machine", ["Stopped"], "TRUE", True)
            sys.exit()
        if delete_vm:
            if not isinstance(manager.machine, Two1MachineVirtual):
                logger.info(click.style("There are no VMs to stop or delete: "
                                        "your services are running natively", fg="magenta"))
                sys.exit()
            try:
                cli_helpers.start_long_running("Deleting virtual machine",
                                               manager.delete_machine)
                cli_helpers.print_str("Virtual machine", ["Deleted"], "TRUE", True)
            except Two1MachineDeleteException:
                cli_helpers.print_str("Virtual machine", ["Failed to delete"], "FALSE", False)

    if manager.status_machine() == VmState.RUNNING:
        services_status = manager.status_services(valid_services, 1)
        running_exists = False
        for service in services_status:
            if (services_status[service]["status"].lower() == "running" or
                    services_status[service]["status"].lower() == "unable to contact"):
                running_exists = True
                break
        if running_exists:
            stop_stats = cli_helpers.start_long_running("Stopping services",
                                                        manager.stop_services,
                                                        valid_services)
            formatted_stats = cli_helpers.stop_dict_to_list(stop_stats)
            cli_helpers.service_status_check(formatted_stats)
        else:
            if not stop_vm and not delete_vm:
                cli_helpers.print_str("Services", ["None found running"], "TRUE", True)

        if stop_vm or delete_vm:
            try:
                cli_helpers.start_long_running("Stopping virtual machine",
                                               manager.stop_machine)
                cli_helpers.print_str("Virtual machine", ["Stopped"], "TRUE", True)
            except Two1MachineStopException:
                cli_helpers.print_str("Virtual machine", ["Failed to stop"], "FALSE", False)
                sys.exit()

            if delete_vm:
                try:
                    cli_helpers.start_long_running("Deleting virtual machine",
                                                   manager.delete_machine)
                    cli_helpers.print_str("Virtual machine", ["Deleted"], "TRUE", True)
                except Two1MachineDeleteException:
                    cli_helpers.print_str("Virtual machine", ["Failed to delete"], "FALSE", False)
                    sys.exit()


@sell.command()
@click.option('-d', '--detail',
              is_flag=True,
              default=False)
@click.pass_context
def status(ctx, detail):
    """
Get status on running services.

\b
Get status on virtual machine and service.
$ 21 sell status
"""

    # pass Two1SellClient down in context
    manager = ctx.obj['manager']

    logger.info(click.style("\n21 SYSTEM STATUS", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style(85*"-", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style("NETWORKING", fg=cli_helpers.TITLE_COLOR))

    if isinstance(manager.machine, Two1MachineVirtual):
        if not cli_helpers.vm_running_check(manager.status_machine() == VmState.RUNNING,
                                            log_not_running=True):
            sys.exit()

    if not cli_helpers.zerotier_service_check(manager.status_networking(),
                                              log_not_running=True):
        sys.exit()

    if not cli_helpers.market_connected_check(manager.machine.host,
                                              log_not_running=True):
        sys.exit()

    logger.info(click.style("SERVER STATUS", fg=cli_helpers.TITLE_COLOR))

    if not cli_helpers.router_running_check(manager.status_router(),
                                            log_not_running=True):
        sys.exit()

    if not cli_helpers.payments_server_running_check(manager.composer.status_payments_server(),
                                                     log_not_running=True):
        sys.exit()

    service_status = manager.status_services(Two1Composer.GRID_SERVICES)
    for service in sorted(service_status):
        cli_helpers.print_str("%s" % service.title(),
                              [service_status[service]["message"]],
                              "TRUE" if service_status[service]["status"] == "Running" else "FALSE",
                              True if service_status[service]["status"] == "Running" else False)

    logger.info(click.style("TRANSACTION TOTALS", fg=cli_helpers.TITLE_COLOR))
    cli_helpers.service_earning_check(list(service_status.keys()), detail)

    if detail:
        logger.info(click.style("BALANCES", fg=cli_helpers.TITLE_COLOR))
        cli_helpers.service_balance_check(list(service_status.keys()))

    logger.info(click.style("EXAMPLE USAGE", fg=cli_helpers.TITLE_COLOR))
    cli_helpers.print_example_usage(list(service_status.keys()),
                                    manager.get_market_address(),
                                    manager.get_server_port())


@sell.command(name="list")
@click.pass_context
def list_command(ctx):
    """
List services available to sell.

\b
Get the list of microservices you can sell for bitcoin.
$ 21 sell list
"""

    # pass Two1SellClient down in context
    manager = ctx.obj['manager']

    logger.info(click.style("Available 21 microservices", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style(85*"-", fg=cli_helpers.MENU_COLOR))
    available_services = manager.get_all_services_list()
    if len(available_services) != 0:
        for service in available_services:
            cli_helpers.print_str(service, ["Available"], "TRUE", True)
        # help tip message
        logger.info(click.style("\nTip: run ", fg=cli_helpers.PROMPT_COLOR) +
                    click.style("`21 sell start <services>`", bold=True, fg=cli_helpers.PROMPT_COLOR) +
                    click.style(" to start selling a microservice.", fg=cli_helpers.PROMPT_COLOR))
    else:
        logger.info(click.style("There are no services available at this time.",
                                fg="magenta"))


@sell.command()
@click.argument('services',
                required=False,
                nargs=-1)
@click.option('-a', '--all',
              is_flag=True)
@click.option('--channels',
              is_flag=True)
@click.pass_context
def sweep(ctx, services, all, channels):
    """
Sweep service wallets to primary wallet.

\b
Sweep all service wallets to primary wallet.
$ 21 sell sweep --all

\b
Sweep the wallets of services to primary wallet.
$ 21 sell sweep <services>...
"""
    services_present = len(services) > 0
    all_present = all is True
    channels_present = channels is True

    if services_present + all_present + channels_present != 1:
        logger.info(ctx.command.get_help(ctx))
        sys.exit()

    manager = ctx.obj['manager']

    provider = TwentyOneProvider()
    master = Two1Wallet(manager.composer.PRIMARY_WALLET_FILE, provider)

    if not channels_present:
        try:
            with open(manager.composer.SERVICES_WALLET_FILE, "r") as f:
                services_info = json.load(f)
        except:
            logger.info(click.style("The services wallet information file seems to be corrupted, exiting..."), fg="magenta")
            sys.exit()

        requested_services_set = frozenset(services)
        available_services_set = frozenset(services_info.keys())

        if all:
            start_string = "Sweeping all service balances..."
            clients = {service_name: Two1Wallet.import_from_mnemonic(provider, service_details['mnemonic'])
                       for service_name, service_details in services_info.items()}
        elif requested_services_set.issubset(available_services_set):
            start_string = "Sweeping balances for " + ", ".join(services) + "..."
            clients = {service_name: Two1Wallet.import_from_mnemonic(provider, services_info[service_name]['mnemonic'])
                       for service_name in services}
        else:
            unavailable_requested_services = requested_services_set.difference(available_services_set)
            if len(unavailable_requested_services) > 1:
                logger.info(click.style("Services {} aren't available to be sweeped".format(", ".join(unavailable_requested_services)), fg="magenta"))
            else:
                logger.info(click.style("Service {} isn't available to be sweeped".format(", ".join(unavailable_requested_services)), fg="magenta"))
            sys.exit()
        logger.info(click.style(start_string, fg=cli_helpers.TITLE_COLOR))
    else:
        logger.info(click.style("Sweeping payment server balances...", fg=cli_helpers.TITLE_COLOR))
        try:
            with open(manager.composer.PAYMENTS_WALLET_FILE, "r") as f:
                payments_info = json.load(f)
        except:
            logger.info(click.style("The payment server wallet information file seems to be corrupted, exiting..."), fg="magenta")
            sys.exit()
        clients = {"payment channels": Two1Wallet.import_from_mnemonic(provider, payments_info['mnemonic'])}

    logger.info(click.style(start_string, fg=cli_helpers.TITLE_COLOR))

    utxo_sums = {}
    for service_name, wallet in clients.items():
        utxos_by_addr = wallet.get_utxos(include_unconfirmed=True,
                                         accounts=wallet._accounts)
        utxo_sums[service_name] = wallet._sum_utxos(utxos_by_addr)

    fee_dict = {}
    fee_amounts = txn_fees.get_fees()
    for service_name, utxo_sum in utxo_sums.items():
        total_value, num_utxos = utxo_sum
        fee_dict[service_name] = fee_calc_small(num_utxos, total_value, fee_amounts)
    fees = sum(fee_dict.values())

    if click.confirm(click.style("This will incur a fee of approximately %d satoshis in total. "
                                 "Would you like to continue?" % fees, fg=cli_helpers.PROMPT_COLOR)):
        for service_name, wallet in clients.items():
            try:
                wallet.sweep(master.current_address, fee_calculator=fee_calc_small)
            except WalletBalanceError:
                cli_helpers.print_str(service_name, ["Wallet balance (%d satoshis) is less than the dust limit. Not Sweeping." % utxo_sums[service_name][0]], "FALSE", False)
            except DustLimitError:
                cli_helpers.print_str(service_name, ["Wallet balance (%d satoshis) would be below the dust limit when fees are deducted. Not Sweeping." % utxo_sums[service_name][0]], "FALSE", False)
            else:
                total_value = utxo_sums[service_name][0]
                fees_incurred = fee_dict[service_name]
                cli_helpers.print_str(service_name, ["Sweeped %d satoshis, excluding %d satoshis of fees" % (total_value - fees_incurred, fees_incurred)], "TRUE", True)
    else:
        sys.exit()


def fee_calc_small(num_utxos, total_value, fee_amounts):
    maybe_fee = _fee_calc(num_utxos, total_value, fee_amounts)
    return int(min([total_value / 2, maybe_fee]))
