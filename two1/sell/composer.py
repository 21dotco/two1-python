# standard python imports
import re
import os
import time
import json
import shutil
import subprocess
from enum import Enum
from abc import ABCMeta
from abc import abstractmethod
import tarfile
import yaml

# 3rd party imports
import requests
from docker import Client
from docker.utils import kwargs_from_env as docker_env

# two1 imports
from io import BytesIO

from two1.wallet import Two1Wallet
from two1.blockchain import TwentyOneProvider
from two1.sell.exceptions import exceptions_composer as exceptions
from two1.sell.util.context import YamlDataContext
from two1.commands.util.exceptions import ServerRequestError


class ComposerState(Enum):
    """ Composer state label.
    """
    CONNECTED = 1,
    DISCONNECTED = 2


class Two1Composer(metaclass=ABCMeta):
    """ Abstract base composer layer.
    """

    DOCKERHUB_API_URL = "https://registry.hub.docker.com/v2/repositories"
    DOCKERHUB_REPO = "21dotco/two1"

    PRIMARY_ACCOUNT_DIR = os.path.expanduser("~/.two1")
    PRIMARY_ACCOUNT_FILE = os.path.join(PRIMARY_ACCOUNT_DIR, "two1.json")

    BASE_DIR = os.path.join(PRIMARY_ACCOUNT_DIR, "services")
    DB_DIR = os.path.join(BASE_DIR, "db_dir")
    os.makedirs(DB_DIR, exist_ok=True)
    SITES_ENABLED_PATH = os.path.join(BASE_DIR, "config", "sites-enabled")
    SITES_AVAILABLE_PATH = os.path.join(BASE_DIR, "config", "sites-available")

    COMPOSE_FILE = os.path.join(BASE_DIR, "21-compose.yaml")

    BASE_SERVICES = ["router", "payments", "base"]

    SERVICE_START_TIMEOUT = 10
    SERVICE_PUBLISH_TIMEOUT = 15

    class ComposerYAMLContext(YamlDataContext):
        """ Context manager for composer YAML service file.
        """

        def __init__(self, username=None, password=None, server_port=None, mnemonic=None):
            self.username = username
            self.password = password
            self.server_port = server_port
            self.mnemonic = mnemonic
            super().__init__(Two1Composer.COMPOSE_FILE)

        def __enter__(self):
            sup = super().__enter__()
            for service in self.data['services']:
                service_definition = self.data['services'][service]
                if 'environment' in service_definition:

                    if 'TWO1_USERNAME' in service_definition['environment'] and self.username is not None:
                        service_definition['environment']['TWO1_USERNAME'] = self.username

                    if 'TWO1_PASSWORD' in service_definition['environment'] and self.password is not None:
                        service_definition['environment']['TWO1_PASSWORD'] = self.password

                    if 'TWO1_WALLET_MNEMONIC' in service_definition['environment'] and self.mnemonic is not None:
                        service_definition['environment']['TWO1_WALLET_MNEMONIC'] = self.mnemonic

                    if 'PAYMENT_SERVER_IP' in service_definition['environment'] and self.server_port is not None:
                        rest = service_definition['environment']['PAYMENT_SERVER_IP'].rsplit(':', maxsplit=1)[-1]
                        service_definition['environment']['PAYMENT_SERVER_IP'] = '%s:%s' % (rest, self.server_port)
            return sup

        def _filler(self):
            """ Create the base service description file.
            """
            return {
                'version': '2',
                'services': {
                    'base': {
                        'image': '%s:base' % Two1Composer.DOCKERHUB_REPO,
                    },
                    'router': {
                        'image': '%s:router' % Two1Composer.DOCKERHUB_REPO,
                        'container_name': 'sell_router',
                        'restart': 'always',
                        'volumes': [
                            Two1Composer.SITES_ENABLED_PATH + ":/etc/nginx/sites-enabled",
                            Two1Composer.SITES_AVAILABLE_PATH + ":/etc/nginx/sites-available",
                        ],
                        'ports': ['%s:%s' % (self.server_port, self.server_port)],
                        'links': [
                            'payments:payments',
                        ],
                    },
                    'payments': {
                        'image': '%s:payments' % Two1Composer.DOCKERHUB_REPO,
                        'depends_on': ['base'],
                        'container_name': 'sell_payments',
                        'restart': 'always',
                        'environment': {
                            "TWO1_USERNAME": str(self.username),
                            "TWO1_PASSWORD": str(self.password),
                            "TWO1_WALLET_MNEMONIC": str(self.mnemonic)
                        },
                        'volumes': [
                            Two1Composer.DB_DIR + ":/usr/src/db/"
                        ],
                        'logging': {
                            'driver': 'json-file'
                        },
                        'cap_drop': [
                            'ALL'
                        ],
                        'cap_add': [
                            'DAC_OVERRIDE',
                            'NET_RAW',
                        ],
                    }
                }
            }

    @property
    def wallet_file(self):
        """ Get the default wallet path.
        """
        try:
            with open(Two1Composer.PRIMARY_ACCOUNT_FILE, 'r') as f:
                account_info = json.load(f)
        except Exception:
            raise
        return account_info.get("wallet_path")

    @abstractmethod
    def start_services(self, *args):
        """ Start router, payments server, and machine-payable
        services.
        """

    @abstractmethod
    def list_services(self):
        """ List all available services.
        """

    @abstractmethod
    def stop_services(self, *args):
        """ Stop router, payments server, and machine-payable
        services.
        """

    @abstractmethod
    def status_services(self, *args):
        """ Get the status of services.
        """

    @abstractmethod
    def status_router(self, *args):
        """ Get the status of the router.
        """

    @abstractmethod
    def status_payments_server(self, *args):
        """ Get the status of the payments server.
        """

    @abstractmethod
    def connect(self, *args, **kwargs):
        """ Connect to the docker client
        """

    @abstractmethod
    def read_server_config(self):
        """Read configuration of server.
        """


class Two1ComposerNative(Two1Composer):
    """ Manage machine-payable microservices natively.
    """

    def __init__(self):
        self._connected = ComposerState.DISCONNECTED
        self.provider = TwentyOneProvider()
        self.default_wallet = Two1Wallet(self.wallet_file,
                                         self.provider)

    def connect(self, *args, **kwargs):
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
        self.default_wallet = Two1Wallet(self.wallet_file, self.provider)

    # public api
    def connect(self, machine_env, host, machine_config_file):
        """ Connect service composer to machine layer.

        Args:
            machine_env (dict): Environment dictionary for the docker client of the machine layer
            host: Hostname of the machine layer docker daemon
            machine_config_file (str): Path to the config file for the machine layer
        """
        self.machine_env = machine_env
        self.machine_host = host
        with open(machine_config_file, 'r') as f:
            self.machine_config = json.load(f)
        self.docker_client = Client(**docker_env(assert_hostname=False,
                                                 environment=self.machine_env))
        self._connected = ComposerState.CONNECTED

    def initialize_server(self, username, password, server_port, wallet=None):
        """ Initialize micropayments server.

        Define boilerplate services, networks, and volumes composer file
        and nginx server config.

        Generates a wallet mnemonic if non-existent.

        Args:
            username (str): Username to log in with
            password (str): Password to log in with
            server_port (int): The server port that the router is running on
            wallet: The wallet to use for the payments server and subsequent services
        """
        self._create_base_server(server_port)  # create base router server config
        self._create_payments_route()  # create route to payments server

        new_wallet = None  # rv[1], not None if mnemonic is replaced in this function

        # generate service description (yaml)
        with self.ComposerYAMLContext(username, password, server_port) as composer_yaml:
            try:
                mnemonic = composer_yaml['services']['payments']['environment']['TWO1_WALLET_MNEMONIC']
                if not mnemonic or mnemonic == str(None):  # if mnemonic is Falsy or uninitialized
                    raise ValueError()
            except (KeyError, ValueError):  # catches if mnemonic is Falsy or doesn't exist in dict tree
                new_machine_wallet = self.default_wallet.create(self.provider)[1]
                composer_yaml['services']['payments']['environment']['TWO1_WALLET_MNEMONIC'] = new_machine_wallet
                new_wallet = new_machine_wallet

        return 0, new_wallet

    def list_services(self):
        """ List available services to sell.
        """
        service_image_data = requests.get(os.path.join(
            Two1Composer.DOCKERHUB_API_URL, Two1Composer.DOCKERHUB_REPO, 'tags')).json().get('results')
        valid_service_names = set([image_data['name'].split('service-')[1] for image_data in
                                   service_image_data if re.match(r'^service-', image_data['name'])])
        return list(valid_service_names)

    def pull_latest_images(self, images):
        """ Pull latest images from 21 DockerHub.

        Args:
            images (list): List of images to pull from the 21 DockerHub.
        """
        for image_tag in images:
            self.docker_client.pull(Two1Composer.DOCKERHUB_REPO, image_tag, stream=False)
        return 0

    def start_services(self, services, failed_to_start_hook, started_hook, failed_to_restart_hook, restarted_hook,
                       failed_to_up_hook, up_hook):
        """ Start selected services.

        Args:
            services (list): List of services to start.
            failed_to_start_hook (Callable): A callable hook that takes in a service name and is run when said service
                                             fails to start.
            started_hook (Callable): A callable hook that takes in a service name and is run when said service starts.
            failed_to_restart_hook (Callable): A callable hook that takes in a service name and is run when said service
                                               fails to restart.
            restarted_hook (Callable): A callable hook that takes in a service name and is run when said service
                                       restarts.
            failed_to_up_hook (Callable): A callable hook that takes in a service name and is run when said service
                                          fails to go up.
            up_hook (Callable): A callable hook that takes in a service name and is run when said service goes up.

        Returns:
            dict: Dictionary with service as key and value as dictionary.
                  Inner dictionary has format {"started": bool, "message": str, "order": int}.

        Raises:

        """
        self._start_sell_service('base', failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)
        self._start_sell_service('router', failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)
        self._start_sell_service('payments', failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)

        self._restart_sell_service('router', failed_to_start_hook, started_hook, failed_to_restart_hook, restarted_hook,
                                   failed_to_up_hook, up_hook)

        # Attempt to start all market services
        for service_name in services:
            # create nginx routes for service_name
            self._create_service_route(service_name)
            # add service_name to docker compose file
            with self.ComposerYAMLContext() as docker_compose_yaml:
                username = docker_compose_yaml['services']['payments']['environment']['TWO1_USERNAME']
                password = docker_compose_yaml['services']['payments']['environment']['TWO1_PASSWORD']
                mnemonic = docker_compose_yaml['services']['payments']['environment']['TWO1_WALLET_MNEMONIC']
                docker_compose_yaml['services'][service_name] = {
                    'image': '%s:%s' % (Two1Composer.DOCKERHUB_REPO, 'service-' + service_name),
                    'container_name': 'sell_%s' % service_name,
                    'depends_on': ['base'],
                    'restart': 'always',
                    'environment': {
                        "TWO1_USERNAME": str(username),
                        "TWO1_PASSWORD": str(password),
                        "TWO1_WALLET_MNEMONIC": str(mnemonic),
                        "SERVICE": str(service_name),
                        "PAYMENT_SERVER_IP": "http://%s:%s" % (self.machine_host, self.machine_config["server_port"])
                    },
                    'volumes': [
                        Two1Composer.DB_DIR + ":/usr/src/db/"
                    ],
                    'logging': {
                        'driver': 'json-file'
                    },
                    'cap_drop': [
                        'ALL'
                    ],
                    'cap_add': [
                        'DAC_OVERRIDE',
                        'NET_RAW',
                    ],
                }
                link_str = '%s:%s' % (service_name, service_name)
                if link_str not in docker_compose_yaml['services']['router']['links']:
                    docker_compose_yaml['services']['router']['links'].append(link_str)

            # attempt to build service_name
            self._start_sell_service(service_name, failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)

        self._restart_sell_service('router', failed_to_start_hook, started_hook, failed_to_restart_hook, restarted_hook,
                                   failed_to_up_hook, up_hook)

    def _start_sell_service(self, service_name, failed_to_start_hook, started_hook, failed_to_up_hook, up_hook,
                            timeout=Two1Composer.SERVICE_START_TIMEOUT):
        try:
            subprocess.check_output(["docker-compose", "-f", Two1Composer.COMPOSE_FILE, "up", "-d", service_name],
                                    stderr=subprocess.DEVNULL, env=self.machine_env)
        except subprocess.CalledProcessError:
            failed_to_start_hook(service_name)
        else:
            started_hook(service_name)
            if service_name == 'router':
                time.sleep(5)
            elif service_name != 'router' and service_name != 'base':
                start = time.clock()

                exec_id = self.docker_client.exec_create('sell_router', "curl %s:5000" % service_name)['Id']
                self.docker_client.exec_start(exec_id)
                running = True

                while time.clock() - start < timeout and running is True:
                    running = self.docker_client.exec_inspect(exec_id)['Running']

                if running is True:
                    failed_to_up_hook(service_name)
                else:
                    up_hook(service_name)

    def _restart_sell_service(self, service_name, failed_to_start_hook, started_hook, failed_to_restart_hook,
                              restarted_hook, failed_to_up_hook, up_hook):
        try:
            self.docker_client.stop("sell_%s" % service_name)
        except:
            is_restart = False
        else:
            is_restart = True

        self._start_sell_service(service_name, failed_to_restart_hook if is_restart else failed_to_start_hook,
                                 restarted_hook if is_restart else started_hook, failed_to_up_hook, up_hook)

    def stop_services(self, services,
                      service_found_stopped_and_removed_hook,
                      service_failed_to_stop_hook,
                      service_failed_to_be_removed_hook,
                      service_not_found_hook):
        """ Stop selected services and remove containers.

        Args:
            services (list): List of services to stop.
            service_found_stopped_and_removed_hook (Callable): A callable hook that takes in a service name and is run
                                                               when said service is found, stopped, and removed.
            service_failed_to_stop_hook (Callable): A callable hook that takes in a service name and is run when said
                                                    service fails to be stopped.
            service_failed_to_be_removed_hook (Callable): A callable hook that takes in a service name and is run when
                                                          said service fails to be removed.
            service_not_found_hook (Callable): A callable hook that takes in a service name and is run when said service
                                               isn't found.

        """
        running_container_names = self.docker_client.containers(filters={"status": "running"})
        for container_name in running_container_names:
            running_service_name = list(self.names_from_containers([container_name]))[0]
            if running_service_name in services:
                try:
                    self.docker_client.stop(container_name)
                except:
                    service_failed_to_stop_hook(running_service_name)
                else:  # container stopped
                    try:
                        self.docker_client.remove_container(container_name)
                    except:
                        service_failed_to_be_removed_hook(running_service_name)
                    else:  # container
                        service_found_stopped_and_removed_hook(running_service_name)

    def silently_force_stop_all_services(self):
        running_container_names = self.docker_client.containers(filters={"status": "running"})
        for container_name in running_container_names:
            self.docker_client.remove_container(container_name, force=True)

    @staticmethod
    def names_from_containers(containers):
        """ Return names from containers.

        Args:
            containers (list): List of containers as returned by self.docker_client.containers
        """
        return frozenset([service['Names'][0][6:] for service in containers])

    def status_services(self, services,
                        service_nonexistent_hook,
                        service_running_hook,
                        service_exited_hook,
                        service_unknown_state_hook):
        """ Gets running status of specified services.

        Args:
            services (list): List of services to get status for.
            service_nonexistent_hook (Callable): A callable hook that takes in a service name and is run when said
                                                 service is non-existent.
            service_running_hook (Callable): A callable hook that takes in a service name and is run when said service
                                             is running.
            service_exited_hook (Callable): A callable hook that takes in a service name and is run when said service
                                            has exited.
            service_unknown_state_hook (Callable): A callable hook that takes in a service name and is run when said
                                                   service is in an unknown state.
        Returns:
            dict: Dictionary with service as key and value as dictionary.
            Inner dictionary has format: {"status": str, "message": str}.
            "Status" choices are: Not found, Running, Exited, Unable to contact.
        """

        existent_services = self.names_from_containers(self.docker_client.containers(all=True))
        running_services = self.names_from_containers(self.docker_client.containers(filters={"status": "running"}))
        exited_services = self.names_from_containers(self.docker_client.containers(filters={"status": "exited"}))

        for service_name in services:
            if service_name in running_services:
                service_running_hook(service_name)
            elif service_name in exited_services:
                service_exited_hook(service_name)
            elif service_name in existent_services:
                service_unknown_state_hook(service_name)
            else:
                service_nonexistent_hook(service_name)

    def get_running_services(self):
        """ Get list of running services.

        Returns:
            (list) started services
        """
        return list(set(self.names_from_containers(self.docker_client.containers(
            filters={"status": "running"}))).difference(set(Two1Composer.BASE_SERVICES)))

    def status_router(self, service_running_hook, service_unknown_state_hook):
        """ Get status of Nginx router container.

        Args:
            service_running_hook (Callable): A callable hook that takes in a service name and is run when said service
                                             is running.
            service_unknown_state_hook (Callable): A callable hook that takes in a service name and is run when said
                                                   service is in an unknown state.
        """
        if len(self.docker_client.containers(all=True, filters={"name": "sell_router", "status": "running"})) == 1:
            service_running_hook("router")
        else:
            service_unknown_state_hook("router")

    def status_payments_server(self, service_running_hook, service_unknown_state_hook):
        """ Get status of payment channels server.

        Args:
            service_running_hook (Callable): A callable hook that takes in a service name and is run when said service
                                             is running.
            service_unknown_state_hook (Callable): A callable hook that takes in a service name and is run when said
                                                   service is in an unknown state.
        """
        if len(self.docker_client.containers(all=True, filters={"name": "sell_payments", "status": "running"})) == 1:
            service_running_hook("payments")
        else:
            service_unknown_state_hook("payments")

    @staticmethod
    def _create_base_server(server_port):
        """ Create nginx base server config.

        Args:
            server_port (int): port for 21 sell server.
        """
        try:
            # create nginx router dirs
            shutil.rmtree(Two1Composer.SITES_ENABLED_PATH, ignore_errors=True)
            shutil.rmtree(Two1Composer.SITES_AVAILABLE_PATH, ignore_errors=True)
            os.makedirs(Two1Composer.SITES_ENABLED_PATH, exist_ok=True)
            os.makedirs(Two1Composer.SITES_AVAILABLE_PATH, exist_ok=True)

            # create base nginx server
            with open(os.path.join(Two1Composer.SITES_ENABLED_PATH,
                                   "two1baseserver"), 'w') as f:
                f.write("server {\n"
                        "    listen " + str(server_port) + ";\n"
                        "    include /etc/nginx/sites-available/*;\n"
                        "}\n"
                        )
        except Exception:
            raise exceptions.Two1ComposerServiceDefinitionException()

    @staticmethod
    def _create_service_route(service):
        """ Create route for container service.
        """
        os.makedirs(Two1Composer.SITES_AVAILABLE_PATH, exist_ok=True)
        try:
            with open(os.path.join(Two1Composer.SITES_AVAILABLE_PATH, service), 'w') as f:
                f.write("location /" + service + " {\n"
                        "    rewrite ^/" + service + "(.*) /$1 break;\n"
                        "    proxy_pass http://" + service + ":" + str(5000) + ";\n"
                        "    proxy_set_header Host $host;\n"
                        "    proxy_set_header X-Real-IP $remote_addr;\n"
                        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                        "}\n")
        except Exception:
            raise exceptions.Two1ComposerRouteException()

    @staticmethod
    def _create_payments_route():
        """ Add route to payments server.
        """
        os.makedirs(Two1Composer.SITES_AVAILABLE_PATH, exist_ok=True)
        try:
            # write nginx route for payments server
            with open(os.path.join(Two1Composer.SITES_AVAILABLE_PATH, "payments"), 'w') as f:
                f.write("location /payment {\n"
                        "    proxy_pass http://payments:" + str(5000) + ";\n"
                        "    proxy_set_header Host $host;\n"
                        "    proxy_set_header X-Real-IP $remote_addr;\n"
                        "    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;\n"
                        "}\n")
        except Exception:
            raise exceptions.Two1ComposerRouteException()

    def publish_service(self, service_name, rest_client, published_hook, already_published_hook, failed_to_publish_hook,
                        unknown_publish_error_hook):
        strm, stat = self.docker_client.get_archive('sell_%s' % service_name, '/usr/src/app/manifest.yaml')

        with tarfile.open(fileobj=BytesIO(strm.read()), mode='r') as tf:
            manifest = yaml.load(tf.extractfile(stat[u'name']).read().decode())

        try:
            resp = rest_client.publish({"manifest": manifest,
                                        "marketplace": "21mkt"})
        except ServerRequestError as e:
            if e.status_code == 403 and e.data.get("error") == "TO600":
                already_published_hook(service_name)
            else:
                failed_to_publish_hook(service_name)
        except:
            unknown_publish_error_hook(service_name)
        else:
            if resp.status_code == 201:
                published_hook(service_name)
            else:
                failed_to_publish_hook(service_name)

    def read_server_config(self):
        try:
            with open(Two1Composer.COMPOSE_FILE) as f:
                return yaml.load(f)

        except FileNotFoundError:
            return {}

    def get_services_mnemonic(self):
        if os.path.isfile(Two1Composer.COMPOSE_FILE):
            with self.ComposerYAMLContext() as composer_yaml:
                try:
                    maybe_mnemonic = composer_yaml['services']['payments']['environment']['TWO1_WALLET_MNEMONIC']
                except KeyError:
                    rv = None
                else:
                    rv = maybe_mnemonic
        else:
            rv = None
        return rv
