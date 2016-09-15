# standard python imports
import os
import re
import json
import time
import subprocess
import logging
from enum import Enum
from abc import ABCMeta
from abc import abstractmethod

# two1 imports
from two1.commands.util import zerotier
from two1.commands.util import exceptions
from two1.commands.util import uxstring
from two1.sell.exceptions import exceptions_machine

logger = logging.getLogger(__name__)


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


class Two1Machine:
    """ Abstract base machine layer.
    """
    __metaclass__ = ABCMeta

    DEFAULT_ZEROTIER_INTERFACE = "zt0"
    DEFAULT_SERVICE_PORT = 8080

    ZEROTIER_CLI_IPV6_PATTERN = re.compile(r"""(\w{4}:){7}\w{4}""")
    MACHINE_ENV_PATTERN = re.compile(r'''^export(\s*)(?P<env_key>\w*)(\s*)=(\s*)"(?P<env_value>.*)"''')
    MACHINE_CONFIG_FILE = os.path.expanduser("~/.two1/services/config/machine_config.json")
    MACHINE_CONFIG_DIR = os.path.dirname(MACHINE_CONFIG_FILE)

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
            raise

    @abstractmethod
    def env(self):
        """ Machine layer environment.
        """

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
    def status_docker(self):
        """ Get docker status.
        """

    @abstractmethod
    def status_networking(self):
        """ Get network status.
        """

    @abstractmethod
    def _compute_state(self):
        """ Compute machine state label.
        """

    @abstractmethod
    def connect_market(self, client, network):
        """ Connect to the 21mkt network.

        Args:
            client: Client to join network
            network: Network to join
        """

    @abstractmethod
    def _get_market_address(self):
        """ Get status of 21mkt network connection.

        Returns:
            zt_ip (str): ZeroTier IP address.
        """

    def create_machine(self, vm_name, vdisk_size, vm_memory, service_port):
        """ Driver to create custom VM.

        Args:
            vm_name: Name of the VM to create.
            vdisk_size: Size of disk for the VM in MB.
            vm_memory: Size of memory for the VM in MB
            service_port: Port on which the router container will listen.
        """
        pass

    def delete_machine(self):
        """ Delete the virtual machine.
        """
        pass

    def start_machine(self):
        """ Start the virtual machine.
        """
        pass

    def stop_machine(self):
        """ Stop the virtual machine.
        """
        pass

    def status_machine(self):
        """ Get the virtual machine status.
        """
        pass

    def write_machine_config(self, server_port):
        os.makedirs(os.path.dirname(self.MACHINE_CONFIG_FILE), exist_ok=True)
        with open(self.MACHINE_CONFIG_FILE, "w") as f:
            json.dump(server_port, f)

    def read_machine_config(self):
        try:
            with open(self.MACHINE_CONFIG_FILE, "r") as f:
                return json.load(f)
        except FileNotFoundError:
            return {}


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

    def status_docker(self):
        """ Get current status of docker
        """
        rv = False
        try:
            output = subprocess.check_output(['ps', '-A']).decode()
            rv = "docker" in output
        except subprocess.CalledProcessError:
            pass
        return rv

    def env(self):
        """ Get machine env.
        """
        return dict(os.environ)

    def start_docker(self):
        """ Start docker daemon."""
        rv = False
        if not self.status_docker():
            try:
                subprocess.check_output(["sudo", "service", "docker", "start"], stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                rv = False
        return rv

    def start_networking(self):
        """ Start ZeroTier daemon.
        """
        if not self.status_networking():
            try:
                subprocess.Popen(['sudo', 'service', 'zerotier-one', 'start'], stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError:
                return 1
            else:
                now = time.time()

                while time.time() <= now + 60:
                    if self.status_networking():
                        return 0

                return 1
        else:
            return 0

    def stop_networking(self):
        """ Stop ZeroTier daemon.
        """
        subprocess.check_output(['sudo', 'service', 'zerotier-one', 'stop'], stderr=subprocess.DEVNULL)

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

    def connect_market(self, client, network):
        """ Connect to the 21market network.

        Args:
            client: Client to join network
            network: Network to join
        """
        try:
            zt_device_address = zerotier.device_address()
            response = client.join(network, zt_device_address)
            if response.ok:
                network_id = response.json().get("networkid")
                zerotier.join_network(network_id)
                if self.wait_for_zt_confirmation():
                    pass
        except exceptions.ServerRequestError as e:
            if e.status_code == 400:
                logger.info(uxstring.UxString.invalid_network)
            else:
                raise e
        except subprocess.CalledProcessError as e:
            logger.info(str(e))
        time.sleep(10)  # wait for interface to come up

    def wait_for_zt_confirmation(self):
        now = time.time()
        while time.time() <= now + 10:
            try:
                networks = json.loads(subprocess.check_output(["sudo", "zerotier-cli", "listnetworks", "-j"]).decode())
                for network in networks:
                    if network["name"] == "21mkt" and network["status"] == "OK":
                        return True
            except subprocess.CalledProcessError:
                pass
            except ValueError:
                pass
        return False

    def _get_market_address(self):
        """ Get status of 21mkt network connection.

        Returns:
            zt_ip (str): ZeroTier IP address.
        """
        try:
            zt_conf = subprocess.check_output(["sudo", "zerotier-cli", "listnetworks", "-j"])
            if type(zt_conf) == bytes:
                zt_conf = zt_conf.decode()
            zt_conf_json = json.loads(zt_conf)
            for net in zt_conf_json:
                if net["name"] == "21mkt":
                    if net["status"] == "OK":
                        ip_addrs = net["assignedAddresses"]
                        for addr in ip_addrs:
                            potential_match = Two1Machine.ZEROTIER_CLI_IPV6_PATTERN.search(addr)
                            if potential_match is not None:
                                return "[%s]" % potential_match.group(0)
                        return ""
                    else:
                        return ""
            return ""
        except Exception:
            return ""


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
        if self.status_machine() == VmState.RUNNING and self.status_networking():
            return MachineState.READY
        else:
            return MachineState.NOREADY

    # public api

    def status_docker(self):
        """ Get docker status."""
        pass

    def start_docker(self):
        """ Get docker status."""
        pass

    def start_networking(self):
        """ Start ZeroTier One service.
        """
        if not self.status_networking():
            restored_config = False
            if "zerotier_conf" in os.listdir(os.path.expanduser("~/.two1/services")):
                subprocess.check_output(["docker-machine",
                                         "scp",
                                         "-r",
                                         os.path.expanduser("~/.two1/services/zerotier_conf"),
                                         "21:~/zerotier_conf"])
                self.docker_ssh(("sudo chmod 755 zerotier_conf; "
                                 "sudo chmod 600 zerotier_conf/authtoken.secret zerotier_conf/identity.secret; "
                                 "sudo chmod 644 zerotier_conf/identity.public "
                                 "zerotier_conf/zerotier-one.pid zerotier_conf/zerotier-one.port"),
                                stderr=subprocess.DEVNULL)
                if "zerotier-one" in self.docker_ssh("ls /var/lib", stderr=subprocess.DEVNULL).decode().split("\n"):
                    self.docker_ssh("sudo rm -rf /var/lib/zerotier-one", stderr=subprocess.DEVNULL)
                self.docker_ssh("sudo mv zerotier_conf /var/lib/zerotier-one", stderr=subprocess.DEVNULL)
                restored_config = True

            try:
                subprocess.check_output(["docker-machine", "scp",
                                         os.path.join(
                                             os.path.dirname(os.path.abspath(__file__)),
                                             "util",
                                             "scripts",
                                             "zerotier_installer.sh"),
                                         "21:~/zerotier_installer.sh"],
                                        stderr=subprocess.DEVNULL)
                self.docker_ssh("chmod a+x zerotier_installer.sh", stderr=subprocess.DEVNULL)
                self.docker_ssh("sudo ./zerotier_installer.sh",
                                api=subprocess.Popen,
                                stdout=subprocess.DEVNULL,
                                stderr=subprocess.DEVNULL)
            except:
                return 1
            else:
                now = time.time()
                found_nets = False

                while time.time() <= now + 60:
                    if self.status_networking():
                        found_nets = True
                        break

                if found_nets:
                    if restored_config is False:
                        try:
                            self.docker_ssh("sudo cp -r /var/lib/zerotier-one ~/zerotier_conf",
                                            stderr=subprocess.DEVNULL)
                            self.docker_ssh("sudo chmod -R 770 ~/zerotier_conf", stderr=subprocess.DEVNULL)
                            subprocess.check_output(["docker-machine",
                                                     "scp",
                                                     "-r",
                                                     "21:~/zerotier_conf",
                                                     os.path.expanduser("~/.two1/services/zerotier_conf")])
                        except:
                            return 1
                        else:
                            return 0
                    else:
                        return 0
                else:
                    return 1

        else:
            return 0

    def stop_networking(self):
        """ Stop ZeroTier One service.
        """
        pass

    def status_networking(self):
        """ Get status of ZeroTier One service.
        """
        try:
            if "ps_zerotier.sh" not in self.docker_ssh("ls", stderr=subprocess.DEVNULL).decode().split("\n"):
                subprocess.check_output(["docker-machine",
                                         "scp",
                                         os.path.join(
                                             os.path.dirname(os.path.abspath(__file__)),
                                             "util",
                                             "scripts",
                                             "ps_zerotier.sh"),
                                         "21:~/ps_zerotier.sh"])
            self.docker_ssh("chmod a+x ~/ps_zerotier.sh", stderr=subprocess.DEVNULL)
            processes = self.docker_ssh("./ps_zerotier.sh", stderr=subprocess.DEVNULL).decode().split("\n")
            for process in processes:
                if process.find("zerotier-one -d") != -1:
                    return True
            return False
        except subprocess.CalledProcessError:
            return False

    def connect_market(self, client, market):
        try:
            zt_device_address = json.loads(self.docker_ssh("sudo ./zerotier-cli info -j",
                                                           stderr=subprocess.DEVNULL).decode())["address"]
            response = client.join(market, zt_device_address)
            if response.ok:
                network_id = response.json().get("networkid")
                self.docker_ssh("sudo ./zerotier-cli join %s" % network_id, stderr=subprocess.DEVNULL)
                if self.wait_for_zt_confirmation():
                    pass
        except exceptions.ServerRequestError as e:
            if e.status_code == 400:
                logger.info(uxstring.UxString.invalid_network)
            else:
                raise e
        except subprocess.CalledProcessError as e:
            logger.info(str(e))
        time.sleep(10)  # wait for interface to come up
        return

    def wait_for_zt_confirmation(self):
        now = time.time()
        while time.time() <= now + 10:
            try:
                networks = json.loads(self.docker_ssh("sudo ./zerotier-cli listnetworks -j",
                                                      stderr=subprocess.DEVNULL).decode())
                for network in networks:
                    if network["name"] == "21mkt" and network["status"] == "OK":
                        return True
            except subprocess.CalledProcessError:
                pass
            except ValueError:
                pass
        return False

    def _get_market_address(self):
        """ Get status of 21mkt network connection.

        Returns:
            zt_ip (str): ZeroTier IP address.
        """
        try:
            zt_conf = self.docker_ssh("sudo ./zerotier-cli listnetworks -j", stderr=subprocess.DEVNULL)
            if type(zt_conf) == bytes:
                zt_conf = zt_conf.decode()
            zt_conf_json = json.loads(zt_conf)
            for net in zt_conf_json:
                if net["name"] == "21mkt":
                    if net["status"] == "OK":
                        ip_addrs = net["assignedAddresses"]
                        for addr in ip_addrs:
                            potential_match = Two1Machine.ZEROTIER_CLI_IPV6_PATTERN.search(addr)
                            if potential_match is not None:
                                return "[%s]" % potential_match.group(0)
                        return ""
                    else:
                        return ""
            return ""
        except Exception:
            return ""

    def create_machine(self, vm_name, vdisk_size, vm_memory, service_port):
        """ Driver to create custom VM.

        Args:
            vm_name: Name of the VM to create.
            vdisk_size: Size of disk for the VM in MB.
            vm_memory: Size of memory for the VM in MB
            service_port: Port on which the router container will listen.
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
            os.makedirs(os.path.dirname(Two1Machine.MACHINE_CONFIG_FILE), exist_ok=True)
            with open(Two1Machine.MACHINE_CONFIG_FILE, "w") as f:
                json.dump({
                    "disk_size": vdisk_size,
                    "vm_memory": vm_memory,
                    "server_port": service_port
                }, f)
            return 0
        except:
            raise exceptions_machine.Two1MachineCreateException()

    def delete_machine(self):
        """ Delete a custom VM.
        """
        if self.status_machine() == VmState.NOEXIST:
            raise exceptions_machine.Two1MachineDoesNotExist()
        try:
            subprocess.check_output(["docker-machine", "rm", "--force", self.name], stderr=subprocess.DEVNULL)
            return 0
        except:
            raise exceptions_machine.Two1MachineDeleteException()

    def start_machine(self):
        """ Start 21 VM.
        """
        if self.status_machine() == VmState.NOEXIST:
            raise exceptions_machine.Two1MachineExistException(self.name)
        try:
            if self.status_machine() != VmState.RUNNING:
                subprocess.check_output(["docker-machine", "start", self.name], stderr=subprocess.DEVNULL)
            return 0
        except:
            self.stop_machine()
            raise exceptions_machine.Two1MachineStartException()

    def stop_machine(self):
        """ Stop 21 VM.
        """
        try:
            if self.status_machine() == VmState.RUNNING:
                subprocess.check_output(["docker-machine", "stop", self.name], stderr=subprocess.DEVNULL)
            return 0
        except:
            raise exceptions_machine.Two1MachineStopException()

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
        except:
            return VmState.NOEXIST

    # private methods
    def env(self):
        """ Machine layer environment variables.

        These are used for communication with docker engine.
        """
        machine_env = {}
        try:
            r = subprocess.check_output(["docker-machine", "env", "--shell", "bash", self.name])
            for line in r.decode().split("\n"):
                env_match = Two1MachineVirtual.MACHINE_ENV_PATTERN.search(line)
                if env_match is not None:
                    machine_env[env_match.group("env_key")] = env_match.group("env_value")
            environ = os.environ.copy()
            environ.update(machine_env)
            return environ
        except:
            raise exceptions_machine.Two1MachineException()

    def docker_ssh(self, cmd, api=subprocess.check_output, **kwargs):
        try:
            return api(["docker-machine", "ssh", "21", cmd], **kwargs)
        except Exception as e:
            raise e
