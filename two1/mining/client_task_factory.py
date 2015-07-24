from client_message_handler import ClientMessageHandler

__author__ = 'Ali'


class ClientTaskFactory:
    """
    Tasks that can be run as part of a client
    """

    @staticmethod
    def create_message_handler_task(user_id, worker_id, host, port):
        handler = ClientMessageHandler(host, port, user_id, worker_id)
        yield from handler.start()

    @staticmethod
    def create_cli_handler_task(self):
        pass

    @staticmethod
    def create_miner_task(self):
        pass
