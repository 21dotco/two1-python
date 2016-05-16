"""Diagnose 21 installation."""
import os
import platform
import shutil
import socket
import sys
import enum
import urllib.parse as parse
import logging

import click
import requests

import two1
import two1.commands.util.version as version
from two1.commands.util import uxstring
from two1.commands.util import decorators
from two1.commands.util import exceptions
from two1.commands.util import bitcoin_computer

# Creates a ClickLogger
logger = logging.getLogger(__name__)


class Check(object):
    """ Maintains the state information of an individual doctor check """

    class Result(enum.Enum):
        """ Enum used to indicate result of a Doctor check """
        PASS = "green"
        FAIL = "red"
        SKIP = "purple"
        WARN = "yellow"

    # change this to adjust the first column width in the doctor report
    WIDTH = 35

    def __init__(self, name, message, value, result):
        self.name = name
        self.message = message
        self.value = value
        self.result = result

    def __str__(self):
        return "  {0: <{width}}->  {1: <{width}}  [{2}]".format(
            self.message,
            self.value,
            click.style(self.result.name, fg=self.result.value),
            width=self.WIDTH)

    def to_dict(self):
        """ Returns a dict of all of the Checks data members """
        return {"name": self.name, "message": self.message, "value": self.value, "result": self.result.name}


class Doctor(object):
    """ Get an installation checkup with the doctor

        Doctor makes severeal checks on your system to ensure your
        sytem is functioning correctly.
    """

    # Types of checkups available
    SPECIALTIES = {
        "general": uxstring.UxString.doctor_general,
        "server": uxstring.UxString.doctor_servers,
        "dependency": uxstring.UxString.doctor_dependencies,
        "BC": uxstring.UxString.doctor_BC,
        }

    # gets printed in begin_checkup
    HEADER = uxstring.UxString.doctor_general

    # OS dictionary of operating system name to version
    SUPPORTED_OS = {
        "Linux": "4.0.0",
        "Darwin": "14.0.0"
        }
    UNMAINTAINED_OS = {
        "Linux": "3.13.0",
        "Darwin": "14.0.0"
        }

    # python version
    SUPPORTED_PYTHON_VERSION = "3.3.0"

    # gets printed in begin_checkup
    HEADER = uxstring.UxString.doctor_dependencies

    # gets printed in begin_checkup
    HEADER = uxstring.UxString.doctor_servers

    # max timeout value when making requests to servers
    SOCKET_TIMEOUT = 10

    # lookup for ports based upon scheme if the hard-coded config value doesn't have a port
    PORT_MAPPING = {'https': 443, 'http': 80}

    def __init__(self, two1_config):
        """ constructor of the Doctor class

        Args:
            config (Config): config object used for getting .two1 information
        """
        self.config = two1_config
        self.checks = {specialty: [] for specialty in self.SPECIALTIES}

    def get_checks(self, result=None):
        """ Gets a flat list of all checks

        Args:
            result (Check.Result): only returns a list of the specified result type

        Raises:
            ValueError: if result is not of type Check.Result
        """
        if result and not isinstance(result, Check.Result):
            raise ValueError("result {} is not of type Check.Result".format(result))

        # flat list of checks
        checks = [check for check_type in self.checks.keys() for check in self.checks[check_type]]
        return checks if not result else [check for check in checks if check.result == result]

    def to_dict(self):
        """ Puts all checks into dict format grouped by check types """
        return {specialty: [check.to_dict() for check in self.checks[specialty]] for specialty in self.checks.keys()}

    def make_http_connection(self, url):
        """ Uses sockets to connect to the server url

        Args:
            url (str): url string with or without a port

        Returns:
            bool: True if socket connection can be made, False otherwise
        """
        url = parse.urlparse(url)

        port = url.port
        if not port:
            port = self.PORT_MAPPING[url.scheme]

        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(self.SOCKET_TIMEOUT)
            sock.connect((url.hostname, port))
        except socket.timeout:
            return False
        except ConnectionRefusedError:
            return False
        except Exception:
            return False

        return True

    def checkup(self, check_type):
        """ Runs through all checks of the check_type given

        Args:
            check_type (str): Type of check to start. One of the keys in HEADERS

        Raises:
            KeyError: if check_type not in self.HEADERS
        """
        logger.info("\n{}\n".format(self.SPECIALTIES[check_type]))

        for attr_name in dir(self):
            if attr_name.startswith("check_{}".format(check_type)):
                func = getattr(self, attr_name)
                if callable(func):
                    result, message, value = func()

                    # truncate the string if value is too long
                    if isinstance(value, str) and len(value) > Check.WIDTH:
                        value = "{}...".format(value[:Check.WIDTH - 3])

                    check = Check(func.__name__, message, value, result)
                    logger.info(str(check))
                    self.checks[check_type].append(check)

        self.print_results(check_type)

    def print_results(self, check_type=""):
        """ Prints a summary of the results to standard out

        Args:
            skip_checks (bool): skips printing check summary if True
        """
        if check_type:
            checks = self.checks[check_type]
        else:
            # flat list of checks
            checks = [check for check_type in self.checks.keys() for check in self.checks[check_type]]

        # breaks down checks into Check.Result buckets
        summary = {result.name: [check for check in checks if check.result == result] for result in Check.Result}
        logger.info("\n{}/{} Checks passed, {} failed, {} warnings, and {} skipped".format(
            len(summary['PASS']),
            len(checks),
            len(summary['FAIL']),
            len(summary['WARN']),
            len(summary['SKIP'])))

    def check_general_two1_version(self):
        """ Checks if the installed two1 version is up-to-date

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    The actaul two1 version installed on the system
        """
        check_str = "21 Tool Version"
        latest_version = version.get_latest_two1_version_pypi()
        actual_version = two1.TWO1_VERSION

        if version.is_version_gte(actual_version, latest_version):
            return Check.Result.PASS, check_str, actual_version

        return Check.Result.FAIL, check_str, actual_version

    def check_general_operating_system(self):
        """ Checks if the OS is supported

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    The name of the operating system
        """
        check_str = "Operating Sytem"
        actual_os = platform.system()
        if actual_os in self.SUPPORTED_OS.keys():
            return Check.Result.PASS, check_str, actual_os

        return Check.Result.FAIL, check_str, actual_os

    def check_general_operating_system_release(self):
        """ Checks if the OS version is supported

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Operating system version
        """
        check_str = "Operating Sytem Release Version"
        actual_os = platform.system()
        actual_os_version = platform.release()

        # make sure the os is supported first
        if actual_os in self.SUPPORTED_OS.keys():

            # use the os as a lookup for the version
            expected_os_version = self.SUPPORTED_OS[actual_os]
            unmaintained_os_version = self.UNMAINTAINED_OS[actual_os]
            if version.is_version_gte(actual_os_version, expected_os_version):
                return Check.Result.PASS, check_str, actual_os_version

            elif version.is_version_gte(actual_os_version, unmaintained_os_version):
                return Check.Result.WARN, check_str, actual_os_version

        return Check.Result.FAIL, check_str, actual_os_version

    def check_general_python_version(self):
        """ Checks if the python version is valid

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    The python version
        """
        check_str = "Python Version"
        actual_py_version = platform.python_version()

        if version.is_version_gte(actual_py_version, self.SUPPORTED_PYTHON_VERSION):
            return Check.Result.PASS, check_str, actual_py_version

        return Check.Result.FAIL, check_str, actual_py_version

    def check_BC_has_chip(self):
        """ Checks if the system has a 21 bitcoin shield

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    "Yes" if the device has a bitcoin shield, "No" otherwise
        """
        check_str = "Has Mining Chip"
        if bitcoin_computer.has_mining_chip():
            return Check.Result.PASS, check_str, "Yes"
        else:
            return Check.Result.FAIL, check_str, "No"

    def check_general_ip_address(self):
        """ Checks if the system has an IP addressed assigned

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    IP address in string format
        """
        check_str = "IP Address"
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.connect(("8.8.8.8", 80))
            ip_address = sock.getsockname()[0]
        except socket.timeout:
            return Check.Result.FAIL, check_str, "Timeout Error on connection"

        return Check.Result.PASS, check_str, ip_address

    def check_dependency_two1_lib(self):
        """ Checks if two1 is properly installed on your system

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Path to the installed two1 package
        """
        check_str = "Two1 Library"

        two1_location = two1.__file__
        if 'two1' in sys.modules:
            return Check.Result.PASS, check_str, two1_location

        return Check.Result.FAIL, check_str, "two1 not in sys.modules"

    def check_dependency_two1_cli(self):
        """ Checks if binaries 21 and twentyone are installed on your system

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Path to the 21 binary
        """
        check_str = "Two1 CLI"
        two1_cli = shutil.which("21")
        twentyone_cli = shutil.which("twentyone")
        if two1_cli and twentyone_cli:
            return Check.Result.PASS, check_str, two1_cli

        if not two1_cli and not twentyone_cli:
            message = "21 and twnetyone binaries not found"
        elif not two1_cli:
            message = "21 binary not found"
        else:
            message = "twentyone binary not found"

        return Check.Result.FAIL, check_str, message

    def check_dependency_zerotier_cli(self):
        """ Checks if zerotier-cli is installed on your system

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Path to the zerotier-cli binary
        """
        check_str = "Zerotier CLI"

        zt_cli = shutil.which("zerotier-cli")
        if zt_cli:
            return Check.Result.PASS, check_str, zt_cli

        if two1.TWO1_DEVICE_ID:
            return Check.Result.FAIL, check_str, "zerotier-cli not installed"
        else:
            return Check.Result.WARN, check_str, "zerotier-cli not installed"

    def check_BC_minerd_cli(self):
        """ Checks if minerd binary is installed on your system

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Path to the minerd binary
        """
        check_str = "Minerd"

        minerd_cli = shutil.which("minerd")
        if minerd_cli:
            return Check.Result.PASS, check_str, minerd_cli
        else:
            return Check.Result.FAIL, check_str, "minerd not installed"

    def check_dependency_wallet_cli(self):
        """ Checks if the two1 wallet is properly installed

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Path to the two1 wallet
        """
        check_str = "Two1 Wallet"

        wallet_cli = shutil.which("wallet")
        if wallet_cli:
            return Check.Result.PASS, check_str, wallet_cli

        return Check.Result.FAIL, check_str, "Two1 wallet not installed"

    def check_dependency_two1_dotenv(self):
        """ Checks if the two1 dotenv folder and files are present

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Path to the two1 dotenv folder
        """
        check_str = "Two1 Dotenv"

        dotenv_path = two1.TWO1_USER_FOLDER
        if not os.path.exists(dotenv_path):
            return Check.Result.FAIL, check_str, "{} does not exist".format(dotenv_path)

        config_file_path = two1.TWO1_CONFIG_FILE
        config_file = config_file_path.split(os.path.sep)[-1]
        if os.path.exists(config_file_path):
            return Check.Result.PASS, check_str, config_file_path

        return Check.Result.FAIL, check_str, "{} config file does not exist".format(config_file)

    def check_server_21_api(self):
        """ Checks if the 21 api is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Url to the 21 api
        """
        check_str = "21 API"
        result = Check.Result.FAIL
        if self.make_http_connection(two1.TWO1_HOST):
            result = Check.Result.PASS

        return result, check_str, two1.TWO1_HOST

    def check_server_21_pool(self):
        """ Checks if the 21 pool api is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Url to the 21 pool api
        """
        check_str = "21 Pool"
        result = Check.Result.FAIL
        if self.make_http_connection(two1.TWO1_POOL_URL):
            result = Check.Result.PASS

        return result, check_str, two1.TWO1_POOL_URL

    def check_server_21_logging(self):
        """ Checks if the 21 logging server is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Url to the 21 logging server
        """
        check_str = "21 Logging"
        result = Check.Result.FAIL
        if self.make_http_connection(two1.TWO1_LOGGER_SERVER):
            result = Check.Result.PASS

        return result, check_str, two1.TWO1_LOGGER_SERVER

    def check_server_21_provider(self):
        """ Checks if 21 blockchain provider is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Url to the 21 blockchain provider
        """
        check_str = "21 Blockchain Provider"
        result = Check.Result.FAIL
        # checks connection and status code
        if self.make_http_connection(two1.TWO1_PROVIDER_HOST):
            result = Check.Result.PASS

        return result, check_str, two1.TWO1_PROVIDER_HOST

    def check_server_21_pypi(self):
        """ Checks if 21 hosted pypi server is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    Url to the 21 pypi server
        """
        check_str = "21 Pypicloud"
        result = Check.Result.FAIL
        if self.make_http_connection(two1.TWO1_PYPI_HOST):
            result = Check.Result.PASS

        return result, check_str, two1.TWO1_PYPI_HOST

    def check_server_21_slack(self):
        """ Checks if the 21 slack server is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    HTTP status code from the request
        """
        return self._check_server("21 Slack", "https://slack.21.co")

    def check_server_website(self):
        """ Checks if the 21.co is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    HTTP status code from the request
        """
        return self._check_server("21 Website", "https://21.co")

    def check_server_mkt(self):
        """ Checks if the 21 marketplace is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    HTTP status code from the request
        """
        return self._check_server("21 Marketplace", "https://21.co/mkt")

    def _check_server(self, check_str, url):
        """ Checks if the <check_str> server at <url> is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    HTTP status code from the request
        """
        try:
            response = requests.get(url)
        except requests.exceptions.RequestException:
            return Check.Result.FAIL, check_str, url

        if response.status_code >= 400:
            return Check.Result.FAIL, check_str, url

        return Check.Result.PASS, check_str, url

    def check_BC_raspbian_apt(self):
        """ Checks if the raspbian mirror is up

        Returns:
            Check.Result, str, str: Result of the check
                                    Human readable message describing the check
                                    HTTP status code from the request
        """
        check_str = "Raspbian Mirror"
        url = "http://mirrordirector.raspbian.org/raspbian"
        result = Check.Result.FAIL
        response = requests.get(url)
        if response.status_code < 400:
            result = Check.Result.PASS

        return result, check_str, response.status_code


@click.command()
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
def doctor(ctx):
    """ Diagnose this 21 installation."""
    return _doctor(ctx.obj['config'])


def _doctor(two1_config):

    # warm welcome message
    logger.info(uxstring.UxString.doctor_start)

    # Get an appointment with the doctor
    doc = Doctor(two1_config)

    # Get a general doctor checkup
    doc.checkup("general")
    doc.checkup("dependency")
    doc.checkup("server")
    if bitcoin_computer.get_device_uuid():
        doc.checkup("BC")

    logger.info("\n" + uxstring.UxString.doctor_total)

    # groups all checks into one class for reuse of print_summary
    doc.print_results()

    if len(doc.get_checks(Check.Result.FAIL)) == 0:
        return doc.to_dict()
    else:
        raise exceptions.Two1Error("21 doctor failed some checks.", json=doc.to_dict())
