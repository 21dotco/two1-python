# -*- Mode: Cython -*-

# based on: Thomas Dixon's MIT-licensed python code.

import struct

from libc.stdint cimport uint32_t, uint8_t

cdef uint32_t k[64]

k[:] = [
    0x428a2f98, 0x71374491, 0xb5c0fbcf, 0xe9b5dba5,
    0x3956c25b, 0x59f111f1, 0x923f82a4, 0xab1c5ed5,
    0xd807aa98, 0x12835b01, 0x243185be, 0x550c7dc3,
    0x72be5d74, 0x80deb1fe, 0x9bdc06a7, 0xc19bf174,
    0xe49b69c1, 0xefbe4786, 0x0fc19dc6, 0x240ca1cc,
    0x2de92c6f, 0x4a7484aa, 0x5cb0a9dc, 0x76f988da,
    0x983e5152, 0xa831c66d, 0xb00327c8, 0xbf597fc7,
    0xc6e00bf3, 0xd5a79147, 0x06ca6351, 0x14292967,
    0x27b70a85, 0x2e1b2138, 0x4d2c6dfc, 0x53380d13,
    0x650a7354, 0x766a0abb, 0x81c2c92e, 0x92722c85,
    0xa2bfe8a1, 0xa81a664b, 0xc24b8b70, 0xc76c51a3,
    0xd192e819, 0xd6990624, 0xf40e3585, 0x106aa070,
    0x19a4c116, 0x1e376c08, 0x2748774c, 0x34b0bcb5,
    0x391c0cb3, 0x4ed8aa4a, 0x5b9cca4f, 0x682e6ff3,
    0x748f82ee, 0x78a5636f, 0x84c87814, 0x8cc70208,
    0x90befffa, 0xa4506ceb, 0xbef9a3f7, 0xc67178f2
]

cdef uint32_t rotr (uint32_t x, uint32_t y):
    return ((x >> y) | (x << (32-y))) & 0xFFFFFFFFU

cdef uint32_t be_decode_uint32 (uint8_t * b):
    cdef uint32_t n = 0
    for i in range (4):
        n <<= 8
        n |= b[i]
    return n

cdef class sha256:
    cdef uint32_t* h
    cdef uint32_t h_initial[8]
    cdef bytes _buffer
    cdef uint32_t _counter
    cdef bint _locked

    def __init__ (self, bytes m):
        self._buffer = b''
        self._counter = 0
        self.h_initial[:] = [0x6a09e667, 0xbb67ae85, 0x3c6ef372, 0xa54ff53a, 0x510e527f, 0x9b05688c, 0x1f83d9ab, 0x5be0cd19]
        if m is not None:
            self.update(m)
        
    cdef process (self, bytes x):
        cdef uint32_t a,b,c,d,e,f,g,h
        cdef uint32_t s0, s1, maj, t1, t2, ch
        cdef uint32_t w[64]
        cdef uint8_t * x0 = x
        cdef int i

        for i in range (16):
            w[i] = be_decode_uint32 (x0)
            x0 += 4
        
        for i in range(16, 64):
            s0 = rotr(w[i-15], 7) ^ rotr(w[i-15], 18) ^ (w[i-15] >> 3)
            s1 = rotr(w[i-2], 17) ^ rotr(w[i-2], 19) ^ (w[i-2] >> 10)
            w[i] = (w[i-16] + s0 + w[i-7] + s1) & 0xFFFFFFFFu
        
        a = self.h[0]; b = self.h[1]; c = self.h[2]; d = self.h[3]
        e = self.h[4]; f = self.h[5]; g = self.h[6]; h = self.h[7]
        
        for i in range(64):
            s0 = rotr(a, 2) ^ rotr(a, 13) ^ rotr(a, 22)
            maj = (a & b) ^ (a & c) ^ (b & c)
            t2 = s0 + maj
            s1 = rotr(e, 6) ^ rotr(e, 11) ^ rotr(e, 25)
            ch = (e & f) ^ ((~e) & g)
            t1 = h + s1 + ch + k[i] + w[i]
            
            h = g
            g = f
            f = e
            e = (d + t1) & 0xFFFFFFFFu
            d = c
            c = b
            b = a
            a = (t1 + t2) & 0xFFFFFFFFu
            
        self.h[0] += a; self.h[1] += b; self.h[2] += c; self.h[3] += d
        self.h[4] += e; self.h[5] += f; self.h[6] += g; self.h[7] += h
        
    def update (self, bytes m):
        self.h = self.h_initial
        self._buffer += m
        self._counter += len(m)
        while len(self._buffer) >= 64:
            self.process (self._buffer[:64])
            self._buffer = self._buffer[64:]
            
    def digest (self):
        mdi = self._counter & 0x3F
        length = struct.pack('!Q', self._counter<<3)
        
        if mdi < 56:
            padlen = 55-mdi
        else:
            padlen = 119-mdi
        
        self.update (b'\x80'+(b'\x00'*padlen)+length)
        return ''.join([struct.pack('!L', i) for i in self.h[:8]])
        
    property mid_state:
        def __get__ (self):
            cdef uint32_t * h = self.h
            return [h[0], h[1], h[2], h[3], h[4], h[5], h[6], h[7]]

    def hexdigest(self):
        return self.digest().encode('hex')
