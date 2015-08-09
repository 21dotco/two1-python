from client_task_factory import ClientTaskFactory
import logging.config
import asyncio
import configs
from mining.message_factory import ASNLaminarMessageFactory

configs.load_configs()
logger = logging.getLogger(__name__)

user = 'b6d75d34732d41c096302bb866a36c1e'
worker = '000000010203'
host = '127.0.0.1'
port = '8008'

message_factory = ASNLaminarMessageFactory()
tasks = [
    ClientTaskFactory.create_message_handler_task(user_id=user, worker_id=worker, host=host, port=port,
                                                  message_factory=message_factory),
]

logger.info("Client Started with %d tasks: ", len(tasks))
asyncio.get_event_loop().run_until_complete(asyncio.wait(tasks))
logger.warn("Client Shutting down")
