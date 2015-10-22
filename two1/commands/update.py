import sys
import subprocess
from urllib.parse import urljoin
from datetime import date
from datetime import datetime
from distutils.version import LooseVersion

import os
import click
from two1.commands.config import TWO1_VERSION
from two1.commands.config import TWO1_PYPI_HOST
from two1.commands.config import TWO1_PACKAGE_NAME
from two1.commands.exceptions import ServerRequestError
from two1.lib.server.analytics import capture_usage
from two1.lib.util.uxstring import UxString
from two1.commands.config import pass_config


@click.command()
@click.argument('version', nargs=1, required=False, default='latest')
@click.pass_context
def update(ctx, version):
    """Update the 21 Command Line Interface.

\b
Usage
-----
Invoke this with no arguments to update the CLI.
$ 21 update
"""
    config = ctx.obj['config']
    _update(config, version)


@capture_usage
def _update(config, version):
    click.echo(UxString.update_check)
    update_two1_package(config, version, force_update_check=True)

TWO1_APT_INSTALL_PACKAGE_PATH = "/usr/lib/python3/dist-packages/" + TWO1_PACKAGE_NAME


def update_two1_package(config, version, force_update_check=False):
    """ Handles the updating of the CLI software including any dependencies.

        How does the update work?
        The entry point function to run the updater is update(self).
        Update steps
        1) If update check has not been performed today, check to see if an
           update is available.
        2) If a new version is available, run the updater and reset the update
           check.

        Key State Variables in the config:
            config.last_update_check (string): This stores the last date on
            which an update check was performed in %Y-%m-%d format.

        Args:
            config (Config): Config context object
            version (string): The requested version of 21 to install (defaults
                to 'latest')
            force_update_check (bool): Forces an update check with the pypi
            service

        Returns:
            dict: A dict with two keys are returned.
                  update_available (bool): Whether an update is available.
                  update_successful (bool): Whether the update was successfully
                  downloaded and installed.
    """
    ret = dict(
        update_available=False,
        update_successful=None
    )
    # Has update been already performed today?
    if not force_update_check and checked_for_an_update_today(config):
        # do nothing
        pass
    else:
        # Set the update check date to today. There are several schools of
        # thought on this. This could be done after a successful update as
        # well.
        set_update_check_date(config, date.today())

        installed_version = TWO1_VERSION
        latest_version = lookup_pypi_version(version)
        # Check if available version is more recent than the installed version.
        if (LooseVersion(latest_version) > LooseVersion(installed_version) or
                version != 'latest'):
            ret["update_available"] = True
            # An updated version of the package is available.
            # The update is performed either using pip or apt-get depending
            # on how two1 was installed in the first place.

            click.echo(UxString.update_package % latest_version)
            # Detect if the package was installed using apt-get
            # This detection only works for deb based linux systems
            if os.path.isdir(TWO1_APT_INSTALL_PACKAGE_PATH):
                ret["update_successful"] = perform_apt_based_update()
            else:
                ret["update_successful"] = perform_pip_based_update(
                    latest_version)

    return ret


def lookup_pypi_version(version='latest'):
    """Get the latest version of the software from the PyPi service.

    Args:
        version (string): The requested version number, sha hash, or relative
        timing of the released package to install.
        Example: '0.2.1', '8e15eb1', 'latest'

    Returns:
        version (string): A version string with period delimited major,
        minor, and patch numbers.
        Example: '0.2.1'
    """
    import requests
    try:
        url = urljoin(TWO1_PYPI_HOST,
                      "api/package/{}/".format(TWO1_PACKAGE_NAME))
        r = requests.get(url)
        data = r.json()
    except:
        raise ServerRequestError(UxString.Error.connection % 'PyPI host.')

    pypi_version = None

    try:
        packages = data["packages"]
        two1data = packages[0]
        if version != 'latest':
            data = next((p for p in packages if version in p["version"]), None)
            if not data:
                click.echo(UxString.Error.version_not_found % version)
            else:
                two1data = data

        if two1data["name"] == TWO1_PACKAGE_NAME:
            pypi_version = two1data["version"]
    except (AttributeError, KeyError, TypeError):
        raise ServerRequestError(UxString.Error.server_err)

    return pypi_version


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
        last_update_check_date = datetime.strptime(last_update_check, "%Y-%m-%d").date()
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


def set_update_check_date(config, update_date):
    """ Set's the date on which the last update check was performed.

    Args:
        config (Config): Config context object
        update_date (date): Set this as the last update check date
    """

    # Save the date in a locked down string format
    config.update_key('last_update_check', update_date.strftime("%Y-%m-%d"))
    config.save()


def perform_pip_based_update(version):
    """ This will use pip3 to update the package (without dependency update)
    """

    install_command = ["pip3",
                       "install",
                       "-i",
                       "{}/pypi".format(TWO1_PYPI_HOST),
                       "-U",
                       "--no-deps",
                       "-I",
                       "{}=={}".format(TWO1_PACKAGE_NAME, version)]

    try:
        # Inside a virtualenv, sys.prefix points to the virtualenv directory,
        # and sys.real_prefix points to the "real" prefix of the system Python
        # (often /usr or /usr/local or some such).
        if hasattr(sys, "real_prefix"):
            subprocess.check_call(install_command)
        else:
            click.echo(UxString.update_superuser)
            # If not in a virtual environment, run the install command
            # with sudo permissions.
            subprocess.check_call(["sudo"] + install_command)
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        # TODO: log this error on the server backend for diagnostics
        click.echo(UxString.Error.update_failed)
        return False

    return True


def perform_apt_based_update():
    """ This will perform an apt-get based update.
    """

    update_command = ["sudo",
                      "apt-get",
                      "update"
                      ]
    upgrade_command = ["sudo",
                       "apt-get",
                       "install",
                       "--only-upgrade",
                       TWO1_PACKAGE_NAME
                       ]
    ret = False
    try:
        subprocess.check_call(update_command)
        subprocess.check_call(upgrade_command)
        ret = True
    except (subprocess.CalledProcessError, OSError, FileNotFoundError):
        # TODO: log this error on the server backend for diagnostics
        click.echo(UxString.Error.update_failed)

    return ret
