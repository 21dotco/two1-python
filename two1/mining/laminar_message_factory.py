import asyncio

__author__ = 'Ali'
import logging
import struct
from gen.laminar_ber import *


class LaminarEncodingError(Exception):
    pass


@asyncio.coroutine
def read_server_message_from_connection(reader):
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


def encode_laminar_object(laminar_obj):
    try:
        msg = LaminarClientMessage(value=laminar_obj).encode()
    except Exception as e:
        logging.getLogger().error("Laminar message encoding failed")
        raise LaminarEncodingError from e

    header = struct.pack('>H', len(msg))
    return header + msg
