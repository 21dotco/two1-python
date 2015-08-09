from abc import ABCMeta
import abc
import asyncio
import codecs
import logging
import struct
from gen import laminar_pb2
from gen.laminar_ber import LaminarClientMessage, LaminarServerMessage, BitsplitAuthRequest, SubmitRequest

decode_hex = codecs.getdecoder("hex_codec")


class AbstractMessageFactory(metaclass=ABCMeta):
    @staticmethod
    @abc.abstractmethod
    def encode_object(laminar_obj):
        pass

    @staticmethod
    @abc.abstractmethod
    def read_object(reader):
        pass

    @staticmethod
    @abc.abstractmethod
    def create_bitshare_auth_request(version, username, mac, wallet_index, numerator, denominator):
        pass

    @staticmethod
    @abc.abstractmethod
    def create_submit_request(message_id, job_id, enonce2, otime, nonce):
        pass


class ProtobufMessageFactory(AbstractMessageFactory):
    @staticmethod
    def encode_object(laminar_obj):
        msg_str = laminar_obj.SerializeToString()
        header = struct.pack('>H', len(msg_str))
        return header + msg_str

    @staticmethod
    def create_bitshare_auth_request(version, username, mac, wallet_index, numerator, denominator):
        req = laminar_pb2.LaminarClientMessage()
        req.bitshare_auth_request.version = version
        req.bitshare_auth_request.username = decode_hex(username)[0]
        req.bitshare_auth_request.mac = decode_hex(mac)[0]
        req.bitshare_auth_request.wallet_index = wallet_index
        req.bitshare_auth_request.numerator = numerator
        req.bitshare_auth_request.denominator = denominator
        return req

    @staticmethod
    def create_submit_request(message_id, job_id, enonce2, otime, nonce):
        req = laminar_pb2.LaminarClientMessage()
        req.submit_request.message_id = message_id
        req.submit_request.job_id = job_id
        req.submit_request.enonce2 = enonce2
        req.submit_request.otime = otime
        req.submit_request.nonce = nonce
        return req

    @staticmethod
    @asyncio.coroutine
    def read_object(reader):
        head_buffer = yield from reader.read(2)
        if len(head_buffer) == 0:
            raise ConnectionError

        size, = struct.unpack('>H', head_buffer)
        pkt = yield from _read_exact(size, reader)
        client_message = laminar_pb2.LaminarServerMessage()
        client_message.ParseFromString(pkt)
        # take a look at the protobuf file to see what this means.
        message_type = client_message.WhichOneof("servermessages")
        if message_type is None:
            logger = logging.getLogger(__name__)
            logger.warn("Invalid or Empty Message Sent to Client")
            raise LaminarEncodingError("Invalid Client Message Received")
        return getattr(client_message, message_type)


class ASNLaminarMessageFactory(AbstractMessageFactory):
    @staticmethod
    def create_bitshare_auth_request(version, username, mac, wallet_index, numerator, denominator):
        result = BitsplitAuthRequest(
            version=version,
            uuid=decode_hex(username)[0],
            mac=decode_hex(mac)[0],
            protocol=wallet_index,
            numerator=numerator,
            denominator=denominator
        )
        return result

    @staticmethod
    def create_submit_request(message_id, job_id, enonce2, otime, nonce):
        laminar_obj = SubmitRequest(
            message_id=message_id,
            jobid=job_id,
            enonce2=enonce2,
            otime=otime,
            nonce=nonce)
        return laminar_obj

    @staticmethod
    def encode_object(laminar_obj):
        try:
            msg = LaminarClientMessage(value=laminar_obj).encode()
        except Exception as e:
            logging.getLogger().error("Laminar message encoding failed")
            raise LaminarEncodingError from e

        header = struct.pack('>H', len(msg))
        return header + msg

    @staticmethod
    @asyncio.coroutine
    def read_object(reader):
        """
        reads a  LaminarClientMessage from the reader stream.
        :param reader: asyncio stream reader
        """
        head_buffer = yield from reader.read(2)
        if len(head_buffer) == 0:
            raise ConnectionError

        size, = struct.unpack('>H', head_buffer)
        pkt = yield from _read_exact(size, reader)
        msg = LaminarServerMessage()
        try:
            msg.decode(pkt)
        except Exception as e:
            raise LaminarEncodingError from e

        return msg


@asyncio.coroutine
def _read_exact(n, reader):
    buffer = yield from reader.read(n)
    n -= len(buffer)
    if n == 0:
        return buffer

    buffer_list = [buffer]
    while 1:
        buffer = yield from reader.read(n)
        buffer_list.append(buffer)
        n -= len(buffer)
        if n == 0:
            return buffer


class LaminarEncodingError(Exception):
    pass
