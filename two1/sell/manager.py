""" Create and manage machine-payable web services.
"""
from two1.sell.machine import Two1Machine, Two1MachineNative, Two1MachineVirtual
from two1.sell.composer import Two1ComposerContainers
from two1.sell.exceptions.exceptions_sell import Two1SellNotSupportedException


def get_manager(sysdata):
    """ Return a manager for the 21 agent.

    Constucts a manager consisting of a platform-dependent
    machine layer and a service composer layer.
    """
    if sysdata.detected_os == "Darwin":
        return Two1Manager(Two1MachineVirtual(), Two1ComposerContainers())
    elif sysdata.detected_os == "Linux" and sysdata.is_supported:
        return Two1Manager(Two1MachineNative(), Two1ComposerContainers())
    else:
        raise Two1SellNotSupportedException


class Two1Manager():
    """ Two1Manager manages the machine and composer layers that make up
    the 21 agent.

    Two1Manager provides an API for creating and managing machine-payable
    microservices.  A pluggable networking layer enables peer discovery on
    the various 21 marketplace networks.

    """

    def __init__(self, machine, composer):
        self.machine = machine
        self.composer = composer

    # machine layer

    def start_networking(self):
        """ Start the pluggable networking layer.
        """
        return self.machine.start_networking()

    def stop_networking(self):
        """ Start the pluggable networking layer.
        """
        return self.machine.stop_networking()

    def status_networking(self):
        """ Start the pluggable networking layer.

        Returns: True if ZeroTier One service is running.
        """
        return self.machine.status_networking()

    def get_market_address(self):
        """ Check if connected to 21market network.
        """
        return self.machine.host

    def get_server_port(self):
        """ Return the 21 server port.
        """
        return self.machine.port

    def connect_market(self, client, network="21market"):
        """ Connect to 21market network.
        """
        return self.machine.connect_market(client, network)

    def create_machine(self, vm_name=Two1MachineVirtual.DEFAULT_VM_NAME,
                       vdisk_size=Two1MachineVirtual.DEFAULT_VDISK_SIZE,
                       vm_memory=Two1MachineVirtual.DEFAULT_VM_MEMORY,
                       service_port=Two1Machine.DEFAULT_SERVICE_PORT,
                       zt_interface=Two1Machine.DEFAULT_ZEROTIER_INTERFACE):
        """ Create the virtual machine.
        """
        return self.machine.create_machine(vm_name, vdisk_size, vm_memory,
                                           service_port, zt_interface)

    def delete_machine(self):
        """ Delete the virtual machine.
        """
        return self.machine.delete_machine()

    def start_machine(self):
        """ Start the virtual machine.
        """
        return self.machine.start_machine()

    def stop_machine(self):
        """ Stop the virtual machine.
        """
        return self.machine.stop_machine()

    def status_machine(self):
        """ Get the virtual machine status.
        """
        return self.machine.status_machine()

    # composer layer

    def build_base_services(self):
        """ Build router and payments server services images.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.build_base_services()

    def build_market_services(self, *args):
        """ Build market services images.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.build_market_services(*args)

    def write_global_services_env(self, *args):
        """ Write global service credentials to .env.
        The .env files are passed to the container services.
        """
        return self.composer.write_global_services_env(*args)

    def start_services(self, *args):
        """ Start services.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.start_services(*args)

    def stop_services(self, *args):
        """ Stop services.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.stop_services(*args)

    def status_router(self):
        """ Get router status.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.status_router()

    def status_services(self, *args):
        """ Get status of all services.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.status_services(*args)

    def running_services_exist(self, *args):
        """ Check if running services exist.
        """
        self.composer.connect(self.machine.env,
                              self.machine.host,
                              self.machine.MACHINE_CONFIG_FILE)
        return self.composer.running_services_exist(*args)

    def get_all_services_list(self):
        """ Returns a list of all availible services.
        Does not require connection to docker engine.
        """
        return self.composer._get_all_services_list()
