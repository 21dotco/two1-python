from client_task_factory import ClientTaskFactory
import logging.config
import asyncio
import configs
import argparse
from message_factory import ProtobufMessageFactory

configs.load_configs()
logger = logging.getLogger(__name__)

DEFAULT_USER = "b6d75d34732d41c096302bb866a36c1e"
DEFAULT_WORKER = "000000010203"
DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = "8008"


def parse():
    parser = argparse.ArgumentParser(description='Process some integers.')
    parser.add_argument('--user', type=str, default=DEFAULT_USER,
                       help='User connecting, default: ' + DEFAULT_USER)
    parser.add_argument('--worker', default=DEFAULT_WORKER,
                       help='Worker to connect to, default: ' + DEFAULT_WORKER)
    parser.add_argument('--host', type=str, default=DEFAULT_HOST,
                       help='Pool2 hostname to connect to, default: ' + DEFAULT_HOST)
    parser.add_argument('--port', type=str, default=DEFAULT_PORT,
                       help='Port to connect to, default: ' + DEFAULT_PORT)

    return parser.parse_args()

if __name__ == "__main__":
    args = parse()
    message_factory = ProtobufMessageFactory()
    tasks = [
        ClientTaskFactory.create_message_handler_task(
            user_id=args.user,
            worker_id=args.worker,
            host=args.host,
            port=args.port,
            message_factory=message_factory),
    ]

    logger.info("Client Started with %d tasks: ", len(tasks))
    asyncio.get_event_loop().run_until_complete(asyncio.wait(tasks))
    logger.warn("Client Shutting down")