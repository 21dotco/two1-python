"""
Encode and send to server. Receive and parse messages from server.
"""
import asyncio
import logging

import cpu_miner

STATE_CONNECT = "connect"
STATE_DISCONNECT = "connect"
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

    @asyncio.coroutine
    def start(self):
        self.state = STATE_CONNECT
        while True:
            method = '_state_%s' % (self.state,)
            self.state = yield from getattr(self, method)()
            if self.state == STATE_DISCONNECT:
                return

    def _state_connect(self):
        self.logger.info('Connecting')
        self.reader, self.writer = yield from asyncio.open_connection(host=self.host,
                                                                      port=self.port)
        return STATE_AUTHORIZE

    @asyncio.coroutine
    def _state_authorize(self):
        self.logger.info('Authenticating')

        auth_msg = self._message_factory.create_auth_request(
            username=self.user,
            uuid=self.worker,
        )

        yield from self._send_to_server(auth_msg)

        # ignore the auth result for now
        auth_msg = yield from self._message_factory.read_object_async(self.reader)
        auth_type = auth_msg.WhichOneof("authreplies")
        auth_resp = getattr(auth_msg, auth_type)

        if auth_type == 'auth_reply_yes':
            self.logger.info('Auth Success')
            enonce1 = auth_resp.enonce1
            enonce2_size = auth_resp.enonce2_size
            self.cpu_work_master = cpu_miner.CPUWorkMaster(enonce1, enonce2_size)

            return STATE_HANDLE_MSG
        elif auth_type == 'auth_reply_no':
            self.logger.info('Auth Failed. error=%s', auth_resp.error)
            return STATE_DISCONNECT


    @asyncio.coroutine
    def _state_handle_msg(self):

        msg = yield from self._message_factory.read_object_async(self.reader)
        msg_type = msg.__class__.__name__
        if msg_type == "WorkNotification":
            self._handle_notification(msg)
        return STATE_HANDLE_MSG

    def _handle_notification(self, data):
        self.logger.info('Work Notification Received')
        event_loop = asyncio.get_event_loop()
        # TODO we need to find a way to gracefully shutdown this thread
        # incase the main loop stops
        self.cpu_work_master.load_work(data, event_loop, self._handle_found)

    @asyncio.coroutine
    def _handle_found(self, share):

        # TODO: not sure what to put for message_id. fix when get info
        yield from self._submit_request_to_server(
            message_id=share.work_id,
            work_id=share.work_id,
            enonce2=share.enonce2,
            otime=share.otime,
            nonce=share.nonce)

    @asyncio.coroutine
    def _handle_submit_reply(self, data):
        self.logger.info('SubmitReply Received')

    @asyncio.coroutine
    def _submit_request_to_server(self, message_id, work_id, enonce2, otime, nonce):
        """
        """
        msg = self._message_factory.create_submit_share_request(
            message_id=message_id,
            work_id=work_id,
            enonce2=enonce2,
            otime=otime,
            nonce=nonce)

        self.logger.info('Sending Shares to the server %g ', work_id)
        yield from self._send_to_server(msg)

    @asyncio.coroutine
    def _send_to_server(self, msg):
        """
        sends a swirl encoded message to the server.
        """
        try:
            self.writer.write(msg)
            yield from self.writer.drain()
        except ConnectionResetError:
            raise ConnectionError
