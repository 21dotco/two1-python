import json
import socket
import socketserver

import tempfile
from jsonrpcserver import dispatcher
from jsonrpcclient.server import Server
from path import Path
from two1.lib.wallet.exceptions import DaemonNotRunningError


class UnixSocketJSONRPCServer(socketserver.UnixStreamServer):
    TEMP_DIR = Path(tempfile.gettempdir())
    SOCKET_FILE_NAME = TEMP_DIR.joinpath("walletd.sock")

    class JSONRPCHandler(socketserver.BaseRequestHandler):
        """ The RequestHandler class for our server.

            It is instantiated once per connection to the server, and
            must override the handle() method to implement
            communication to the client.
        """

        def handle(self):
            self.data = self.request.recv(1024).strip().decode()
            try:
                response = dispatcher.dispatch(self.server._methods, self.data)
            except Exception as e:
                print("Do something with this: %s" % e)
                raise

            try:
                self.request.sendall(json.dumps(response.json).encode())
            except BrokenPipeError:
                pass
            except Exception as e:
                print("Unable to send response. Error: %s" % e)

    def __init__(self, dispatcher_methods):
        if self.SOCKET_FILE_NAME.exists():
            self.SOCKET_FILE_NAME.unlink()

        self._methods = dispatcher_methods

        super().__init__(self.SOCKET_FILE_NAME,
                         UnixSocketJSONRPCServer.JSONRPCHandler)


class UnixSocketServerProxy(Server):

    def __init__(self):
        # Try connecting to the socket
        s = socket.socket(family=socket.AF_UNIX)
        not_running_msg = "walletd is not running, or the socket is not readable."
        try:
            s.connect(UnixSocketJSONRPCServer.SOCKET_FILE_NAME)
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
                return self.request(name, *args, **kwargs)
            else:
                return self.notify(name, *args, **kwargs)
        return attr_handler

    def send_message(self, message, expect_reply=True):
        sock = socket.socket(family=socket.AF_UNIX)
        sock.connect(self.endpoint)

        if isinstance(message, str):
            message = message.encode()
        sock.sendall(message)

        rv = ""
        if expect_reply:
            reply = sock.recv(65536)
            if isinstance(reply, bytes):
                rv = reply.decode()
            else:
                rv = reply

        sock.close()

        return rv
