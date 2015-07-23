# -*- Mode: Python -*-

import base58
import codecs
import struct
import hashlib


def bytes_to_str(b):
    return codecs.encode(b, 'hex_codec').decode('ascii')

def hex_str_to_bytes(h):
    return bytes.fromhex(h)

def dhash(s):
    return hashlib.sha256(hashlib.sha256(s).digest()).digest()

# Is there a better way of doing this?
def render_int(n):
    # little-endian byte stream
    if n < 0:
        neg = True
        n = -n
    else:
        neg = False
    r = []
    while n:
        r.append(n & 0xff)
        n >>= 8
    if neg:
        if r[-1] & 0x80:
            r.append(0x80)
        else:
            r[-1] |= 0x80
    elif r and (r[-1] & 0x80):
        r.append(0)
    return bytes(r)

def pack_compact_int(i):
    ''' See
        https://bitcoin.org/en/developer-reference#compactsize-unsigned-integers
    '''
    if i < 0xfd:
        return struct.pack('<B', i)
    elif i <= 0xffff:
        return struct.pack('<BH', 0xfd, i)
    elif i <= 0xffffffff:
        return struct.pack('<BI', 0xfe, i)
    else:
        return struct.pack('<BQ', 0xff, i)

def unpack_compact_int(bytestr):
    ''' See
        https://bitcoin.org/en/developer-reference#compactsize-unsigned-integers
    '''

    b0 = bytestr[0]
    if b0 < 0xfd:
        return (b0, bytestr[1:])
    elif b0 == 0xfd:
        return (struct.unpack('<H', bytestr[1:3])[0], bytestr[3:])
    elif b0 == 0xfe:
        return (struct.unpack('<I', bytestr[1:5])[0], bytestr[5:])
    elif b0 == 0xff:
        return (struct.unpack('<Q', bytestr[1:9])[0], bytestr[9:])
    else:
        return None

def make_push_str(s):
    ls = len(s)
    hexstr = bytes_to_str(s)
    pd_index = 0

    from two1.bitcoin.script import Script
    
    if ls < Script.BTC_OPCODE_TABLE['OP_PUSHDATA1']:
        return bytes([ls]) + s
    # Determine how many bytes are required for the length
    elif ls < 0xff:
        pd_index = 1
    elif ls < 0xffff:
        pd_index = 2
    else:
        pd_index = 4

    return bytes(Script('OP_PUSHDATA%d 0x%s' % (pd_index, hexstr)))

def make_push_int(i):
    from two1.bitcoin.script import Script
    
    if i >= 0 and i <= 16:
        return bytes(Script('OP_%d' % i))
    else:
        return make_push_str(render_int(i))

def pack_u32(i):
    return struct.pack('<I', i)

def unpack_u32(b):
    u32 = struct.unpack('<I', b[0:4])
    return (u32[0], b[4:])

def pack_u64(i):
    return struct.pack('<Q', i)

def unpack_u64(b):
    u64 = struct.unpack('<Q', b[0:8])
    return (u64[0], b[8:])

def pack_var_str(s):
    return pack_compact_int(len(s)) + s

def unpack_var_str(b):
    strlen, b0 = unpack_compact_int(b)
    return (b0[:strlen], b0[strlen:])

def pack_output(script, value):
    return ''.join([
        pack_u64(value),
        pack_var_str(script)
    ])

def pack_height(height):
    return pack_var_str(make_push_int(height))

# These 2 functions are very specific to finishing
# a merkle tree *after* the coinbase has been added
# in. These should likely be elsewhere, i.e. the pool
# mining code
def merkle_edge(tl):
    edge = []
    hl = [dhash(t) for t in tl]
    while True:
        if len(hl) == 1:
            return hl[0], edge
        else:
            edge.append(hl[1])
        if len(hl) % 2 != 0:
            hl.append(hl[-1])
        hl0 = []
        for i in range(0, len(hl), 2):
            hl0.append(dhash(hl[i] + hl[i + 1]))
        hl = hl0

def finish_edge(t0, tl):
    if len(tl):
        return finish_edge(dhash(t0 + tl[0]), tl[1:])
    else:
        return t0

def decode_compact_target(bits):
    shift = bits >> 24
    target = (bits & 0xffffff) * (1 << (8 * (shift - 3)))
    return target

def encode_compact_target(target):
    hex_target = '%x' % target
    shift = (len(hex_target) + 1) / 2
    prefix = target >> (8 * (shift - 3))
    return (shift << 24) + prefix

def bits_to_difficulty(bits):
    target = decode_compact_target(bits)
    return 0xffff0000000000000000000000000000000000000000000000000000 / target

def address_to_key(s):
    n = base58.b58decode_check(s)
    version = n[0]
    h160 = n[1:]
    return version, h160

def compute_reward(height):
    era = height // 210000
    return 50 * 100000000 / (era + 1)
