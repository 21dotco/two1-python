import asyncio
import codecs
import logging
import time
import cpu_miner
import laminar_message_factory

import gen.laminar_ber as laminar

decode_hex = codecs.getdecoder("hex_codec")

STATE_CONNECT = "connect"
STATE_RECONNECT = "reconnect"
STATE_AUTHORIZE = "authorize"
STATE_HANDLE_MSG = "handle_msg"


class ClientMessageHandler(object):
    def __init__(self, host, port, user, worker):
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

        laminar_obj = laminar.BitsplitAuthRequest(
            version=0,
            uuid=decode_hex(self.user)[0],
            mac=decode_hex(self.worker)[0],
            protocol=0,
            numerator=3,
            denominator=4
        )

        auth_msg = laminar_message_factory.encode_laminar_object(laminar_obj)

        yield from self._send_to_server(auth_msg)
        msg = yield from laminar_message_factory.read_server_message_from_connection(self.reader)
        if not isinstance(msg.value, laminar.AuthReply):
            return STATE_RECONNECT
        data = msg.value
        if isinstance(data.value, laminar.AuthReplyYes):
            self.logger.info('Authentication Successful')
            return STATE_HANDLE_MSG
        elif isinstance(data.value, laminar.AuthReplyNo):
            self.logger.info('Authentication Failed')
            return STATE_RECONNECT
        else:
            return STATE_RECONNECT

    @asyncio.coroutine
    def _state_handle_msg(self):

        msg = yield from laminar_message_factory.read_server_message_from_connection(self.reader)
        data = msg.value
        if isinstance(data, laminar.Notify):
            self._handle_notification(data)
            return STATE_HANDLE_MSG
        elif isinstance(data, laminar.SetDifficulty):
            yield from self._handle_set_difficulty(data)
            return STATE_HANDLE_MSG
        elif isinstance(msg.value, laminar.SubmitReply):
            yield from self._handle_submit_reply(data)
            return STATE_HANDLE_MSG
        else:
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
        laminar_obj = laminar.SubmitRequest(message_id=message_id, jobid=job_id, enonce2=enonce2, otime=otime,
                                            nonce=nonce)

        msg = laminar_message_factory.encode_laminar_object(laminar_obj)
        self.logger.info('Sending Shares to the server %g ',job_id)
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
