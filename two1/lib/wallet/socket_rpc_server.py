import getpass
import json
import socket
import socketserver

import tempfile
from jsonrpcserver import dispatcher
from jsonrpcserver.request import Request
from jsonrpcserver.response import ErrorResponse
from jsonrpcserver.status import HTTP_STATUS_CODES
from jsonrpcclient.server import Server
from path import Path
from two1.lib.wallet.exceptions import DaemonRunningError
from two1.lib.wallet.exceptions import DaemonNotRunningError


class UnixSocketJSONRPCServer(socketserver.ThreadingMixIn,
                              socketserver.UnixStreamServer):
    TEMP_DIR = Path(tempfile.gettempdir())
    SOCKET_FILE_NAME = TEMP_DIR.joinpath("walletd.%s.sock" % getpass.getuser())

    class JSONRPCHandler(socketserver.BaseRequestHandler):
        """ The RequestHandler class for our server.

            It is instantiated once per connection to the server, and
            must override the handle() method to implement
            communication to the client.
        """

        def handle(self):
            logger = self.server.logger
            while True:
                self.data = self.request.recv(1024).strip().decode()
                if not self.data:
                    break

                try:
                    if self.server._request_cb is not None:
                        self.server._request_cb(self.data)
                    if self.server._client_lock.acquire(True, 10):
                        logger.debug("Dispatching %s" % (self.data))
                        response = dispatcher.dispatch(self.server._methods,
                                                       self.data)
                        logger.debug("Responding with: %s" % response.json_debug)
                        self.server._client_lock.release()
                    else:
                        # Send a time out response
                        r = Request(self.data)
                        logger.debug("Timed out waiting for lock with request = %s" %
                                     (self.data))
                        request_id = r.request_id if hasattr(r, 'request_id') else None
                        response = ErrorResponse(http_status=HTTP_STATUS_CODES[408],
                                                 request_id=request_id,
                                                 code=-32000,  # Server error
                                                 message="Timed out waiting for lock")
                except Exception as e:
                    if logger is not None:
                        logger.exception(e)

                try:
                    self.request.sendall(json.dumps(response.json_debug).encode())
                except BrokenPipeError:
                    break
                except Exception as e:
                    if logger is not None:
                        logger.exception(e)

    def __init__(self, dispatcher_methods, client_lock,
                 request_cb=None, logger=None):
        if self.SOCKET_FILE_NAME.exists():
            # Try connecting to it
            try:
                sock = socket.socket(family=socket.AF_UNIX)
                sock.connect(UnixSocketJSONRPCServer.SOCKET_FILE_NAME)
                raise DaemonRunningError("A daemon is already running.")
            except ConnectionRefusedError:
                self.SOCKET_FILE_NAME.unlink()

        self._methods = dispatcher_methods
        self._client_lock = client_lock
        self._request_cb = request_cb
        self.logger = logger

        super().__init__(self.SOCKET_FILE_NAME,
                         UnixSocketJSONRPCServer.JSONRPCHandler)


class UnixSocketServerProxy(Server):

    def __init__(self):
        # Try connecting to the socket
        self.sock = socket.socket(family=socket.AF_UNIX)
        not_running_msg = "walletd is not running, or the socket is not readable."
        try:
            self.sock.connect(UnixSocketJSONRPCServer.SOCKET_FILE_NAME)
        except FileNotFoundError:
            raise DaemonNotRunningError(not_running_msg)
        except ConnectionRefusedError:
            raise DaemonNotRunningError(not_running_msg)

        super().__init__(UnixSocketJSONRPCServer.SOCKET_FILE_NAME)

    def __getattr__(self, name):
        # Override the getattr to have 'response' default to True

        def attr_handler(*args, **kwargs):
            """Call self.request from here"""
            if kwargs.get('response', True):
                return self.request(name, [dict(args=args, kwargs=kwargs)])
            else:
                return self.notify(name, *args, **kwargs)
        return attr_handler

    def send_message(self, message, expect_reply=True):
        if isinstance(message, str):
            message = message.encode()

        self.sock.sendall(message)

        rv = ""
        if expect_reply:
            reply = self.sock.recv(65536)
            if isinstance(reply, bytes):
                rv = reply.decode()
            else:
                rv = reply

        return rv
