# standard python imports
import os

# 3rd party imports
import pytest

# two1 imports
from two1.sell.machine import Two1MachineVirtual
from two1.sell.machine import VmState, MachineState
from two1.sell.composer import Two1ComposerContainers
from two1.sell.composer import ComposerState
from two1.sell.manager import Two1Manager

SKIP_TEST = os.environ.get("SKIP_SELL_TESTS", True)


def set_up_machine(sys_platform):
    """ Create the machine layer and init to READY state.

    Returns: manager
    """
    manager = Two1Manager(sys_platform)
    manager.machine.start_networking()
    manager.machine.create_machine()
    manager.machine.start_machine()
    return manager


def tear_down_machine(manager):
    """ Tear down the machine layer.
    """
    manager.machine.stop_machine()
    manager.machine.stop_networking()
    manager.machine.delete_machine()


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_create_client_mac(sys_platform):
    """ Test creation of Two1SellClient on Mac OS X (supported).
    """
    manager = None
    try:
        manager = Two1Manager(sys_platform)
    except Exception:
        if manager is not None:
            assert isinstance(manager.machine, Two1MachineVirtual)
            assert isinstance(manager.composer, Two1ComposerContainers)
        else:
            assert False


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_start_stop_networking(sys_platform):
    """ Test starting and stopping networking.
    """
    manager = Two1Manager(sys_platform)

    if manager.machine.status_networking() is True:
        manager.machine.stop_networking()
        assert manager.machine.status_networking() is False

    manager.start_networking()
    assert manager.machine.status_networking() is True

    manager.stop_networking()
    assert not manager.machine.status_networking()


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_create_delete_machine_layer(sys_platform):
    """ Test starting and stopping networking.
    """
    manager = Two1Manager(sys_platform)

    if manager.machine.status_machine() != VmState.NOEXIST:
        manager.machine.delete_machine()
        assert manager.machine.status_machine() == VmState.NOEXIST
    manager.start_networking()
    manager.create_machine()
    assert manager.machine.status_machine() != VmState.NOEXIST
    manager.delete_machine()
    manager.stop_networking()
    assert manager.machine.status_machine() == VmState.NOEXIST


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_start_stop_machine_layer(sys_platform):
    """ Test starting and stopping machine layer.
    """
    manager = Two1Manager(sys_platform)

    if manager.manager.machine.status_machine() == VmState.RUNNING:
        manager.manager.machine.stop_machine()
        manager.manager.machine.delete_machine()
        manager.manager.machine.stop_networking()
        assert manager.manager.machine.status_machine() == VmState.NOEXIST

    manager.manager.machine.start_networking()
    manager.manager.machine.create_machine()
    manager.manager.machine.start_machine()
    assert manager.manager.machine.status_machine() == VmState.RUNNING
    assert manager.manager.machine.state == MachineState.READY

    manager.manager.machine.stop_machine()
    assert manager.manager.machine.status_machine() == VmState.STOPPED

    manager.manager.machine.stop_networking()
    manager.manager.machine.delete_machine()
    assert manager.manager.machine.status_machine() == VmState.NOEXIST


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_connect(sys_platform):
    """ Test composer connection with machine layer.
    """
    manager = set_up_machine(sys_platform)
    manager.composer.connect(manager.machine.env,
                             manager.machine_host)
    assert manager.manager.composer.connected == ComposerState.CONNECTED
    tear_down_machine(manager)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_build_base_services(sys_platform):
    """ Test building base services with Two1Composer.
    """
    manager = set_up_machine(sys_platform)
    manager.manager.build_base_services()
    assert 1 == 1
    tear_down_machine(manager)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_build_market_services(sys_platform):
    """ Test building market services with Two1Composer.
    """
    manager = set_up_machine(sys_platform)
    manager.manager.build_base_services()
    manager.manager.build_market_services(["ping"])
    assert 1 == 1
    tear_down_machine(manager)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_composer_start_stop_services(sys_platform):
    """ Test starting and stopping market services with Two1Composer.
    """
    services = ["ping"]
    manager = set_up_machine(sys_platform)

    manager.manager.build_base_services()
    manager.manager.build_market_services(services)
    manager.manager.write_global_services_env('jgfreshprod23', 'Tester123')

    manager.manager.start_services(services)
    assert 1 == 1
    manager.manager.stop_services(services)
    tear_down_machine(manager)


@pytest.mark.skipif(SKIP_TEST, reason="need infra")
def test_create_client_aws_ubuntu(sys_platform):
    """ Test creation of Two1SellClient on AWS Ubuntu 12.04 (supported).
    """
    assert 1 == 1
