import click
import errno
import os
import platform
import re
import requests
import shutil
import socket
import sys
from enum import Enum, unique
from json import JSONEncoder
from two1.commands.config import \
    TWO1_LOGGER_SERVER, TWO1_HOST, TWO1_PROVIDER_HOST, \
    TWO1_PYPI_HOST, TWO1_POOL_URL, TWO1_MERCHANT_HOST, \
    TWO1_VERSION, TWO1_USER_FOLDER, TWO1_CONFIG_FILE
from two1.commands.status import has_bitcoinkit
from two1.lib.util.exceptions import TwoOneError
from two1.lib.server.analytics import capture_usage
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString

# Doctor Constants
MIN_VERSION_21 = (0, 3, 0)
MIN_VERSION_OS = (1, 0, 0)
if platform.system() == "Darwin":
  MIN_VERSION_OS = (14, 0, 0)
elif platform.system() == "Linux":
  MIN_VERSION_OS = (4, 0, 0)
MIN_VERSION_PYTHON = (3, 3, 0)
SOCKET_TIMEOUT = 10
DEMO_ENDPOINTS = [
    {"url": "/bitcoin_auth/token", "method": "get"},
    {"url": "/phone/send-sms", "method": "post"},
    {"url": "/search/bing", "method": "post"},
]

@unique
class DoctorStatus(Enum):
    OK, Fail, Warning = range(3)

    def prettyprint(self):
        color = "white"
        if self.name == "OK":
            color = "green"
        elif self.name == "Fail":
            color = "red"
        elif self.name == "Warning":
            color = "orange"
        return click.style(self.name, fg=color)

class DoctorCheck:
    def __init__(self, config):
        self.config = config;
        self.checks = []
        self.summary = {}
        self.passed = 0
        self.warnings = 0

    def addCheck(self, name, value, status, error=None):
        self.checks.append({
            "name": name,
            "value": value,
            "status": status.name,
            "error": error
        })
        self.config.log("  {: <30} -> {:<35} [{}]".format(name, value, status.prettyprint()))
        if status is DoctorStatus.OK:
            self.passed += 1
        elif status is DoctorStatus.Warning:
            self.passed += 1
            self.warnings += 1
        elif status is DoctorStatus.Fail:
            if error:
                self.config.log(UxString.doctor_error + error)

    def generateSummary(self):
        final_status = DoctorStatus.Fail
        if self.passed == len(self.checks):
            final_status = DoctorStatus.OK
            if self.warnings > 0:
                final_status = DoctorStatus.Warning
        self.summary = {
            "passed": self.passed,
            "warnings": self.warnings,
            "total": len(self.checks),
            "status": final_status.name
        }
        DoctorCheck.printSummary(self.config, self.summary)

    # static method
    def printSummary(config, *summary):
        total = {
            "passed": 0,
            "total": 0,
            "warnings": 0
        }

        for s in summary:
            total["passed"] += s["passed"]
            total["total"] += s["total"]
            total["warnings"] += s["warnings"]

        final_status = DoctorStatus.Fail
        if total["passed"] == total["total"]:
            final_status = DoctorStatus.OK
            if total["warnings"] > 0:
                final_status = DoctorStatus.Warning

        config.log("\n{} / {} tests passed, {} warnings. [{}]\n".format(\
            total["passed"],
            total["total"],
            total["warnings"],
            final_status.prettyprint()))

    def json(self):
        return {
            "checks": self.checks,
            "summary": self.summary
        }

@click.command()
@json_output
def doctor(config):
    """Checks on the health of the tool.
    """
    return _doctor(config)

@capture_usage
def _doctor(config):
    def assertEqual(checker, name, val, expected_val):
        if val == expected_val:
            checker.addCheck(name, val, DoctorStatus.OK)
        else:
            checker.addCheck(name, val, DoctorStatus.Fail, "{} != {}.".format(val, expected_val))

    def assertTrue(checker, name, val, success_msg="Exists", error_msg = None):
        if val == True or val == "Yes":
            checker.addCheck(name, success_msg, DoctorStatus.OK)
        else:
            if error_msg == None:
                error_msg = "{} is not True.".format(val)
            checker.addCheck(name, "No", DoctorStatus.Fail, error_msg)


    def assertAny(checker, name, val):
        if val != None and val != "":
            checker.addCheck(name, val, DoctorStatus.OK)
        else:
            checker.addCheck(name, val, DoctorStatus.Fail, "{} cannot be None.".format(name))

    def assertIn(checker, name, val, expected_val_array):
        if val in expected_val_array:
            checker.addCheck(name, val, DoctorStatus.OK)
        else:
            checker.addCheck(name, val, DoctorStatus.Fail, "{} must be one of {}".format(val, expected_val_array)) 

    def assertGte(checker, name, val, min_val):
        if val >= min_val:
            checker.addCheck(name, val, DoctorStatus.OK)
        else:
            checker.addCheck(name, val, DoctorStatus.Fail, "{} must be >= {}".format(val, min_val))

    def assertVersionGte(checker, name, version, min_version):
        ok = True
        version_str = "{}.{}.{}".format(version[0],version[1],version[2])
        # compare major
        if int(version[0]) > min_version[0]:
            ok = True
        elif int(version[0]) < min_version[0]:
            ok = False
        else:
            # compare minor
            if int(version[1]) > min_version[1]:
                ok = True
            elif int(version[1]) < min_version[1]:
                ok = False
            else:
                # compare revision
                rev = int(version[2].split('-')[0])
                if rev >= min_version[2]:
                    ok = True
                elif rev < min_version[2]:
                    ok = False
        if ok:
            checker.addCheck(name, version_str, DoctorStatus.OK)
        else:
            checker.addCheck(name, version_str, DoctorStatus.Fail, "Version must be >= {}.{}.{}. Your version is {}.{}.{}.".format(min_version[0], min_version[1], min_version[2], version[0],version[1],version[2]))

    def assertHTTPStatusCode(checker, name, url, method="get", expected_status_code=402):
      try:
          request_method = getattr(requests, method)
          r  = request_method(url, timeout=SOCKET_TIMEOUT)
          if r.status_code == expected_status_code:
              checker.addCheck("{} {}".format(method.upper(), name), r.status_code, DoctorStatus.OK)
          else:
              checker.addCheck("{} {}".format(method.upper(), name), r.status_code, DoctorStatus.Fail, "Expected status code '{}'".format(expected_status_code))
      except requests.exceptions.ConnectionError:
          checker.addCheck("{} {}".format(method.upper(), name), "Failed", DoctorStatus.Fail, "Could not connect to '{}'".format(url))
      except Exception as e:
          checker.addCheck("{} {}".format(method.upper(), name), "Failed", DoctorStatus.Fail, str(e))
    
    def assertSocket(checker, name, url):
        protocol = "http"
        port = 80
        hostname = ""

        url_components = url.split("://")
        if len(url_components) >= 2:
            protocol = url_components[0]
            hostname = url_components[1]
            host_components = hostname.split(":")
            if len(host_components) == 2:
                hostname = host_components[0]
                port = int(host_components[1])
        else:
            checker.addCheck(name, url, DoctorStatus.Fail, "Invalid url " + url)
            return

        if protocol == "https":
            port = 443

        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(SOCKET_TIMEOUT)
        try:
            result = s.connect_ex((hostname, port))
            s.close()
            if result > 0:
                checker.addCheck(name, url, DoctorStatus.Fail, errno.errorcode[result])
            else:
                checker.addCheck(name, "{}:{}".format(hostname, port), DoctorStatus.OK)
        except Exception as e:
            s.close()
            checker.addCheck(name, url, DoctorStatus.Fail, str(e))

    def assertCommandExists(checker, name, cmd, error_msg=None):
        cmd_path = None
        try:
            cmd_path = shutil.which(cmd)
        except Exception as e:
            pass
        if error_msg == None:
          error_msg = "'{}' does not exist.".format(cmd)
        assertTrue(check_dependencies, name, cmd_path != None, error_msg=error_msg)

    def assertPathExists(checker, name, path):
        return assertTrue(checker, name, os.path.exists(path), error_msg="'{}' does not exist.".format(path))

    # doctor code start
    config.log(UxString.doctor_start)

    # Checking OS
    config.log(UxString.doctor_general)
    check_general = DoctorCheck(config)
    assertVersionGte(check_general, "21 Tool version", TWO1_VERSION.split('.'), MIN_VERSION_21)
    assertIn(check_general, "OS System", platform.system(), ["Windows", "Linux", "Darwin"])
    assertVersionGte(check_general, "OS Release", platform.release().split('.'), MIN_VERSION_OS)
    assertVersionGte(check_general, "Python version", platform.python_version_tuple(), MIN_VERSION_PYTHON)
    assertTrue(check_general, "Has Bitcoin kit", has_bitcoinkit(), success_msg="Yes", error_msg="Bitcoin kit not detected.")
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        assertAny(check_general, "IP Address", s.getsockname()[0])
    except Exception as e: 
        assertTrue(check_general, "IP Address", False, error_msg="No Internet Connectivity Found.")
    check_general.generateSummary()

    # Checking dependencies
    config.log(UxString.doctor_dependencies)
    check_dependencies = DoctorCheck(config)
    assertTrue(check_dependencies, "two1 python library", 'two1' in sys.modules, error_msg="two1 lib does not exist.")
    cli_path = None
    try:
        cli_path = shutil.which('21')
    except Exception as e:
        pass
    assertCommandExists(check_dependencies, "21 CLI", cmd="21", error_msg="21 CLI not bound to '21'.")
    assertCommandExists(check_dependencies, "Zerotier CLI", cmd="zerotier-cli", error_msg="Zerotier CLI not bound.")
    assertCommandExists(check_dependencies, "apt-get", cmd="apt-get")
    assertCommandExists(check_dependencies, "minerd", cmd="minerd")
    assertCommandExists(check_dependencies, "wallet", cmd="wallet")

    assertPathExists(check_dependencies, ".two1 folder", TWO1_USER_FOLDER)
    assertPathExists(check_dependencies, ".two1 config file", TWO1_CONFIG_FILE)
    check_dependencies.generateSummary()

    # Checking demo endpoints
    config.log(UxString.doctor_demo_endpoints)
    check_demos = DoctorCheck(config)
    for demo_endpoint in DEMO_ENDPOINTS:
        assertHTTPStatusCode(check_demos, name=demo_endpoint["url"], url=(TWO1_MERCHANT_HOST + demo_endpoint["url"]), method=demo_endpoint["method"], expected_status_code=402)
    check_demos.generateSummary()

    # Check servers
    config.log(UxString.doctor_servers)
    check_servers = DoctorCheck(config)
    assertSocket(check_servers, "Pool2 Api", TWO1_HOST)
    assertSocket(check_servers, "Pool2 Tcp", TWO1_POOL_URL)
    assertSocket(check_servers, "Log server", TWO1_LOGGER_SERVER)
    assertSocket(check_servers, "Merchant", TWO1_MERCHANT_HOST)
    assertSocket(check_servers, "Blockchain", TWO1_PROVIDER_HOST)
    assertSocket(check_servers, "PyPi Host", TWO1_PYPI_HOST)
    assertHTTPStatusCode(check_servers, name="21co slack", url="https://slack.21.co", expected_status_code=200)
    assertHTTPStatusCode(check_servers, name="Raspbian package repo", url="http://mirrordirector.raspbian.org/raspbian", expected_status_code=200)
    assertHTTPStatusCode(check_servers, name="Chain.com API", url="https://api.chain.com", expected_status_code=401)
    
    check_servers.generateSummary()

    config.log(UxString.doctor_total)
    DoctorCheck.printSummary(config, \
        check_general.summary, \
        check_dependencies.summary, \
        check_demos.summary, \
        check_servers.summary)

    result =  {
        "general": check_general.json(),
        "dependencies": check_dependencies.json(),
        "demo": check_demos.json(),
        "servers": check_servers.json()
    }

    if all([doctor_check['summary']['total'] == doctor_check['summary']['passed'] for doctor_check in result.values()]):
        return result
    else:
        raise TwoOneError("21 doctor failed some checks.", result)
