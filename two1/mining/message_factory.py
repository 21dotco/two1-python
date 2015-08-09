from abc import ABCMeta
import abc
import asyncio
import codecs
import logging
import struct
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
    def create_bitsplit_auth_request(version, user, worker, protocol, numerator, denominator):
        pass


class ASNLaminarMessageFactory(AbstractMessageFactory):
    @staticmethod
    def create_bitsplit_auth_request(version, user, worker, protocol, numerator, denominator):
        result = BitsplitAuthRequest(
            version=version,
            uuid=decode_hex(user)[0],
            mac=decode_hex(worker)[0],
            protocol=protocol,
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
