""" Uninstall 21 and its dependencies. """
# standard python imports
import logging
import subprocess
import tempfile

# 3rd party requests
import click

# two1 imports
from two1.commands.util import uxstring
from two1.commands.util import decorators

# Creates a ClickLogger
logger = logging.getLogger(__name__)

UNINSTALL_SH = b"""\
#!/bin/bash

print_step() {
    printf "\n$1\n"
}

print_error() {
    printf "$1\n"
}

uninstall_common()
{
    # Remove two1 Python Library
    # This does not remove the ~/.two1/ folder!
    sudo pip3 uninstall -y two1
}

uninstall_linux()
{
    # Remove ZeroTier One
    # Does not remove credentials!
    read -r -p "Uninstall ZeroTier [y/N] " response
    case $response in
        [yY][eE][sS]|[yY])
            sudo dpkg -r zerotier-one
            echo 'Uninstalled ZeroTier'
            ;;
        *)
            echo 'Skipping ZeroTier'
            ;;
    esac
}

uninstall_mac()
{
    # Remove ZeroTier One
    # Does not remove credentials!
    read -r -p "Uninstall ZeroTier [y/N] " response
    case $response in
        [yY][eE][sS]|[yY])
            # Remove ZeroTier One
            sudo "/Library/Application Support/ZeroTier/One/uninstall.sh"
            echo 'Uninstalled ZeroTier'
            ;;
        *)
            echo 'Skipping ZeroTier'
            ;;
    esac

    # Remove Homebrew Package Manager
    read -r -p "Uninstall Homebrew [y/N] " response
    case $response in
        [yY][eE][sS]|[yY])
            /usr/bin/ruby -e "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/master/uninstall)"
            echo 'Uninstalled Homebrew'
            ;;
        *)
            echo 'Skipping Homebrew'
            ;;
    esac
}

main()
{
    print_step "Uninstalling 21's software libraries and tools"
    uninstall_common
    UNAME=$(uname)
    case "${UNAME:-nil}" in
        Linux)
            uninstall_linux
        ;;
        Darwin) ## Mac OSX
            uninstall_mac
        ;;
        *)
            print_error "Sorry, $UNAME is currently not supported via this uninstaller."
            exit 1
        ;;
    esac
    exit 0
}

main
"""


@click.command()
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def uninstall(ctx):
    """Uninstall 21 and its dependencies.

\b
Usage
-----
Invoke this with no arguments to uninstall 21.
$ 21 uninstall
"""
    logger.info(uxstring.UxString.uninstall_init)

    with tempfile.NamedTemporaryFile(delete=False) as f:
        f.write(UNINSTALL_SH)

    try:
        out = subprocess.check_output(['sh', f.name])
        logger.info(uxstring.UxString.uninstall_success)
    except subprocess.CalledProcessError:
        raise ValueError("uninstall error")
