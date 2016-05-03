# standard python imports
import re
import os
import time
import json
import yaml
import random
import requests
import subprocess
from enum import Enum
from abc import ABCMeta
from abc import abstractmethod

# 3rd party imports
from docker import Client
from docker.utils import kwargs_from_env as docker_env

# two1 imports
from two1.wallet import Two1Wallet
from two1.blockchain import TwentyOneProvider
from two1.sell.exceptions.exceptions_composer import *


class ComposerState(Enum):
    """ Composer state label.
    """
    CONNECTED = 1,
    DISCONNECTED = 2


class Two1Composer():
    """ Abstract base composer layer.
    """
    __metaclass__ = ABCMeta

    PRIMARY_WALLET_DIR = os.path.expanduser("~/.two1/wallet")
    PRIMARY_WALLET_FILE = os.path.join(PRIMARY_WALLET_DIR, "default_wallet.json")

    BASE_DIR = os.path.expanduser("~/.two1/services")
    SERVICES_WALLET_FILE = os.path.join(BASE_DIR, "services.json")
    PAYMENTS_WALLET_FILE = os.path.join(BASE_DIR, "payments_wallet.json")
    COMPOSE_FILE = os.path.join(BASE_DIR, "production.yaml")

    BLUEPRINTS_DIR = os.path.join(BASE_DIR, "blueprints")
    SERVICES_DIR = os.path.join(BLUEPRINTS_DIR, "services")
    PAYMENTS_DIR = os.path.join(BLUEPRINTS_DIR, "payments")
    SITES_ENABLED_PATH = os.path.join(BLUEPRINTS_DIR, "router", "sites-enabled")
    SITES_AVAILABLE_PATH = os.path.join(BLUEPRINTS_DIR, "router", "sites-available")

    DEFAULT_INTERNAL_PORT_MIN = 6000
    DEFAULT_INTERNAL_PORT_MAX = 6999

    DEFAULT_WAIT_TIME_STATUS = 60

    BASE_SERVICES = ["router", "payments", "base"]
    GRID_SERVICES = ["ping"]

    @property
    def connected(self):
        return self._connected

    @abstractmethod
    def build_base_services(self):
        """ Build router and payments server images.
        """

    @abstractmethod
    def build_market_services(self):
        """ Build machine-payable service images.
        """

    @abstractmethod
    def start_services(self):
        """ Start router, payments server, and machine-payable
        services.
        """

    @abstractmethod
    def stop_services(self):
        """ Stop router, payments server, and machine-payable
        services.
        """

    @abstractmethod
    def status_services(self):
        """ Get the status of services.
        """

    @abstractmethod
    def status_router(self):
        """ Get the status of the router.
        """

    @abstractmethod
    def status_payments_server(self):
        """ Get the status of the payments server.
        """


class Two1ComposerNative(Two1Composer):
    """ Manage machine-payable microservices natively.
    """

    def __init__(self):
        self._connected = ComposerState.DISCONNECTED
        self.provider = TwentyOneProvider()
        self.default_wallet = Two1Wallet(os.path.expanduser("~/.two1/wallet/default_wallet.json"),
                                         self.provider)

    def connect(self, **kwargs):
        """ Create docker client.
        """
        self.docker_client = Client()
        self._connected = ComposerState.DISCONNECTED


class Two1ComposerContainers(Two1Composer):
    """ Manage machine-payable microservices in containers.
    """

    def __init__(self):
        self._connected = ComposerState.DISCONNECTED
        self.provider = TwentyOneProvider()
        self.default_wallet = Two1Wallet(Two1Composer.PRIMARY_WALLET_FILE,
                                         self.provider)

    # public api

    def connect(self, machine_env, host, machine_config_file):
        """ Connect service composer to machine layer.
        """
        self.machine_env = machine_env
        self.machine_host = host
        with open(machine_config_file, 'r') as f:
            self.machine_config = json.load(f)
        try:
            self.docker_client = Client(**docker_env(assert_hostname=False,
                                                     environment=self.machine_env))
            self._connected = ComposerState.CONNECTED
        except Exception:
            raise Two1ComposerConnectedException()

    def build_base_services(self):
        """ Build router and payment server images.
        """
        # create base service definitions file
        self._create_service_definitions()

        # initialize payments server wallet
        try:
            payments_wallet = self._check_or_create_payments_wallet()
            self._update_payments_wallet_env()
        except Exception:
            raise Two1ComposerWalletException()

        # create route to payments server
        self._create_payments_route()

        # build base services
        services = Two1Composer.BASE_SERVICES
        try:
            cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "build"] + services
            r = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, env=self.machine_env)
        except Exception as e:
            raise Two1ComposerBuildException()

        return payments_wallet

    def build_market_services(self, services):
        """ Build service images and configure routing.
        """
        services = list(set(services).intersection(Two1Composer.GRID_SERVICES))

        # wallet generation/retrieval and restoration
        try:
            wallets = self._check_or_create_wallets(services)
            self._update_wallet_env(services)
        except Exception:
            raise Two1ComposerWalletException()

        # create routes to grid services
        for service in services:
            self._create_service_route(service)

        try:
            cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "build"] + services
            r = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, env=self.machine_env)
        except Exception as e:
            raise Two1ComposerBuildException()

        return wallets

    def write_global_services_env(self, username, password):
        """ Write global service credentials to .env.

        The .env files are passed to the container services.

        """
        os.makedirs(Two1Composer.SERVICES_DIR, exist_ok=True)
        with open(os.path.join(Two1Composer.SERVICES_DIR, ".env"), "w") as f:
            to_write = ("TWO1_USERNAME=%s\n"
                        "TWO1_PASSWORD=%s\n") % (username, password)
            f.write(to_write)

    def start_services(self, services, wait_time_status=25):
        """ Start selected services and generates wallet if nonexistant.

        Args:
            services (list): List of services to start.
            wait_time_status (int): Number of seconds to wait for
                containrs to respond to requests.

        Returns:
            dict: Dictionary with service as key and value as dictionary.
                  Inner dictionary has format {"started": bool, "message": str, "order": int}.

        Raises:

        """
        service_status_dict = {}

        # Attempt to start all services
        for service_count, service in enumerate(sorted(services)):
            service_template = {"started": None,
                                "message": None,
                                "order": None}
            try:
                cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "up", "-d", service]
                r = subprocess.check_output(cmd, stderr=subprocess.DEVNULL,
                                            env=self.machine_env)
                service_template["order"] = service_count
                service_status_dict[service] = service_template
            except Exception as e:
                service_template["started"] = False
                service_template["message"] = "Error starting service."
                service_template["order"] = service_count
                service_status_dict[service] = service_template

        # wait for services to come up
        time.sleep(3)

        # Check if services which did not raise exception started running
        potentially_started_services = [service for service in services
                                        if service_status_dict[service]["started"] is None]

        check_potentially_started = self.status_services(potentially_started_services,
                                                         wait_time_status)

        for service in check_potentially_started:
            service_status_dict[service]["started"] = True if check_potentially_started[service]["status"] == "Running" else False
            service_status_dict[service]["message"] = check_potentially_started[service]["message"]

        # rebuild router image and restart router, start payments server
        self._restart_router()
        self._start_payments_server()

        return service_status_dict

    def stop_services(self, services):
        """ Stop selected services and remove containers.

        Args:
            services (list): List of services to start.

        Returns:
            dict: Dictionary with service as key and value as dictionary.
            Inner dictionary has format {"stopped": bool, "message": str, "order": int}.
        """
        service_status_dict = {}

        containers = self.docker_client.containers(all=True)
        container_names = self._get_services_container_names()

        for service_count, service in enumerate(sorted(services)):
            service_template = {"stopped": None,
                                "message": None,
                                "order": None}

            if service in container_names:
                container_name = container_names[service]
                stopped = False
                try:
                    self.docker_client.stop(container_name)
                    stopped = True
                    if os.path.isfile(os.path.join(Two1Composer.SERVICES_DIR, service, ".env")):
                        os.remove(os.path.join(Two1Composer.SERVICES_DIR, service, ".env"))
                except Exception:
                    service_template["stopped"] = False
                    service_template["message"] = "Unable to stop service."
                    service_template["order"] = service_count
                if stopped:
                    try:
                        self.docker_client.remove_container(container_name)
                        service_template["stopped"] = True
                        service_template["message"] = "Stopped service and removed container."
                        service_template["order"] = service_count
                    except Exception:
                        service_template["stopped"] = False
                        service_template["message"] = "Unable to remove container."
                        service_template["order"] = service_count
            else:
                service_template["stopped"] = True
                service_template["message"] = "Container not found."
                service_template["order"] = service_count

            running_containers = self.docker_client.containers()
            found_running = False
            for container in running_containers:
                if container["Names"][0].strip("/sell_").lower() in [i.lower() for i in
                                                                     self._get_all_services_list()]:
                    found_running = True
                    break
            if not found_running:
                if os.path.isfile(os.path.join(Two1Composer.SERVICES_DIR, ".env")):
                    os.remove(os.path.join(Two1Composer.SERVICES_DIR, ".env"))
            else:
                service_template["stopped"] = True
                service_template["message"] = "21 VM not running."
                service_template["order"] = service_count

            service_status_dict[service] = service_template

        # stop router if all services stopped
        stopped_services = [service for service, description in
                            service_status_dict.items() if description['stopped'] is True]
        if len(stopped_services) == len(service_status_dict.keys()):
            self._stop_router()
        return service_status_dict

    def status_services(self, services, wait_time_status=Two1Composer.DEFAULT_WAIT_TIME_STATUS):
        """ Gets running status of specified services.

        Args:
            services (list): List of services to get status for.
            wait_time_status (int): Number of seconds before container request timeout.

        Returns:
            dict: Dictionary with service as key and value as dictionary.
            Inner dictionary has format: {"status": str, "message": str}.
            "Status" choices are: Not found, Running, Exited, Unable to contact.
        """
        statuses_dict = {}
        containers = self.docker_client.containers(all=True)
        containers_names = [service['Names'][0].strip('/sell_') for service in containers]
        for service in services:
            statuses_dict[service] = {}
            if service not in containers_names:
                statuses_dict[service]["status"] = "Not found"
                statuses_dict[service]["message"] = "Container not found."

        # Check status of services
        end_time = time.time() + wait_time_status
        while time.time() < end_time:

            # Services which have exited
            exited = self.docker_client.containers(filters={"status": "exited"})
            for service in exited:
                service_name = service["Names"][0].strip("/sell_")
                if service_name in services:
                    statuses_dict[service_name]["status"] = "Exited"
                    statuses_dict[service_name]["message"] = service["Status"]

            # Services starting or started
            running = self.docker_client.containers(filters={"status": "running"})
            for service in running:
                service_name = service['Names'][0].strip('/sell_')
                if service_name in services:

                    # Check that service started (responds to HTTP request)
                    running = self._check_running_service(service_name)
                    if running:
                        statuses_dict[service_name]["status"] = "Running"
                        statuses_dict[service_name]["message"] = service["Status"]

            # All services have confirmed value
            all_confirmed = True
            for service in statuses_dict:
                if "status" not in statuses_dict[service].keys():
                    all_confirmed = False
                    break
            if all_confirmed:
                break

        for service in statuses_dict:
            if "status" not in statuses_dict[service].keys():
                statuses_dict[service]["status"] = "Unable to contact"
                statuses_dict[service]["message"] = "Service container still spinning up..."

        return statuses_dict

    def status_router(self):
        """ Get status of Nginx router container.
        """
        router = self.docker_client.containers(all=True, filters={"name": "sell_router"})
        if len(router) == 0:
            status = "Container not found"
        else:
            status = router[0]['State'].title()
        return status

    def status_payments_server(self):
        """ Get status of payment channels server.
        """
        pc_server = self.docker_client.containers(all=True, filters={"name": "sell_payments"})
        if len(pc_server) == 0:
            status = "Container not found"
        else:
            status = pc_server[0]['State'].title()
        return status

    def running_services_exist(self, services):
        """ Check if any services are running.

        Returns: True:  if any micropayments services are running.
                 False: otherwise
        """
        try:
            all_services = self._get_all_services_list()
            if all:
                to_check = all_services
            else:
                to_check = [i for i in services if i in all_services]

            status = self.status_services(to_check)
            running = False
            for service in status:
                if status[service]["status"] == "Running" or \
                   status[service]["status"] == "Unable to contact":
                    running = True
                    break
            return running
        except Two1MachineException as e:
            return False

    # private methods

    def _start_router(self):
        """ Start Nginx router container service.
        """
        try:
            if "router" not in [i["Names"][0].strip("/sell_") for
                                i in self.docker_client.containers()]:
                cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "up", "-d", "router"]
                r = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env=self.machine_env)
        except Exception:
            raise Two1ComposerRouterException()

    def _restart_router(self):
        """ Restart Nginx router container service.
        """
        try:
            cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "build", "router"]
            r = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, env=self.machine_env)
            if "router" in [i["Names"][0].strip("/sell_") for
                            i in self.docker_client.containers()]:
                self.docker_client.stop("sell_router")
            cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "up", "-d", "router"]
            subprocess.check_output(cmd, stderr=subprocess.DEVNULL, env=self.machine_env)
        except Exception:
            raise Two1ComposerRouterException()

    def _stop_router(self):
        """ Stop Nginx router container service.
        """
        try:
            with open(Two1Composer.COMPOSE_FILE, 'r') as f:
                container_name = yaml.load(f)['services']['router']['container_name']
            if "router" in [i["Names"][0].strip("/sell_") for
                            i in self.docker_client.containers()]:
                self.docker_client.stop(container_name)
                self.docker_client.remove_container(container_name)
        except Exception as e:
            raise Two1ComposerRouterException()

    def _start_payments_server(self):
        """ Start payment channels server.
        """
        try:
            if "payments" not in [i["Names"][0].strip("/sell_") for
                                  i in self.docker_client.containers()]:
                cmd = ["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "up", "-d", "payments"]
                r = subprocess.call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                                    env=self.machine_env)
        except Exception as e:
            raise Two1ComposerStartException()

    def _stop_payments_server(self):
        """ Stop payment channels server.
        """
        try:
            with open(Two1Composer.COMPOSE_FILE, 'r') as f:
                container_name = yaml.load(f)['services']['payments']['container_name']
            if "payments" in [i["Names"][0].strip("/sell_") for
                              i in self.docker_client.containers()]:
                self.docker_client.stop(container_name)
                self.docker_client.remove_container(container_name)
        except Exception as e:
            raise Two1ComposerStopException()

    def _check_running_service(self, service_name):
        """ Checks if given service has started by making HTTP request.

        Args:
            service (str): Name of service to test.

        Returns:
            bool: True if service is up.

        NOTE: server.py must be main function of each service.
        """
        # Gets accessible port from docker-compose.yaml
        with open(Two1Composer.COMPOSE_FILE, 'r') as f:
            service_description = yaml.load(f)['services'][service_name]
        if 'expose' in service_description:
            service_ports = str(service_description['expose'][0])
        elif 'ports' in service_description:
            service_ports = str(service_description['ports'][0])
        if service_ports.find(':') != -1:
            service_port = service_ports.split(':')[1]
        else:
            service_port = service_ports

        # construct service url
        port = self.machine_config['server_port']
        url = 'http://%s:%s/%s' % (self.machine_host, port, service_name)

        # make request
        try:
            resp = requests.get(url, timeout=1)
            service_up = True
        except requests.exceptions.ConnectionError as e:
            service_up = False
        except requests.exceptions.Timeout as e:
            service_up = False

        return service_up

    def _check_or_create_wallets(self, services):
        """ Check if wallet exists for each serviecs and generates one if not.

        Args:
            services (list): List of services for which to check/generate wallet.

        Returns:
            dict: Dictionary with service as keys and values as dictionary.
            Inner dictionary has the format: {"existed": bool or None,
            "created": bool or None, "mnemonic": str}

        Raises:
            JSONDecodeError: services.json may be corrupted.
        """

        wallets_dict = {}
        existing_mnemonics_dict = {}

        if os.path.isfile(Two1Composer.SERVICES_WALLET_FILE):
            try:
                with open(Two1Composer.SERVICES_WALLET_FILE, "r") as f:
                    existing_mnemonics_dict = json.load(f)
            except ValueError:
                # services wallet file exists but empty
                if os.path.getsize(Two1Composer.SERVICES_WALLET_FILE) == 0:
                    os.remove(Two1Composer.SERVICES_WALLET_FILE)
                    return self._check_or_create_wallets(services)
                else:
                    raise ValueError("Error: %s may be corrupted." %
                                     Two1Composer.SERVICES_WALLET_FILE)
        else:
            os.makedirs(os.path.dirname(Two1Composer.SERVICES_WALLET_FILE), exist_ok=True)
            with open(Two1Composer.SERVICES_WALLET_FILE, 'w') as f:
                f.write("{}")

        for service in services:
            wallet_template = {"existed": None,
                               "created": None,
                               "mnemonic": None}
            # wallet exists
            if service in existing_mnemonics_dict:
                wallet_template["existed"] = True
                wallet_template["mnemonic"] = existing_mnemonics_dict[service]["mnemonic"]
                wallet_template["port"] = existing_mnemonics_dict[service]["port"]

            # generate new wallet
            else:
                generated_mnemonic = self.default_wallet.create(self.provider)[1]
                selected_port = self._get_unused_port()
                wallet_template["created"] = True
                wallet_template["mnemonic"] = generated_mnemonic
                wallet_template["port"] = selected_port

            wallets_dict[service] = wallet_template

        with open(Two1Composer.SERVICES_WALLET_FILE, "w") as f:
            json.dump({
                service: {
                    "mnemonic": wallets_dict[service]["mnemonic"],
                    "port": wallets_dict[service]["port"]
                } for service in wallets_dict}, f)

        return wallets_dict

    def _check_or_create_payments_wallet(self):
        """ Check if wallet exists for payment server container.

        Returns:
            dict: Dictionary with service as keys and values as dictionary.
            Inner dictionary has the format: {"existed": bool or None,
            "created": bool or None, "mnemonic": str}

        Raises:
            JSONDecodeError: services.json may be corrupted.
        """
        payment_wallet = {"existed": None,
                          "created": None,
                          "mnemonic": None}
        if os.path.isfile(Two1Composer.PAYMENTS_WALLET_FILE):
            try:
                with open(Two1Composer.PAYMENTS_WALLET_FILE, "r") as f:
                    payment_mnemonic = json.load(f)["mnemonic"]
                    payment_wallet["existed"] = True
                    payment_wallet["mnemonic"] = payment_mnemonic
                    return payment_wallet
            except ValueError:
                if os.path.getsize(Two1Composer.PAYMENTS_WALLET_FILE) == 0:
                    os.remove(Two1Composer.PAYMENTS_WALLET_FILE)
                    return self._check_or_create_payments_wallet()
                else:
                    raise ValueError("Error: %s may be corrupted." %
                                     Two1Composer.PAYMENTS_WALLET_FILE)
        else:
            os.makedirs(os.path.dirname(Two1Composer.PAYMENTS_WALLET_FILE), exist_ok=True)
            with open(Two1Composer.PAYMENTS_WALLET_FILE, "w") as f:
                generated_mnemonic = self.default_wallet.create(self.provider)[1]
                json.dump({"mnemonic": generated_mnemonic, "port": 7000}, f)
            payment_wallet["created"] = True
            payment_wallet["mnemonic"] = generated_mnemonic
        return payment_wallet

    def _update_wallet_env(self, services):
        """ Updates the .env file in each service folder with wallet mnemonic.

        Args:
            services (list): List of services for which to update .env.

        Returns:
            int: 0 if .env files all restored successfully
        """
        with open(Two1Composer.SERVICES_WALLET_FILE, "r") as f:
            services_info = json.load(f)

        two1_mnemonic_pattern = re.compile(r"""^(\s*)TWO1_WALLET_MNEMONIC(\s*)=""")
        port_pattern = re.compile(r"""^(\s*)PORT(\s*)=""")
        service_pattern = re.compile(r"""^(\s*)SERVICE(\s*)=""")
        payment_pattern = re.compile(r"""^(\s*)PAYMENT_SERVER_IP(\s*)=""")
        for service in services:
            service_env_file = os.path.join(Two1Composer.SERVICES_DIR,
                                            service,
                                            '.env')

            service_file_lines = []
            if os.path.isfile(service_env_file):
                with open(service_env_file, "r") as f:
                    service_file_lines = [line for line in f.read().split("\n")
                                          if two1_mnemonic_pattern.search(line)
                                          is None or port_pattern.search(line)
                                          is None or service_pattern.search(line)
                                          is None or payment_pattern.search(line)
                                          is None]
            service_file_lines.append("TWO1_WALLET_MNEMONIC=%s" %
                                      services_info[service]["mnemonic"])
            service_file_lines.append("PORT=%s" % services_info[service]["port"])
            service_file_lines.append("SERVICE=%s" % service)
            service_file_lines.append("PAYMENT_SERVER_IP=http://%s:%s" %
                                      (self.machine_host,
                                       self.machine_config["server_port"]))
            os.makedirs(os.path.dirname(service_env_file), exist_ok=True)
            with open(service_env_file, "w") as f:
                f.write("\n".join(service_file_lines))

    def _update_payments_wallet_env(self):
        """ Updates the .env file for payments container.

        Returns:
            int: 0 if .env files all restored successfully
        """
        with open(Two1Composer.PAYMENTS_WALLET_FILE, "r") as f:
            payment_info = json.load(f)

        two1_mnemonic_pattern = re.compile(r"""^(\s*)TWO1_WALLET_MNEMONIC(\s*)=""")
        port_pattern = re.compile(r"""^(\s*)PORT(\s*)=""")
        payment_env_file = os.path.join(Two1Composer.PAYMENTS_DIR, ".env")

        file_lines = []
        if os.path.isfile(payment_env_file):
            with open(payment_env_file, "r") as f:
                file_lines = [line for line in f.read().split("\n")
                              if two1_mnemonic_pattern.search(line)
                              is False or port_pattern.search(line)
                              is False]
        file_lines.append("TWO1_WALLET_MNEMONIC=%s" %
                          payment_info["mnemonic"])
        file_lines.append("PORT=%s" % payment_info["port"])

        os.makedirs(Two1Composer.PAYMENTS_DIR, exist_ok=True)
        with open(payment_env_file, "w") as f:
            f.write("\n".join(file_lines))

    def _get_all_services_list(self):
        """ Get list of available services as defined in docker-composer.yaml

        Returns:
            list: Available services.
        """
        return list(self._get_services_container_names().keys())

    def _get_services_container_names(self):
        """ Maps service folder names to names of container.

        Returns:
            dict: Service folder name as key and container name as value.
        """
        services = {}
        sellables = set(os.listdir(Two1Composer.SERVICES_DIR)).intersection(
            set(Two1Composer.GRID_SERVICES))
        for service in sellables:
            services[service] = "sell_" + service
        return services

    def _get_unused_port(self):
        """ Return a unique port for a service.
        """
        try:
            with open(Two1Composer.SERVICES_WALLET_FILE, "r") as f:
                service_info = json.load(f)
            used_ports = set([service_info[s]['port'] for s in service_info.keys()])
            if set(range(Two1Composer.DEFAULT_INTERNAL_PORT_MIN,
                         Two1Composer.DEFAULT_INTERNAL_PORT_MAX + 1)).issubset(used_ports):
                # all ports in allotted range are used
                raise
            else:
                while(True):
                    service_port = random.randint(Two1Composer.DEFAULT_INTERNAL_PORT_MIN,
                                                  Two1Composer.DEFAULT_INTERNAL_PORT_MAX)
                    if service_port not in used_ports:
                        # todo: try to make socket connection to port inside vm
                        break
            return service_port
        except Exception:
            raise

    def _create_service_definitions(self):
        """ Define boilerplate services, networks, and volumes.

        Args:
            port (int): port for 21 sell server.
        """
        try:
            # create nginx router dirs
            subprocess.check_output(["rm", "-rf",
                                     os.path.join(Two1Composer.SITES_ENABLED_PATH)])
            subprocess.check_output(["rm", "-rf",
                                     os.path.join(Two1Composer.SITES_AVAILABLE_PATH)])
            os.makedirs(Two1Composer.SITES_ENABLED_PATH, exist_ok=True)
            os.makedirs(Two1Composer.SITES_AVAILABLE_PATH, exist_ok=True)

            # create base nginx server
            port = self.machine_config['server_port']
            with open(os.path.join(Two1Composer.SITES_ENABLED_PATH,
                                   "two1baseserver"), 'w') as f:
                f.write("server {\n"
                        "    listen " + str(port) + ";\n"
                        "    include /etc/nginx/sites-available/*;\n"
                        "}\n"
                        )

            # initalize docker compose file
            with open(Two1Composer.COMPOSE_FILE, 'w') as f:
                f.write("version: '2'\n"
                        "services:\n"
                        "  router:\n"
                        "    restart: always\n"
                        "    container_name: sell_router\n"
                        "    build: blueprints/router\n"
                        "    ports:\n"
                        '      - "' + str(port) + ':' + str(port) + '"\n'
                        "    links:\n"
                        "      - payments:payments\n"
                        "    image: two1:router\n"
                        '    command: ["nginx", "-g", "daemon off;"]\n'
                        "  base:\n"
                        "    build: blueprints/base\n"
                        "    image: two1:base\n"
                        )
        except Exception:
            raise Two1ComposerServiceDefinitionException()

    def _create_service_route(self, service):
        """ Create route for container service.
        """
        try:
            # update docker compose file
            with open(Two1Composer.COMPOSE_FILE, 'r') as f:
                two1_services = yaml.load(f)
            service_map = service + ":" + service
            if service_map not in two1_services['services']['router']['links']:
                two1_services['services']['router']['links'].append(service_map)
            two1_services['services'][service] = {}
            two1_services['services'][service]['container_name'] = "sell_" + service
            two1_services['services'][service]['restart'] = "always"
            two1_services['services'][service]['build'] = os.path.join(Two1Composer.SERVICES_DIR,
                                                                       service)
            two1_services['services'][service]['volumes'] = [
                os.path.dirname(Two1Composer.SERVICES_WALLET_FILE) + ":/usr/src/db/"]
            env_dirs = [os.path.join(Two1Composer.SERVICES_DIR, '.env'),
                        os.path.join(Two1Composer.SERVICES_DIR, service, '.env')]
            two1_services['services'][service]['env_file'] = env_dirs
            with open(Two1Composer.SERVICES_WALLET_FILE, 'r') as f:
                service_json = json.load(f)
            two1_services['services'][service]['expose'] = [service_json[service]['port']]
            two1_services['services'][service]['depends_on'] = ['base']
            two1_services['services'][service]['image'] = 'two1:ping'
            two1_services['services'][service]['logging'] = {}
            two1_services['services'][service]['logging']['driver'] = "json-file"
            run_command = 'sh -c "python3 /usr/src/app/login.py && sleep 2 && ' + \
                          'python3 /usr/src/app/server.py"'
            two1_services['services'][service]['command'] = run_command
            with open(Two1Composer.COMPOSE_FILE, 'w') as f:
                f.write(yaml.dump(two1_services, default_flow_style=False))
            # update nginx sites-available
            with open(os.path.join(Two1Composer.SITES_AVAILABLE_PATH, service), 'w') as f:
                f.write("location /" + service + " {\n"
                        "    rewrite ^/" + service + "(.*) $1 break;\n"
                        "    proxy_pass http://" + service + ":" +
                        str(service_json[service]['port']) + ";\n"
                        "    proxy_set_header Host $host;\n"
                        "    proxy_set_header X-Real-IP $remote_addr;\n"
                        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                        "}\n")
        except Exception:
            raise Two1ComposerRouteException()

    def _create_payments_route(self):
        """ Add route to payments server.
        """
        try:

            # link payments server container to router container
            with open(Two1Composer.COMPOSE_FILE, 'r') as f:
                existing = yaml.load(f)
            if "payments:payments" not in existing["services"]["router"]["links"]:
                existing["services"]["router"]["links"].append("payments:payments")

            # write payments server description
            existing["services"]["payments"] = {}
            existing["services"]["payments"]["container_name"] = "sell_payments"
            existing["services"]["payments"]["restart"] = "always"
            existing["services"]["payments"]["build"] = os.path.join(Two1Composer.PAYMENTS_DIR)
            existing["services"]["payments"]["volumes"] = [
                os.path.dirname(Two1Composer.SERVICES_WALLET_FILE) + ":/usr/src/db/"]
            env_dirs = [os.path.join(Two1Composer.SERVICES_DIR, ".env"),
                        os.path.join(Two1Composer.PAYMENTS_DIR, ".env")]
            existing["services"]["payments"]["env_file"] = env_dirs
            with open(Two1Composer.PAYMENTS_WALLET_FILE, "r") as f:
                payments_info = json.load(f)
            existing["services"]["payments"]["expose"] = [payments_info["port"]]
            existing["services"]["payments"]["depends_on"] = ["base"]
            existing["services"]["payments"]["image"] = "two1:payments"
            existing["services"]["payments"]["logging"] = {"driver": "json-file"}
            run_command = 'sh -c "python3 /usr/src/app/login.py && sleep 2 && ' + \
                          'python3 /usr/src/app/server.py"'
            existing["services"]["payments"]["command"] = run_command

            # write docker-compose file
            with open(Two1Composer.COMPOSE_FILE, "w") as f:
                    f.write(yaml.dump(existing, default_flow_style=False))

            # write nginx route for payments server
            with open(os.path.join(Two1Composer.SITES_AVAILABLE_PATH, "payments"), 'w') as f:
                f.write("location /payment {\n"
                        "    proxy_pass http://payments:" + str(payments_info["port"]) + ";\n"
                        "    proxy_set_header Host $host;\n"
                        "    proxy_set_header X-Real-IP $remote_addr;\n"
                        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                        "}\n")

        except Exception:
            raise Two1ComposerRouteException()
