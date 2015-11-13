import os
import sys
import tempfile
import shutil
from two1.tests.integration.util import random_str
import pytest
from click.testing import CliRunner
import pexpect
import json
import requests

def pytest_addoption(parser):
    parser.addoption("--integration", action="store_true",
                     help="Run the integration tests")
    parser.addoption("--full-integration-inject-flush", action="store_true",
                     help="Inject a Flush in the middle of the full integration")
    parser.addoption("--full-integration-file", action="store",
                     help="Run the full test integration with a file scenario")
    parser.addoption("--full-integration-number", type=int, action="store",
                     default=0,
                     help="Run the full test integration with N tasks")
    parser.addoption("--integration-cli-wallet-path", type=str, action="store",
                     default="",
                     help="Path to the wallet to use for integration")
    parser.addoption("--integration-cli-config-path", type=str, action="store",
                     default="",
                     help="Path to the user config to use for integration")
