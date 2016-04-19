""" Two1 command to update to the latest version of two1 and it's dependencies """
# standard python imports
import sys
import re
import logging
import subprocess
from datetime import datetime
from datetime import date
from urllib.parse import urljoin
# distutils.version is changed when running in a venv
# pylint: disable=no-name-in-module,import-error
from distutils.version import LooseVersion

# 3rd party requests
import requests
import click

# two1 imports
import two1
from two1.commands.util import uxstring
from two1.commands.util import decorators
from two1.commands.util import exceptions
from two1.commands.util import bitcoin_computer


LAST_CHECKED_FORMAT = "%Y-%m-%d"

# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.argument('version', nargs=1, required=False, default='')
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def update(ctx, version):
    """Update the 21 Command Line Interface.

\b
Usage
-----
Invoke this with no arguments to update the CLI.
$ 21 update
"""
    _update(ctx.obj['config'], version, True)


def _update(config, version, force_update_check=False):
    """ Handles updating the CLI software including any dependencies.

        Args:
            config (Config): Config context object
            version (string): The requested version of 21 to install (defaults to 'latest')
            force_update_check (bool): Forces an update check with the pypi service

        Returns:
            dict: A dict with two keys are returned.
                  update_available (bool): Whether an update is available.
                  update_successful (bool): Whether the update was successfully
                  downloaded and installed.
    """
    logger.info(uxstring.UxString.update_check)

    # Has update been already performed today?
    if not force_update_check and checked_for_an_update_today(config):
        return

    # current two1 version installed
    installed_version = two1.TWO1_VERSION

    # This should never be the case
    if not installed_version:
        raise exceptions.Two1Error(uxstring.UxString.Error.version_not_detected)

    # Set the update check date to today and saves to config file
    config.set('last_update_check', date.today().strftime(LAST_CHECKED_FORMAT), should_save=True)

    # go and get the latest version from pypi
    latest_version = lookup_pypi_version(version)

    # Check if available version is more recent than the installed version.
    if version or LooseVersion(latest_version) > LooseVersion(installed_version):
        # An updated version of the package is available.
        # The update is performed either using pip or apt-get depending
        # on how two1 was installed in the first place.
        logger.info(uxstring.UxString.update_package.format(latest_version))

        # pip install the latest package
        perform_pip_based_update(latest_version)

        # On a BC also see if there are any apt packages available
        if bitcoin_computer.has_mining_chip():
            perform_apt_based_update(latest_version)
    else:
        # Alert the user if there is no newer version available
        logger.info(uxstring.UxString.update_not_needed)


def stop_walletd():
    """ Stops the walletd process if it is running. """
    from two1.wallet import daemonizer
    from two1.wallet.exceptions import DaemonizerError
    failed = False
    try:
        d = daemonizer.get_daemonizer()
        if d.started():
            if not d.stop():
                failed = True
    except OSError:
        pass
    except DaemonizerError:
        failed = True

    return not failed


def lookup_pypi_version(version=None):
    """ Get the latest version of the software from the PyPi service

    Args:
        version (str): The requested version number or None to get latest version

    Returns:
        version (str): A version string with period delimited major, minor, and patch numbers.

    Raises:
        Two1Error: if pypi server cannot be reached, the data returned from the server is
            incorrect, or the version specified is not available.
    """
    try:
        url = urljoin(two1.TWO1_PYPI_HOST, "api/package/{}/".format(two1.TWO1_PACKAGE_NAME))
        response = requests.get(url)
    except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
        raise exceptions.Two1Error(uxstring.UxString.Error.update_server_connection)

    try:
        data = response.json()
    except ValueError:
        raise exceptions.Two1Error(uxstring.UxString.Error.version_not_found)

    try:
        packages = data["packages"]

        # gets all stable versions from list of packages
        versions = [package['version'] for package in packages
                    if re.search(r'\d+\.\d+\.\d+', package['version'])]

        if not versions:
            raise exceptions.Two1Error(uxstring.UxString.Error.version_not_found)

        # gets the max version from all available versions
        latest_version = max(versions, key=LooseVersion)

        # make sure version given is valid
        if version:
            if version in versions:
                return version
            else:
                raise exceptions.Two1Error(
                        uxstring.UxString.Error.version_does_not_exist.format(version,
                                                                              latest_version))
        else:
            return latest_version

    except (AttributeError, KeyError, TypeError):
        raise exceptions.Two1Error(uxstring.UxString.Error.version_not_found)


def checked_for_an_update_today(config):
    """ Checks if an update check was performed today

    Args:
        config (Config): Config context

    Returns:
        bool: True if an update check has already been performed today,
              False otherwise
    """
    try:
        last_update_check = config.last_update_check
        last_update_check_date = datetime.strptime(last_update_check, LAST_CHECKED_FORMAT).date()
        today_date = date.today()
        # Check if last_update_check was performed before today
        if today_date > last_update_check_date:
            ret = False
        else:
            ret = True

    except AttributeError:
        # missing attribute could be due to several reasons
        # but we must check for an update in this case
        ret = False

    return ret


def perform_pip_based_update(version):
    """ Performs a pip based update installing two1 and all dependencies

    Raises:
        Two1Error: if the update subprocess call is not successfull
    """
    install_command = ["pip3",
                       "install",
                       "-i",
                       "{}/pypi".format(two1.TWO1_PYPI_HOST),
                       "-U",
                       "-I",
                       "{}=={}".format(two1.TWO1_PACKAGE_NAME, version)]

    if "https" not in two1.TWO1_PYPI_HOST:
        install_command += ["--trusted-host", two1.TWO1_PYPI_HOST.replace("http://", "")]

    stop_walletd()

    try:
        # Inside a virtualenv, sys.prefix points to the virtualenv directory,
        # and sys.real_prefix points to the "real" prefix of the system Python
        # (often /usr or /usr/local or some such).
        if hasattr(sys, "real_prefix"):
            subprocess.check_call(install_command)
        else:
            logger.info(uxstring.UxString.update_superuser)
            # If not in a virtual environment, run the install command
            # with sudo permissions.
            subprocess.check_call(["sudo"] + install_command)
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        raise exceptions.Two1Error(uxstring.UxString.Error.update_failed)


def perform_apt_based_update(version):
    """ Performs an apt-get based update

    Raises:
        Two1Error: if the update subprocess call is not successfull
    """
    stop_walletd()

    update_command = ["sudo",
                      "apt-get",
                      "update"]
    upgrade_command = ["sudo",
                       "apt-get",
                       "-y",
                       "--force-yes",
                       "install",
                       "zerotier-one",
                       "bitcoind",
                       "minerd"]

    try:
        # remove two1 if its installed via apt-get
        has_apt_two1 = has_apt_two1_installed()
        if has_apt_two1:
            remove_apt_two1()

        # install BC dependencies for two1
        subprocess.check_call(update_command)
        subprocess.check_call(upgrade_command)

        # reboot system after removing apt-get two1 packages
        if has_apt_two1:
            logger.info(uxstring.UxString.post_apt_remove_reboot)

            if click.confirm(uxstring.UxString.reboot_prompt):
                subprocess.check_call(["sudo", "reboot"])
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        raise exceptions.Two1Error(uxstring.UxString.Error.update_failed)


def has_apt_two1_installed():
    """ Uses apt-cache to check if two1 is installed on the system

    Returns:
        bool: True if two1 is installed in apt, False otherwise
    """
    try:
        subprocess.check_call(["sudo", "apt-cache", "show", "two1"], stdout=subprocess.PIPE)
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        return False

    return True


def remove_apt_two1():
    """ Removes two1 and all of its dependencies from apt-get """
    try:
        subprocess.check_call(["sudo",
                               "apt-get",
                               "autoremove",
                               "--purge",
                               "-y",
                               "--force-yes",
                               "two1"])
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        raise exceptions.Two1Error(uxstring.UxString.Error.removal_failed)
