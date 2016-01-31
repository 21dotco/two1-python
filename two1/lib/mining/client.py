"""
Mining client that communicates with the pool.
"""
import logging.config
import asyncio
import argparse

import os
import warnings
from two1.lib.mining.client_message_handler import ClientMessageHandler
from two1.lib.server.message_factory import SwirlMessageFactory
import yaml

logger = logging.getLogger(__name__)

DEFAULT_USER = "corentin"
#DEFAULT_USER = "b6d75d34732d41c096302bb866a36c1e"
DEFAULT_WORKER = "10203"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8008"


def parse():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--user', type=str, default=DEFAULT_USER,
                       help='User connecting, default: ' + DEFAULT_USER)
    parser.add_argument('--worker', default=DEFAULT_WORKER,
                       help='Worker to connect to, default: ' + str(DEFAULT_WORKER))
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                       help='Pool2 hostname to connect to, default: ' + DEFAULT_HOST)
    parser.add_argument('--port', type=str, default=DEFAULT_PORT,
                       help='Port to connect to, default: ' + DEFAULT_PORT)

    return parser.parse_args()


def create_message_handler_task(user_id, worker_id, host, port, message_factory):
    handler = ClientMessageHandler(host, port, user_id, worker_id,
                                   message_factory=message_factory)
    yield from handler.start()


def load_configs():
    # set configs based on the server mode
    TEST_MODE = False
    IS_DEBUG = True

    script_dir = os.path.dirname(__file__)
    log_config_path = os.path.join(script_dir, "logger_config.yaml")
    with open(log_config_path, 'rt') as f:
        config = yaml.load(f.read())

    config["handlers"]["file_handler"]["filename"] = os.path.join(script_dir,
                                                                  "logs/app.log")
    logging.config.dictConfig(config)
    if IS_DEBUG:
        # os.environ['PYTHONASYNCIODEBUG'] = '1'
        # logging.basicConfig(level=logging.DEBUG)
        warnings.filterwarnings("default", category=ResourceWarning, append=True)

    return TEST_MODE
if __name__ == "__main__":
    load_configs()
    args = parse()
    message_factory = SwirlMessageFactory()
    tasks = [
        create_message_handler_task(
            user_id=args.user,
            worker_id=args.worker,
            host=args.host,
            port=args.port,
            message_factory=message_factory),
    ]

    logger.info("Client Started with %d tasks: ", len(tasks))
    asyncio.get_event_loop().run_until_complete(asyncio.wait(tasks))
    logger.warn("Client Shutting down")
