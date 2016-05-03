# standard python imports
import os
import re
import json
import subprocess
from enum import Enum
from abc import ABCMeta
from abc import abstractmethod

# two1 imports
from two1.commands.util import zerotier
from two1.commands.util import exceptions
from two1.commands.util import uxstring
from two1.sell.exceptions.exceptions_machine import *


class MachineState(Enum):
    """ Machine networking state.
    """
    READY = 1,  # networking up
    NOREADY = 2  # networking down


class VmState(Enum):
    """ Virtual machine state.
    """
    STOPPED = 1,
    RUNNING = 2,
    NOEXIST = 3,
    UNKNOWN = 4


class Two1Machine():
    """ Abstract base machine layer.
    """
    __metaclass__ = ABCMeta

    DEFAULT_ZEROTIER_INTERFACE = "zt0"
    DEFAULT_MARKET_NETWORK = "10.244"
    DEFAULT_SERVICE_PORT = 8080

    ZEROTIER_IP_PATTERN = re.compile(r"zt\d+(.+\n)+?\s+inet (addr:)?(?P<ip>%s\.\d{1,3}\.\d{1,3})" %
                                     re.escape(DEFAULT_MARKET_NETWORK))
    MACHINE_ENV_PATTERN = re.compile(r'''^export(\s*)(?P<env_key>\w*)(\s*)=(\s*)"(?P<env_value>.*)"''')
    MACHINE_CONFIG_FILE = os.path.expanduser("~/.two1/services/machine_config.json")

    @property
    def host(self):
        """ Virtual network host IP.
        """
        return self._get_market_address()

    @property
    def port(self):
        """ 21 server port.
        """
        try:
            with open(self.MACHINE_CONFIG_FILE) as f:
                return json.load(f)['server_port']
        except Exception:
            return ""

    @property
    def env(self):
        """ Machine layer environment.
        """
        return self._get_machine_env()

    @property
    def state(self):
        """ Machine layer state label.
        """
        return self._compute_state()

    @abstractmethod
    def start_networking(self):
        """ Start networking.
        """

    @abstractmethod
    def stop_networking(self):
        """ Stop networking.
        """

    @abstractmethod
    def status_networking(self):
        """ Get network status.
        """

    @abstractmethod
    def _compute_state(self):
        """ Compute machine state label.
        """

    def connect_market(self, client, network):
        """ Connect to the 21market network.
        """
        try:
            zt_device_address = zerotier.device_address()
            response = client.join(network, zt_device_address)
            if response.ok:
                network_id = response.json().get("networkid")
                zerotier.join_network(network_id)
        except exceptions.ServerRequestError as e:
            if e.status_code == 400:
                logger.info(uxstring.UxString.invalid_network)
            else:
                raise e
        except subprocess.CalledProcessError as e:
            logger.info(str(e))

    def _get_market_address(self):
        """ Get status of 21market network connection.

        Returns:
            zt_ip (str): ZeroTier IP address.
        """
        try:
            r = subprocess.check_output(["ifconfig"]).decode()
            zt_ip = Two1Machine.ZEROTIER_IP_PATTERN.search(r).group("ip")
        except Exception:
            return ""
        return zt_ip


class Two1MachineNative(Two1Machine):
    """ Manages the machine layer on Ubuntu/Debian AWS.
    """

    def __init__(self):
        """ Init the AWS Ubuntu/Debian machine layer.
        """
        pass

    def _compute_state(self):
        """ Compute machine state.
        """
        if self.status_networking():
            return MachineState.READY
        else:
            return MachineState.NOREADY

    def status_machine(self):
        """ Get current status of VM
        """
        return VmState.NOEXIST

    def _get_machine_env(self):
        """ Get machine env.
        """
        return dict(os.environ)

    def start_networking(self):
        """ Start ZeroTier daemon.
        """
        if not self.status_zerotier():
            try:
                subprocess.check_output(['sudo', 'service', 'zerotier-one', 'start'],
                                        stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                rv = 1
            else:
                rv = 0
        else:
            rv = 0
        return rv

    def stop_networking(self):
        """ Stop ZeroTier daemon.
        """
        try:
            subprocess.check_output(['sudo', 'service', 'zerotier-one', 'stop'],
                                    stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError as e:
            raise

    def status_networking(self):
        """ Checks if Zerotier is running.
        """
        try:
            subprocess.check_output(['sudo', 'service', 'zerotier-one', 'status'],
                                    stderr=subprocess.DEVNULL)
        except subprocess.CalledProcessError:
            rv = False
        else:
            rv = True
        return rv


class Two1MachineVirtual(Two1Machine):

    # default virtualbox config
    DEFAULT_VM_NAME = "21"
    DEFAULT_VDISK_SIZE = 5000
    DEFAULT_VM_MEMORY = 1024

    @property
    def name(self):
        """ Virtual machine name.
        """
        return self._name

    def __init__(self, machine_name="21"):
        """ Compute machine state and assign state label.
        """
        self._name = machine_name or Two1MachineVirtual.DEFAULT_VM_NAME
        self._state = self._compute_state()

    def _compute_state(self):
        if self.status_networking() and self.status_machine() == VmState.RUNNING:
            return MachineState.READY
        else:
            return MachineState.NOREADY

    # public api

    def start_networking(self):
        """ Start ZeroTier One service.
        """
        if not self.status_networking():
            try:
                subprocess.check_output(["sudo", "launchctl", "load",
                                        "/Library/LaunchDaemons/com.zerotier.one.plist"],
                                        stderr=subprocess.DEVNULL)
                exit_code = 0
            except Exception as e:
                exit_code = 1
        else:
            exit_code = 0
        return exit_code

    def stop_networking(self):
        """ Stop ZeroTier One service.
        """
        try:
            r = subprocess.check_output(["sudo", "launchctl", "unload",
                                         "/Library/LaunchDaemons/com.zerotier.one.plist"])
        except Exception as e:
            print(e)

    def status_networking(self):
        """ Get status of ZeroTier One service.
        """
        try:
            r = subprocess.check_output(['launchctl', 'print', 'system/com.zerotier.one'],
                                        stderr=subprocess.DEVNULL)
        except Exception:
            return False
        return True

    def create_machine(self, vm_name, vdisk_size, vm_memory, service_port, zt_interface):
        """ Driver to create custom VM.
        """
        try:
            subprocess.check_output(["docker-machine", "create",
                                     "--driver", "virtualbox",
                                     "--virtualbox-disk-size", str(vdisk_size),
                                     "--virtualbox-memory", str(vm_memory),
                                     vm_name], stderr=subprocess.DEVNULL)
            subprocess.check_output(["VBoxManage", "controlvm", vm_name, "natpf1",
                                     "tcp-21-sell,tcp,," + str(service_port) +
                                     ",," + str(service_port)])
            subprocess.check_output(["docker-machine", "stop", vm_name])
            subprocess.check_output(["VBoxManage", "modifyvm", vm_name,
                                     "--nic3", "bridged", "--nicpromisc3", "allow-all",
                                     "--bridgeadapter3", zt_interface, "--nictype3", "82540EM"])
            os.makedirs(os.path.dirname(Two1Machine.MACHINE_CONFIG_FILE), exist_ok=True)
            with open(Two1Machine.MACHINE_CONFIG_FILE, "w") as f:
                json.dump({
                    "disk_size": vdisk_size,
                    "vm_memory": vm_memory,
                    "server_port": service_port,
                    "network_interface": zt_interface
                }, f)
            return 0
        except Exception as e:
            raise Two1MachineCreateException()

    def delete_machine(self):
        """ Delete a custom VM.
        """
        if self.status_machine() == VmState.NOEXIST:
            raise Two1MachineDoesNotExist()
        try:
            r = subprocess.check_output(["docker-machine", "rm", "--force", self.name],
                                        stderr=subprocess.DEVNULL)
            return 0
        except Exception as e:
            raise Two1MachineDeleteException()

    def start_machine(self):
        """ Start 21 VM.
        """
        if self.status_machine() == VmState.NOEXIST:
            raise Two1MachineExistException(self.name)
        try:
            if self.status_machine() != VmState.RUNNING:
                r = subprocess.check_output(["docker-machine", "start", self.name],
                                            stderr=subprocess.DEVNULL)
            return 0
        except Exception as e:
            self.stop_machine()
            raise Two1MachineStartException()

    def stop_machine(self):
        """ Stop 21 VM.
        """
        try:
            if self.status_machine() == VmState.RUNNING:
                r = subprocess.check_output(["docker-machine", "stop", self.name],
                                            stderr=subprocess.DEVNULL)
            return 0
        except Exception as e:
            raise Two1MachineStopException()

    def status_machine(self):
        """ Get status of virtual machine.
        """
        try:
            status = subprocess.check_output(["docker-machine", "status",
                                             self.name],
                                             stderr=subprocess.DEVNULL).decode().rstrip()
            if status.lower() == "running":
                return VmState.RUNNING
            elif status.lower() == "stopped":
                return VmState.STOPPED
            else:
                return VmState.UNKNOWN
        except Exception as e:
            return VmState.NOEXIST

    # private methods

    def _get_machine_env(self):
        """ Machine layer environment variables.

        These are used for communication with docker engine.
        """
        machine_env = {}
        try:
            r = subprocess.check_output(["docker-machine", "env", self.name])
            for line in r.decode().split("\n"):
                env_match = Two1MachineVirtual.MACHINE_ENV_PATTERN.search(line)
                if env_match is not None:
                    machine_env[env_match.group("env_key")] = env_match.group("env_value")
            return dict(os.environ, **machine_env)
        except Exception as e:
            raise Two1MachineException()
