# standard python imports
import re
import os
import time
from collections import OrderedDict
from collections import namedtuple

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

    BASE_SERVICES = {"router", "payments", "base"}

    SERVICE_START_TIMEOUT = 10
    SERVICE_PUBLISH_TIMEOUT = 15

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
        """ Start router, payments server, and machine-payable services.
        """

    @abstractmethod
    def stop_services(self, *args):
        """ Stop router, payments server, and machine-payable services.
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

    class ServiceManager:
        """ Query and modify user services persisting at cls.USER_SERVICES_FILE.
        """

        USER_SERVICES_FILE = os.path.join(Two1Composer.BASE_DIR, "user-services.json")

        class Image(namedtuple('Image', 'docker_hub_account repository tag')):

            def _asdict(self):
                # Fixes a bug for Python 3.4 users
                # https://bugs.python.org/issue24931
                'A new OrderedDict mapping field names to their values'
                return OrderedDict(zip(self._fields, self))

            @property
            def is_dockerhub_image(self):
                """ Returns: True iff Image instance has all fields.
                """
                return self.docker_hub_account and self.repository and self.tag

            @property
            def is_local_image(self):
                """ Returns: True iff Image instance doesn't have docker_hub_account but has all other fields.
                """
                return not self.docker_hub_account and self.repository and self.tag

            def __str__(self):
                """ Returns: Docker image name constructed from Image instance fields.
                """
                if self.is_dockerhub_image:
                    return '%s/%s:%s' % (self.docker_hub_account, self.repository, self.tag)
                elif self.is_local_image:
                    return '%s:%s' % (self.repository, self.tag)
                else:
                    raise ValueError()

            @classmethod
            def from_string(cls, image_name):
                """ Constructs an Image instance from a docker image name.

                Args:
                    image_name (str): A docker image name.

                Returns:
                    Image: An Image instance.
                """
                slashes = re.findall('/', image_name)
                colons = re.findall(':', image_name)

                if len(slashes) == 1:
                    if len(colons) == 1 and image_name.find('/') < image_name.find(':'):
                        docker_hub_account, rest = image_name.split('/')
                        repository, tag = rest.split(':')
                        return cls(docker_hub_account=docker_hub_account, repository=repository, tag=tag)
                    elif len(colons) == 0:
                        docker_hub_account, repository = image_name.split('/')
                        return cls(docker_hub_account=docker_hub_account, repository=repository, tag='latest')
                elif len(slashes) == 0:
                    if len(colons) == 1:
                        repository, tag = image_name.split(':')
                        return cls(docker_hub_account=None, repository=repository, tag=tag)
                    elif len(colons) == 0:
                        return cls(docker_hub_account=None, repository=image_name, tag='latest')
                raise ValueError()

        @classmethod
        def get_image(cls, service_name):
            """ Constructs an Image instance for a service.

            Args:
                service_name (str): The name of either a 21 service in the 21dotco/two1 repository or a user service
                                    added to ServiceManager.USER_SERVICES_FILE by ServiceManager.add_service.

            Returns:
                Image: An Image instance corresponding to the given service.
            """
            if service_name in cls.available_21_services():
                return cls.Image(
                    docker_hub_account='21dotco',
                    repository='two1',
                    tag=service_name if service_name in Two1Composer.BASE_SERVICES else 'service-%s' % service_name
                )
            elif service_name in cls.available_user_services():
                return cls.Image(**cls._get_user_service_dict()[service_name])
            else:
                raise ValueError()

        @classmethod
        def available_services(cls):
            """ Returns: All available service names.
            """
            return cls.available_21_services() | cls.available_user_services()

        @classmethod
        def available_21_services(cls):
            """ Returns: All available 21 services by querying Docker Hub.
            """
            service_image_data = requests.get(os.path.join(
                Two1Composer.DOCKERHUB_API_URL, Two1Composer.DOCKERHUB_REPO, 'tags')).json().get('results')
            return set([image_data['name'].split('service-')[1] for image_data in
                        service_image_data if re.match(r'^service-', image_data['name'])])

        @classmethod
        def available_user_services(cls):
            """ Returns: All available user services.
            """
            return set(cls._get_user_service_dict().keys())

        @classmethod
        def add_service(cls, service_name, image_name_string,
                        service_successfully_added_hook, service_already_exists_hook,
                        service_failed_to_add_hook):
            """ Adds a new service definition to ServiceManager.USER_SERVICES_FILE.

            Args:
                service_name (str): Name of the service definition to add.
                image_name_string (str): Docker image name for the service definition.
            """
            service_dict = cls._get_user_service_dict()
            if service_name in service_dict:
                service_already_exists_hook(service_name)
            else:
                service_dict[service_name] = cls.Image.from_string(image_name_string)._asdict()
                if cls._commit_user_service_dict(service_dict):
                    service_successfully_added_hook(service_name)
                else:
                    service_failed_to_add_hook(service_name)

        @classmethod
        def remove_service(cls, service_name,
                           service_successfully_removed_hook,
                           service_does_not_exists_hook,
                           service_failed_to_remove_hook):
            """ Removes a service definition from ServiceManager.USER_SERVICES_FILE.

            Args:
                service_name (str): Name of the service definition to remove.
            """
            service_dict = cls._get_user_service_dict()
            if service_name in service_dict:
                del service_dict[service_name]
                if cls._commit_user_service_dict(service_dict):
                    service_successfully_removed_hook(service_name)
                else:
                    service_failed_to_remove_hook(service_name)
            else:
                service_does_not_exists_hook(service_name)

        @classmethod
        def _get_user_service_dict(cls):
            """ Returns: ServiceManager.USER_SERVICES_FILE as a dict.
            """
            try:
                with open(cls.USER_SERVICES_FILE, 'r') as data_file:
                    service_dict = json.load(data_file)
            except:
                return {}
            else:
                return service_dict

        @classmethod
        def _commit_user_service_dict(cls, service_dict):
            """ Writes a dict of user services to ServiceManager.USER_SERVICES_FILE in json format.

            Args:
                service_dict (dict): A dictionary of user services of the form
                                     {service_name : _as_dict representation of corresponding Image instance..}.

            Returns:
                bool: True iff no exceptions were raised when writing service_dict to ServiceManager.USER_SERVICES_FILE
                      as json.
            """
            try:
                with open(cls.USER_SERVICES_FILE, 'w') as outfile:
                    json.dump(service_dict, outfile)
            except:
                return False
            else:
                return True

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

    # public api
    def connect(self, machine_env, host, machine_config_file):
        """ Connect service composer to machine layer.

        Args:
            machine_env (dict): Environment dictionary for the docker client of the machine layer.
            host (str): Hostname of the machine layer docker daemon.
            machine_config_file (str): Path to the config file for the machine layer.
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
            username (str): Username to log in with.
            password (str): Password to log in with.
            server_port (int): The server port that the router is running on.
            wallet: The wallet to use for the payments server and subsequent services.
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

    def pull_image(self, image,
                   image_sucessfully_pulled_hook, image_failed_to_pull_hook, image_is_local_hook,
                   image_is_malformed_hook):
        """ Pulls an Image instance iff it is a Docker Hub image.

        Args:
            image (Image): An Image instance.
        """
        if image.is_dockerhub_image:
            try:
                self.docker_client.pull('%s/%s' % (image.docker_hub_account, image.repository),
                                        tag=image.tag, stream=False)
            except:
                image_failed_to_pull_hook(image)
            else:
                image_sucessfully_pulled_hook(image)
        elif image.is_local_image:
            image_is_local_hook(image)
        else:
            image_is_malformed_hook(image)

    def start_services(self, service_names,
                       failed_to_start_hook, started_hook, failed_to_restart_hook, restarted_hook, failed_to_up_hook,
                       up_hook):
        """ Start selected services.

        Args:
            service_names (list): List of service names to start.
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
        """
        self._start_sell_service('base', failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)
        self._start_sell_service('router', failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)
        self._start_sell_service('payments', failed_to_start_hook, started_hook, failed_to_up_hook, up_hook)

        self._restart_sell_service('router', failed_to_start_hook, started_hook, failed_to_restart_hook, restarted_hook,
                                   failed_to_up_hook, up_hook)

        # Attempt to start all market services
        for service_name in service_names:
            try:
                image = self.ServiceManager.get_image(service_name)
                container_name = self.service_name_2_container_name(service_name)

                # create nginx routes for service_name
                self._create_service_route(service_name)
                # add service_name to docker compose file
                with self.ComposerYAMLContext() as docker_compose_yaml:
                    username = docker_compose_yaml['services']['payments']['environment']['TWO1_USERNAME']
                    password = docker_compose_yaml['services']['payments']['environment']['TWO1_PASSWORD']
                    mnemonic = docker_compose_yaml['services']['payments']['environment']['TWO1_WALLET_MNEMONIC']
                    docker_compose_yaml['services'][service_name] = {
                        'image': str(image),
                        'container_name': container_name,
                        'depends_on': ['base'],
                        'restart': 'always',
                        'environment': {
                            "TWO1_USERNAME": str(username),
                            "TWO1_PASSWORD": str(password),
                            "TWO1_WALLET_MNEMONIC": str(mnemonic),
                            "SERVICE": str(service_name),
                            "PAYMENT_SERVER_IP":
                                "http://%s:%s" % (self.machine_host, self.machine_config["server_port"])
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
            except:
                # something went wrong while configuring service_name
                failed_to_start_hook(service_name)
            else:
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

    def stop_services(self, service_names,
                      service_found_stopped_and_removed_hook,
                      service_failed_to_stop_hook,
                      service_failed_to_be_removed_hook,
                      service_not_found_hook):
        """ Stop selected services and remove containers.

        Args:
            service_names (set): Set of services to stop.
            service_found_stopped_and_removed_hook (Callable): A callable hook that takes in a service name and is run
                                                               when said service is found, stopped, and removed.
            service_failed_to_stop_hook (Callable): A callable hook that takes in a service name and is run when said
                                                    service fails to be stopped.
            service_failed_to_be_removed_hook (Callable): A callable hook that takes in a service name and is run when
                                                          said service fails to be removed.
            service_not_found_hook (Callable): A callable hook that takes in a service name and is run when said service
                                               isn't found.

        """
        for service_name in service_names:
            if service_name in self.get_running_services():
                container_name = self.service_name_2_container_name(service_name)
                try:
                    self.docker_client.stop(container_name)
                except:
                    service_failed_to_stop_hook(service_name)
                else:
                    try:
                        self.docker_client.remove_container(container_name)
                    except:
                        service_failed_to_be_removed_hook(service_name)
                    else:
                        service_found_stopped_and_removed_hook(service_name)
            else:
                service_not_found_hook(service_name)

    def silently_force_stop_all_services(self):
        running_container_names = self.docker_client.containers(filters={"status": "running"})
        for container_name in running_container_names:
            self.docker_client.remove_container(container_name, force=True)

    @staticmethod
    def container_names_2_service_names(container_definitions):
        """ Return service names from container definitions.

        See service_name_2_container_name for the inverse operation but on one service name.

        Args:
            container_definitions (list): List of container descriptions as returned by self.docker_client.containers.

        Returns:
            set: Set of service names generated by removing the 'sell_' prefix from the containers' names.
        """
        return set([container_definition['Names'][0][6:] for container_definition in container_definitions])

    @staticmethod
    def service_name_2_container_name(service_name):
        """ Generates a container name from a service name by prepending 'sell_'
        """
        return 'sell_%s' % service_name

    def status_services(self, services):
        """ Gets running status of specified services.

        Args:
            services (list): List of services to get status for.
        """

        existent_services = self.get_services(all=True)
        running_services = self.get_services(filters={"status": "running"})
        exited_services = self.get_services(filters={"status": "exited"})

        return {
            "running": running_services & services,
            "exited": exited_services & services,
            "nonexistent": services - existent_services
        }

    def get_services(self, *args, **kwargs):
        """ Call docker_client.containers | convert resulting container names to service names | remove base services
        """
        return self.container_names_2_service_names(
            self.docker_client.containers(*args, **kwargs)
        ) - Two1Composer.BASE_SERVICES

    def get_running_services(self):
        """ Get list of currently running services that aren't 21 base services.

        Returns:
            set: Set of currently running services.
        """
        return self.get_services(filters={"status": "running"})

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
                        "    rewrite ^/" + service + "/?(.*) /$1 break;\n"
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

    def publish_service(self, service_name, host_override, rest_client, published_hook,
                        already_published_hook, failed_to_publish_hook,
                        unknown_publish_error_hook):
        strm, stat = self.docker_client.get_archive('sell_%s' % service_name,
                                                    '/usr/src/app/manifest.yaml')

        with tarfile.open(fileobj=BytesIO(strm.read()), mode='r') as tf:
            manifest = yaml.load(tf.extractfile(stat[u'name']).read().decode())
        manifest['host'] = host_override

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
