""" Sell web services for micropayments.
"""
# standard python imports
import sys
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
def sell(ctx, **options):
    """
Start local server to sell APIs for bitcoin.

\b
Usage
_____
List services available to sell.
$ 21 sell list

\b
Adding a new service
$ 21 sell add <service_name> <docker_image_name>

\b
Removing a service
$ 21 sell remove <service_name>

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

    # pass Two1Manager & platform data in click context
    ctx.obj['manager'] = manager
    ctx.obj['installer'] = installer


@sell.command()
@click.argument('service_name')
@click.argument('docker_image_name')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def add(ctx, service_name, docker_image_name):
    """
Add a new service to 21 sell

\b
Adding a new service
$ 21 sell add <service_name> <docker_image_name>
"""
    manager = ctx.obj['manager']
    logger.info(click.style("Adding services.", fg=cli_helpers.TITLE_COLOR))

    def service_successfully_added_hook(tag):
        cli_helpers.print_str(tag, ["Added"], "TRUE", True)

    def service_already_exists_hook(tag):
        cli_helpers.print_str(tag, ["Already exists"], "FALSE", False)

    def service_failed_to_add_hook(tag):
        cli_helpers.print_str(tag, ["Failed to add"], "FALSE", False)

    manager.add_service(service_name, docker_image_name, service_successfully_added_hook, service_already_exists_hook,
                        service_failed_to_add_hook)


@sell.command()
@click.argument('service_names', nargs=-1)
@click.option('-a', '--all', 'is_all', is_flag=True)
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def remove(ctx, service_names, is_all):
    """
Remove a service from 21 sell

\b
Removing a service
$ 21 sell remove <service_name>

\b
Removing all services from 21 sell
$ 21 sell remove --all
"""
    if not service_names and is_all is False:
        raise click.UsageError('No service selected.', ctx=ctx)

    manager = ctx.obj['manager']
    logger.info(click.style("Removing services.", fg=cli_helpers.TITLE_COLOR))

    def service_successfully_removed_hook(tag):
        cli_helpers.print_str(tag, ["Removed"], "TRUE", True)

    def service_does_not_exists_hook(tag):
        cli_helpers.print_str(tag, ["Doesn't exist"], "FALSE", False)

    def service_failed_to_remove_hook(tag):
        cli_helpers.print_str(tag, ["Failed to remove"], "FALSE", False)

    if is_all:
        services_to_remove = manager.available_user_services()
    else:
        services_to_remove = service_names

    for service_name in services_to_remove:
        manager.remove_service(service_name, service_successfully_removed_hook, service_does_not_exists_hook,
                               service_failed_to_remove_hook)


@sell.command()
@click.argument('services',
                required=False,
                nargs=-1)
@click.option('-a', '--all',
              is_flag=True)
@click.option('-w', '--wait-time',
              type=int, default=10)
@click.option('--no-vm', is_flag=True, default=False)
@click.option('--no-zt-dep', is_flag=True, default=False)
@click.option('--publishing-ip', type=str)
@click.option('-y', '--yes', '--assume-yes', is_flag=True, default=False)
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def start(ctx, services, all, wait_time, no_vm, no_zt_dep, publishing_ip, assume_yes):
    """
Start selling a containerized service.

\b
Start selling a single service.
$ 21 sell start <service_name>

\b
Start selling all available services.
$ 21 sell start --all
"""
    # display help command if no service is selected
    if len(services) == 0 and all is False:
        raise click.UsageError('No service selected.', ctx=ctx)

    # no-vm version coming soon
    if no_vm:
        raise click.UsageError('This mode is not yet supported.', ctx=ctx)

    # assign manager and installer from context
    manager = ctx.obj['manager']
    installer = ctx.obj['installer']

    if no_zt_dep:
        if publishing_ip is None:
            logger.info(click.style("--no-zt-dep must be used in "
                                    "conjunction with --publishing-ip <IP_TO_PUBLISH>.",
                                    fg=cli_helpers.PROMPT_COLOR))
            sys.exit()

    if cli_helpers.running_old_sell(manager, installer):
        if click.confirm(click.style("It appears that you are running an old version of 21 sell.\n"
                                     "In order to continue using 21 sell, you must update the 21 "
                                     "VM.\nWould you like to delete the existing VM and create a "
                                     "new one?",
                                     fg=cli_helpers.WARNING_COLOR)):
            upgrade_21_sell(ctx, services, all, wait_time, no_vm)
            sys.exit()
        else:
            logger.info(click.style("Please note that your services may be unreachable "
                                    "without this update.",
                                    fg=cli_helpers.WARNING_COLOR))
            sys.exit()

    logger.info(click.style("Checking dependencies.", fg=cli_helpers.TITLE_COLOR))
    deps_list = installer.check_dependencies()
    if no_zt_dep:
        deps_list = [(name, installed) for name, installed in deps_list if name != 'Docker']
    all_deps_installed = cli_helpers.package_check(deps_list, True)

    # install virtualbox, docker, and zerotier deps
    if not all_deps_installed:
        if assume_yes or click.confirm(click.style("Would you like to install the missing "
                                                   "packages?",
                                                   fg=cli_helpers.PROMPT_COLOR)):
            logger.info(click.style("Installing missing dependencies.", fg=cli_helpers.TITLE_COLOR))
            all_installed = cli_helpers.install_missing_dependencies(deps_list,
                                                                     installer)
            if not all_installed:
                sys.exit()
        else:
            sys.exit()

    # pick up docker group permissions by forced logout
    if cli_helpers.check_needs_logout(installer):
        sys.exit()

    if isinstance(manager.machine, Two1MachineVirtual):
        logger.info(click.style("Checking virtual machine status.", fg=cli_helpers.TITLE_COLOR))
        just_started = False
        vm_status = manager.status_machine()
        if vm_status == VmState.NOEXIST:
            if assume_yes or click.confirm(click.style("  21 virtual machine does not exist. "
                                                       "Would you like to create it?",
                                                       fg=cli_helpers.PROMPT_COLOR)):
                vm_config = cli_helpers.get_vm_options()
                try:
                    cli_helpers.start_long_running("Creating machine (this may take a few minutes)",
                                                   manager.create_machine,
                                                   "21",
                                                   vm_config.disk_size,
                                                   vm_config.vm_memory,
                                                   vm_config.server_port)
                    manager.write_machine_config(vm_config._asdict())
                    cli_helpers.print_str("21 virtual machine", ["Created"], "TRUE", True)

                except Two1MachineCreateException:
                    cli_helpers.print_str("21 virtual machine", ["Not created"], "FALSE", False)
                vm_status = manager.status_machine()
            else:
                sys.exit()

        if vm_status != VmState.RUNNING:
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
        manager.write_machine_config({"server_port": server_port})

    # connect to zerotier virtual network
    if not manager.status_networking():
        if no_zt_dep:
            pass
        else:
            try:
                if not isinstance(manager.machine, Two1MachineVirtual):
                    if assume_yes or click.confirm(click.style(
                            "ZeroTier One virtual network service is not running. Would you like "
                            "to start the service?", fg=cli_helpers.PROMPT_COLOR)):
                        manager.start_networking()
                    else:
                        sys.exit()
                else:
                    cli_helpers.start_long_running("Starting ZeroTier One",
                                                   manager.start_networking)

                cli_helpers.print_str("ZeroTier One", ["Started"], "TRUE", True)
            except Two1MachineNetworkStartException:
                cli_helpers.print_str("ZeroTier One", ["Not started"], "FALSE", False)
                sys.exit()

    # join the 21mkt network
    if manager.get_market_address() == "":
        if no_zt_dep:
            pass
        else:
            if not isinstance(manager.machine, Two1MachineVirtual):
                if assume_yes or click.confirm(click.style(
                        "21mkt network not connected. Would you like to join 21mkt?",
                        fg=cli_helpers.PROMPT_COLOR)):
                    logger.info("You might need to enter your superuser password.")
                    manager.connect_market(ctx.obj["client"])
                else:
                    sys.exit()
            else:
                cli_helpers.start_long_running("Connecting to 21mkt",
                                               manager.connect_market,
                                               ctx.obj["client"])

            if manager.get_market_address() != "":
                cli_helpers.print_str("21mkt", ["Joined"], "TRUE", True)
            else:
                cli_helpers.print_str("21mkt", ["Unable to join"], "FALSE", False)
                sys.exit()
    else:
        cli_helpers.print_str("21mkt", ["Joined"], "TRUE", True)

    # ensure docker service is running
    if manager.status_docker() is False:
        if assume_yes or click.confirm(click.style(
                "Docker service is not running. Would you like to start "
                "the service?", fg=cli_helpers.PROMPT_COLOR)):
            try:
                manager.start_docker()
                cli_helpers.print_str("Docker", ["Started"], "TRUE", True)
            except Two1MachineNetworkStartException:
                cli_helpers.print_str("Docker", ["Not started"], "FALSE", False)
        else:
            sys.exit()

    # generate machine wallet & initialize micropayments server
    logger.info(click.style("Initializing micropayments server.", fg=cli_helpers.TITLE_COLOR))
    username, password = cli_helpers.get_user_credentials()  # get user creds
    try:
        server_port = manager.get_server_port()
    except Exception:
        logger.info(click.style("Error: cannot read server port from file.  Please try again or contact "
                                "support@21.co.", fg="magenta"))
    status_init, new_wallet_mnemonic = manager.initialize_server(username, password, server_port)
    if status_init == 0:
        # if new mnemonic has been generated
        if new_wallet_mnemonic is not None:
            logger.info(click.style("\nA unique machine wallet has been generated for your micropayments "
                                    "server.\nPlease write down the following mnemonic and store it in "
                                    "a safe place:\n", fg=cli_helpers.PROMPT_COLOR))
            logger.info(click.style("    {}\n".format(new_wallet_mnemonic), fg="magenta"))
            click.pause()
    else:
        logger.info(click.style("Error initializing micropayments server. Please try again or "
                                "contact support@21.co.", fg="magenta"))
        sys.exit()

    # check that services to start are available
    available_services = manager.get_available_services()

    if len(available_services) == 0:
        raise click.ClickException(click.style("Unable to fetch available services. Please try again or contact"
                                               " support@21.co.", fg="magenta"))

    if not all:
        logger.info(click.style("Checking availability of selected services.", fg=cli_helpers.TITLE_COLOR))

        available_selected_services = set(services) & available_services
        unavailable_selected_services = set(services) - available_services

        for available_selected_service in available_selected_services:
            cli_helpers.print_str(available_selected_service, ["Available"], "TRUE", True)

        for unavailable_selected_service in unavailable_selected_services:
            cli_helpers.print_str(unavailable_selected_service, ["Unavailable"], "False", False)

        if available_selected_services == set(services):
            service_to_pull = set(services)
        elif len(available_selected_services) > 0:
            if click.confirm(click.style("Not all selected services are available, would you like to start the"
                                         " available services anyways?", fg=cli_helpers.PROMPT_COLOR)):
                service_to_pull = available_selected_services
            else:
                raise click.Abort()
        else:
            raise click.ClickException(click.style("None of the services you've selected is available.", fg="magenta") +
                                       click.style(" Run", fg="magenta") +
                                       click.style(" `21 sell list`", bold=True, fg=cli_helpers.PROMPT_COLOR) +
                                       click.style(" to see available microservices.", fg="magenta"))
    else:
        service_to_pull = available_services

    # Pulling images for services in `service_to_pull`
    logger.info(click.style("Pulling images for selected services.", fg=cli_helpers.TITLE_COLOR))

    service_to_start = set()
    for service_name in service_to_pull:

        image_for_service = manager.get_image(service_name)

        def image_sucessfully_pulled_hook(image):
            service_to_start.add(service_name)
            cli_helpers.print_str('%s -> %s' % (service_name, image), ["Pulled"], "TRUE", True)

        def image_failed_to_pull_hook(image):
            cli_helpers.print_str('%s -> %s' % (service_name, image), ["Failed to pull"], "False", False)

        def image_is_local_hook(image):
            service_to_start.add(service_name)
            cli_helpers.print_str('%s -> %s' % (service_name, image), ["Exists locally"], "TRUE", True)

        def image_is_malformed_hook(image):
            cli_helpers.print_str('%s -> %s' % (service_name, image), ["Malformed image name"], "False", False)

        manager.pull_image(image_for_service,
                           image_sucessfully_pulled_hook, image_failed_to_pull_hook, image_is_local_hook,
                           image_is_malformed_hook)

    if service_to_pull > service_to_start:
        if len(service_to_start) > 0:
            if not click.confirm(click.style("Not all Docker Hub images were successfully pulled for the services"
                                             " you've selected, would you like to start the services that had their"
                                             " images successfully pulled anyways?", fg=cli_helpers.PROMPT_COLOR)):
                raise click.Abort()
        else:
            raise click.ClickException(click.style("None of the Docker Hub images were successfully pulled for the"
                                                   " services you've selected.", fg="magenta"))

    # Start services for services in `service_to_start`
    logger.info(click.style("Starting services.", fg=cli_helpers.TITLE_COLOR))
    try:
        manager.start_services(service_to_start,
                               cli_helpers.failed_to_start_hook,
                               cli_helpers.started_hook,
                               cli_helpers.failed_to_restart_hook,
                               cli_helpers.restarted_hook,
                               cli_helpers.failed_to_up_hook,
                               cli_helpers.up_hook)
    except:
        raise click.ClickException(click.style("Unable to start services.", fg="magenta"))

    try:
        started_services = manager.get_running_services()
    except:
        raise click.ClickException(click.style("Unable to fetch running services.", fg="magenta"))

    # prompt to publish services
    published_stats = cli_helpers.prompt_to_publish(started_services, manager, publishing_ip, assume_yes=assume_yes)
    for stat in published_stats:
        cli_helpers.print_str(stat[0],
                              stat[2],
                              "TRUE" if stat[1] else "FALSE",
                              stat[1])

    # help tip message
    logger.info(click.style("\nTip: (1) run ", fg=cli_helpers.PROMPT_COLOR) +
                click.style("`21 publish list`", bold=True, fg=cli_helpers.PROMPT_COLOR) +
                click.style(" to see your published services.\n", fg=cli_helpers.PROMPT_COLOR) +
                click.style("     (2) run ", fg=cli_helpers.PROMPT_COLOR) +
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
@decorators.catch_all
@decorators.capture_usage
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

    try:
        dollars_per_sat = cli_helpers.get_rest_client().quote_bitcoin_price(1).json()["price"]
    except Exception:
        logger.info("Unable to fetch latest bitcoin price quote.", fg="magenta")
        raise

    def service_found_stopped_and_removed_hook(service_name):
        cli_helpers.print_str(service_name, ["Stopped and removed"], "TRUE", True)
        cli_helpers.service_status(service_name, dollars_per_sat)

    def service_failed_to_stop_hook(service_name):
        cli_helpers.print_str(service_name, ["Failed to stop"], "False", False)

    def service_failed_to_be_removed_hook(service_name):
        cli_helpers.print_str(service_name, ["Failed to be removed"], "False", False)

    def service_not_found_hook(service_name):
        cli_helpers.print_str(service_name, ["Not found"], "False", False)

    if manager.status_machine() == VmState.NOEXIST:  # docker isn't running under virtual machine
        if isinstance(manager.machine, Two1MachineVirtual):
            cli_helpers.print_str("Virtual machine", ["Does not exist"], "TRUE", True)
            sys.exit()
        else:
            if stop_vm or delete_vm:
                logger.info(click.style("Your services are running natively: "
                                        "run `21 sell stop --all` to stop services", fg="magenta"))
                sys.exit()
        if all:
            try:
                valid_services = manager.get_running_services()
            except Exception:
                logger.info("Unable to get running services.", fg="magenta")
                sys.exit()
        else:
            valid_services = services
        if len(valid_services) > 0:
            logger.info(click.style("Stopping services.", fg=cli_helpers.TITLE_COLOR))
            # stop bitcoin-payable microservices
            try:
                manager.stop_services(valid_services,
                                      service_found_stopped_and_removed_hook,
                                      service_failed_to_stop_hook,
                                      service_failed_to_be_removed_hook,
                                      service_not_found_hook)
            except Exception:
                logger.info("Unable to stop services.", fg="magenta")
        else:
            logger.info(click.style("All services are stopped.", fg="magenta"))

    if manager.status_machine() == VmState.STOPPED:  # docker-machine stopped
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
        else:
            if not stop_vm:
                logger.info(click.style("All services already stopped.", fg="magenta"))
            cli_helpers.print_str("Virtual machine", ["Stopped"], "TRUE", True)
            sys.exit()

    if manager.status_machine() == VmState.RUNNING:  # docker is running under virtual machine and is up
        if all:
            try:
                valid_services = manager.get_running_services()
            except Exception:
                logger.info("Unable to get running services.", fg="magenta")
                sys.exit()
        else:
            valid_services = services
        if len(valid_services) > 0:
            logger.info(click.style("Stopping services.", fg=cli_helpers.TITLE_COLOR))
            # stop bitcoin-payable microservices
            try:
                manager.stop_services(valid_services,
                                      service_found_stopped_and_removed_hook,
                                      service_failed_to_stop_hook,
                                      service_failed_to_be_removed_hook,
                                      service_not_found_hook)
            except Exception:
                logger.info("Unable to stop services.", fg="magenta")
        else:
            logger.info(click.style("All services are stopped.", fg="magenta"))

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
@decorators.catch_all
@decorators.capture_usage
def status(ctx, detail):
    """
Get status on running services.

\b
Get status on virtual machine and service.
$ 21 sell status
"""

    # read Two1Manager from click context
    manager = ctx.obj['manager']

    logger.info(click.style(85*"-", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style("21 SYSTEM STATUS", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style(85*"-", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style("NETWORKING", fg=cli_helpers.TITLE_COLOR))

    def running_hook(service_name):
        cli_helpers.print_str(service_name.capitalize(), ["Running"], "TRUE", True)

    def unknown_state_hook(service_name):
        cli_helpers.print_str(service_name.capitalize(), ["Unknown state"], "FALSE", False)

    if isinstance(manager.machine, Two1MachineVirtual):
        if not cli_helpers.vm_running_check(manager.status_machine() == VmState.RUNNING,
                                            log_not_running=True):
            sys.exit()

    cli_helpers.zerotier_service_check(manager.status_networking(), log_not_running=True)
    cli_helpers.market_connected_check(manager.machine.host, log_not_running=True)

    logger.info(click.style("SERVICES", fg=cli_helpers.TITLE_COLOR))
    try:
        manager.status_router(running_hook, unknown_state_hook)
    except:
        logger.info("Unable to get router status.", fg="magenta")
        sys.exit()
    try:
        manager.status_payments_server(running_hook, unknown_state_hook)
    except:
        logger.info("Unable to get payments server status.", fg="magenta")
        sys.exit()

    # fetch available services
    try:
        service_statuses = manager.status_services(manager.get_available_services())

        running_services = service_statuses['running']
        exited_services = service_statuses['exited']

        for running_service in running_services:
            cli_helpers.print_str(running_service.capitalize(), ["Running"], "TRUE", True)
        for exited_service in exited_services:
            cli_helpers.print_str(exited_service.captitalize(), ["Exited"], "FALSE", False)
    except:
        logger.info("Unable to get service status.", fg="magenta")
        sys.exit()

    if detail:
        logger.info(click.style("BALANCES", fg=cli_helpers.TITLE_COLOR))
        cli_helpers.service_balance_check()

    if len(running_services | exited_services) > 0:
        logger.info(click.style("TRANSACTION TOTALS", fg=cli_helpers.TITLE_COLOR))
        cli_helpers.service_earning_check(running_services | exited_services, detail)

    example_usages = cli_helpers.get_example_usage(running_services,
                                                   'http://' + manager.get_market_address(), manager.get_server_port())
    if len(example_usages) > 0:
        logger.info(click.style("EXAMPLE USAGE", fg=cli_helpers.TITLE_COLOR))
        for service, usage_string in example_usages.items():
            cli_helpers.print_str_no_label(service, [usage_string])

    # help tip message
    logger.info(click.style("\nTip: run ", fg=cli_helpers.PROMPT_COLOR) +
                click.style("`21 sell list`", bold=True, fg=cli_helpers.PROMPT_COLOR) +
                click.style(" to see available microservices you can sell.",
                            fg=cli_helpers.PROMPT_COLOR))


@sell.command(name="list")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def list_command(ctx):
    """
List services available to sell.

\b
Get the list of microservices you can sell for bitcoin.
$ 21 sell list
"""

    # read Two1Manager from click context
    manager = ctx.obj['manager']

    logger.info(click.style(85*"-", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style("AVAILABLE MICROSERVICES", fg=cli_helpers.MENU_COLOR))
    logger.info(click.style(85*"-", fg=cli_helpers.MENU_COLOR))

    available_21_services = manager.available_21_services()
    available_user_services = manager.available_user_services()

    # list of tips that gets appended to as we learn about what's available
    tips = []

    # if there are ANY services available
    if len(available_21_services) > 0 or len(available_user_services) > 0:
        if len(available_21_services) > 0:
            # list available 21 services
            logger.info(click.style("Official 21 Microservices", fg=cli_helpers.TITLE_COLOR))
            for service in available_21_services:
                cli_helpers.print_str(service, ["Available"], "TRUE", True)
        else:
            logger.info(click.style("There are no official services available at this time.", fg="magenta"))

        if len(available_user_services) > 0:
            # list available user services
            logger.info(click.style("User Microservices", fg=cli_helpers.TITLE_COLOR))
            for service in available_user_services:
                cli_helpers.print_str(service, ["Available"], "TRUE", True)
        else:
            tips.append(click.style("run ", fg=cli_helpers.PROMPT_COLOR) +
                        click.style("`21 sell add <service_name> <docker_image_name>`",
                                    bold=True, fg=cli_helpers.PROMPT_COLOR) +
                        click.style(" to make your own services available to sell.", fg=cli_helpers.PROMPT_COLOR))
        tips.append(click.style("run ", fg=cli_helpers.PROMPT_COLOR) +
                    click.style("`21 sell start <services>`", bold=True, fg=cli_helpers.PROMPT_COLOR) +
                    click.style(" to start selling an available microservice.", fg=cli_helpers.PROMPT_COLOR))
    else:
        logger.info(click.style("There are no services available at this time.", fg="magenta"))

    # tip formatting
    if len(tips) > 0:
        if len(tips) == 1:
            logger.info(click.style("\nTip: ", fg=cli_helpers.PROMPT_COLOR) + tips[0])
        else:
            for idx, tip in enumerate(tips):
                if idx == 0:
                    logger.info(click.style("\nTips: (%s) " % (idx + 1), fg=cli_helpers.PROMPT_COLOR) + tip)
                else:
                    logger.info(click.style("      (%s) " % (idx + 1), fg=cli_helpers.PROMPT_COLOR) + tip)


@sell.command()
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def sweep(ctx):
    """
Sweep your machine wallet to your primary wallet.

\b
Sweep your machine wallet to your primary wallet.
$ 21 sell sweep
"""

    manager = ctx.obj['manager']

    logger.info(click.style("Sweeping all service balances.", fg=cli_helpers.TITLE_COLOR))

    provider = TwentyOneProvider()
    try:
        wallet = Two1Wallet.import_from_mnemonic(provider, manager.get_services_mnemonic())
    except Exception:
        logger.info(click.style("Error: unable to import wallet mnemonic.  Please check to make "
                                "sure the mnemonic exists in %s "
                                "or contact support@21.co." % Two1Composer.COMPOSE_FILE,
                                fg="magenta"))

    utxos = wallet.get_utxos(include_unconfirmed=True, accounts=wallet._accounts)
    utxo_sum = wallet._sum_utxos(utxos)

    fee_amounts = txn_fees.get_fees()
    total_value, num_utxos = utxo_sum

    def fee_calc_small(num_utxos, total_value, fee_amounts):
        maybe_fee = _fee_calc(num_utxos, total_value, fee_amounts)
        return int(min([total_value / 2, maybe_fee]))

    fee = fee_calc_small(num_utxos, total_value, fee_amounts)

    if click.confirm(click.style("Sweeping %s satoshis to your primary wallet. This will incur a "
                                 "fee of approximately %d satoshis.\n"
                                 "Would you like to continue?" % (total_value, fee),
                                 fg=cli_helpers.PROMPT_COLOR)):
        master = Two1Wallet(manager.composer.wallet_file, provider)
        try:
            wallet.sweep(master.current_address, fee_calculator=fee_calc_small)
        except WalletBalanceError:
            cli_helpers.print_str("Sweep", ["Wallet balance (%d satoshis) is less than the dust "
                                            "limit. Not Sweeping." % total_value], "FAILED", False)
        except DustLimitError:
            cli_helpers.print_str("Sweep", ["Wallet balance (%d satoshis) would be below the "
                                            "dust limit when fees are deducted. "
                                            "Aborting sweep." % total_value], "FAILED", False)
        else:
            cli_helpers.print_str("Sweep", ["Swept %d satoshis, excluding %d satoshis of "
                                            "fees" % (total_value - fee, fee)], "SUCCESS", True)
    else:
        sys.exit()


def upgrade_21_sell(ctx, services, all, wait_time, no_vm):
    manager = ctx.obj['manager']

    def resetting_system():
        manager.force_stop_services()
        manager.delete_machine()

    cli_helpers.start_long_running("Resetting system",
                                   resetting_system)

    logger.info(click.style("Your 21 VM has been deleted. Please run ",
                            fg=cli_helpers.TITLE_COLOR) +
                click.style("21 sell start --all ", fg=cli_helpers.PROMPT_COLOR) +
                click.style("to upgrade your 21 VM and start your "
                            "bitcoin-payable microservices.", fg=cli_helpers.TITLE_COLOR))
    return
