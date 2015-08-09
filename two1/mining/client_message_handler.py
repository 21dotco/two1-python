import asyncio
import logging
import time
import cpu_miner

STATE_CONNECT = "connect"
STATE_RECONNECT = "reconnect"
STATE_AUTHORIZE = "authorize"
STATE_HANDLE_MSG = "handle_msg"


class ClientMessageHandler(object):
    def __init__(self, host, port, user, worker, message_factory):
        self._message_factory = message_factory
        self.host = host
        self.port = int(port)
        self.user = user
        self.worker = worker
        self.logger = logging.getLogger(__name__)
        self.cpu_work_master = cpu_miner.CPUWorkMaster()

    @asyncio.coroutine
    def start(self):
        self.state = STATE_CONNECT
        while True:
            method = '_state_%s' % (self.state,)
            self.state = yield from getattr(self, method)()

    def _state_connect(self):
        self.logger.info('Connecting')
        self.reader, self.writer = yield from asyncio.open_connection(host=self.host, port=self.port)
        return STATE_AUTHORIZE

    @asyncio.coroutine
    def _state_reconnect(self):
        self.logger.info('Reconnecting')
        yield from self.writer.close()
        # sleep for a bit before reconnecting - should have better backoff
        time.sleep(3)
        return STATE_CONNECT

    @asyncio.coroutine
    def _state_authorize(self):
        self.logger.info('Authenticating')

        obj = self._message_factory.create_bitsplit_auth_request(
            version=0,
            user=self.user,
            worker=self.worker,
            protocol=0,
            numerator=3,
            denominator=4
        )

        auth_msg = self._message_factory.encode_object(obj)

        yield from self._send_to_server(auth_msg)

        # ignore the auth result for now
        yield from self._message_factory.read_object(self.reader)

        return STATE_HANDLE_MSG

    @asyncio.coroutine
    def _state_handle_msg(self):

        msg = yield from self._message_factory.read_object(self.reader)
        msg_type = msg.value.__class__.__name__
        if msg_type == "Notify":
            self._handle_notification(msg.value)
        return STATE_HANDLE_MSG

    def _handle_notification(self, data):
        self.logger.info('Notification/Work Received')
        event_loop = asyncio.get_event_loop()
        # TODO we need to find a way to gracefully shutdown this thread
        # incase the main loop stops
        self.cpu_work_master.load_work(data, event_loop, self._handle_found)

    @asyncio.coroutine
    def _handle_found(self, share):

        # TODO: not sure what to put for message_id. fix when get info
        yield from self._submit_request_to_server(
            message_id=share.job_id,
            job_id=share.job_id,
            enonce2=share.enonce2,
            otime=share.otime,
            nonce=share.nonce)

    @asyncio.coroutine
    def _handle_set_difficulty(self, data):
        self.logger.info('SetDifficulty Received')

    @asyncio.coroutine
    def _handle_submit_reply(self, data):
        self.logger.info('SubmitReply Received')

    @asyncio.coroutine
    def _submit_request_to_server(self, message_id, job_id, enonce2, otime, nonce):
        """
        """
        try:
            obj = self._message_factory.create_submit_request(
                message_id=message_id,
                job_id=job_id,
                enonce2=enonce2,
                otime=otime,
                nonce=nonce)
        except Exception as e:
            print(e)

        msg = self._message_factory.encode_object(obj)
        self.logger.info('Sending Shares to the server %g ', job_id)
        yield from self._send_to_server(msg)

    @asyncio.coroutine
    def _send_to_server(self, msg):
        """
        sends a laminar encoded message to the server.
        """
        try:
            self.writer.write(msg)
            yield from self.writer.drain()
        except ConnectionResetError:
            raise ConnectionError
