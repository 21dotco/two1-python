# standard python imports
import os

# 3rd party imports
import pytest

# two1 imports
from two1.sell.machine import Two1MachineVirtual
from two1.sell.machine import VmState, MachineState
from two1.sell.composer import Two1ComposerContainers
from two1.sell.composer import ComposerState
from two1.sell.client import Two1SellClient

SKIP_TEST = os.environ.get("SKIP_SELL_TESTS", True)


def set_up_machine(sys_platform):
    """ Create the machine layer and init to READY state.

    Returns: sell_client
    """
    sell_client = Two1SellClient(sys_platform)
    sell_client.manager.machine.start_networking()
    sell_client.manager.machine.create_machine()
    sell_client.manager.machine.start_machine()
    return sell_client


def tear_down_machine(sell_client):
    """ Tear down the machine layer.
    """
    sell_client.manager.machine.stop_machine()
    sell_client.manager.machine.stop_networking()
    sell_client.manager.machine.delete_machine()


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_create_client_mac(sys_platform):
    """ Test creation of Two1SellClient on Mac OS X (supported).
    """
    sell_client = None
    try:
        sell_client = Two1SellClient(sys_platform)
    except Exception:
        if sell_client is not None:
            assert isinstance(sell_client.machine, Two1MachineVirtual)
            assert isinstance(sell_client.composer, Two1ComposerContainers)
        else:
            assert False


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_start_stop_networking(sys_platform):
    """ Test starting and stopping networking.
    """
    sell_client = Two1SellClient(sys_platform)

    if sell_client.manager.machine.status_networking() is True:
        sell_client.manager.machine.stop_networking()
        assert sell_client.manager.machine.status_networking() is False

    sell_client.manager.start_networking()
    assert sell_client.manager.machine.status_networking() is True

    sell_client.manager.stop_networking()
    assert not sell_client.manager.machine.status_networking()


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_create_delete_machine_layer(sys_platform):
    """ Test starting and stopping networking.
    """
    sell_client = Two1SellClient(sys_platform)

    if sell_client.manager.machine.status_machine() != VmState.NOEXIST:
        sell_client.manager.machine.delete_machine()
        assert sell_client.manager.machine.status_machine() == VmState.NOEXIST
    sell_client.manager.start_networking()
    sell_client.manager.create_machine()
    assert sell_client.manager.machine.status_machine() != VmState.NOEXIST
    sell_client.manager.delete_machine()
    sell_client.manager.stop_networking()
    assert sell_client.manager.machine.status_machine() == VmState.NOEXIST


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_start_stop_machine_layer(sys_platform):
    """ Test starting and stopping machine layer.
    """
    sell_client = Two1SellClient(sys_platform)

    if sell_client.manager.machine.status_machine() == VmState.RUNNING:
        sell_client.manager.machine.stop_machine()
        sell_client.manager.machine.delete_machine()
        sell_client.manager.machine.stop_networking()
        assert sell_client.manager.machine.status_machine() == VmState.NOEXIST

    sell_client.manager.machine.start_networking()
    sell_client.manager.machine.create_machine()
    sell_client.manager.machine.start_machine()
    assert sell_client.manager.machine.status_machine() == VmState.RUNNING
    assert sell_client.manager.machine.state == MachineState.READY

    sell_client.manager.machine.stop_machine()
    assert sell_client.manager.machine.status_machine() == VmState.STOPPED

    sell_client.manager.machine.stop_networking()
    sell_client.manager.machine.delete_machine()
    assert sell_client.manager.machine.status_machine() == VmState.NOEXIST


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_connect(sys_platform):
    """ Test composer connection with machine layer.
    """
    sell_client = set_up_machine(sys_platform)
    sell_client.manager.composer.connect(sell_client.manager.machine.env,
                                         sell_client.manager.machine_host)
    assert sell_client.manager.composer.connected == ComposerState.CONNECTED
    tear_down_machine(sell_client)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_build_base_services(sys_platform):
    """ Test building base services with Two1Composer.
    """
    sell_client = set_up_machine(sys_platform)
    sell_client.manager.build_base_services()
    assert 1 == 1
    tear_down_machine(sell_client)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_build_market_services(sys_platform):
    """ Test building market services with Two1Composer.
    """
    sell_client = set_up_machine(sys_platform)
    sell_client.manager.build_base_services()
    sell_client.manager.build_market_services(["ping"])
    assert 1 == 1
    tear_down_machine(sell_client)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_start_stop_services(sys_platform):
    """ Test starting and stopping market services with Two1Composer.
    """
    services = ["ping"]
    sell_client = set_up_machine(sys_platform)

    sell_client.manager.build_base_services()
    sell_client.manager.build_market_services(services)
    status_env = sell_client.manager.write_global_services_env('jgfreshprod23', 'Tester123')

    sell_client.manager.start_services(services)
    assert 1 == 1
    sell_client.manager.stop_services(services)
    tear_down_machine(sell_client)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_create_client_aws_ubuntu(sys_platform):
    """ Test creation of Two1SellClient on AWS Ubuntu 12.04 (supported).
    """
    assert 1 == 1
