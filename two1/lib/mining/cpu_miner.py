"""
CPU-based miner
"""
import asyncio
from collections import namedtuple
import logging
import threading
import time
from two1.lib.bitcoin.block import CompactBlock
from two1.lib.bitcoin.txn import Transaction
from two1.lib.bitcoin.hash import Hash
import two1.lib.bitcoin.utils as utils

Share = namedtuple('Share', ['enonce2', 'nonce', 'otime', 'work_id'])
Work = namedtuple('Work', ['work_id', 'enonce2', 'cb'])


class CPUMiner(threading.Thread):
    def __init__(self, enonce1, enonce2_size, notify_message, event_loop,
                 handle_found_cb):
        threading.Thread.__init__(self)
        self.notify_msg = notify_message
        self.event_loop = event_loop
        self.handle_found_cb = handle_found_cb
        self.stop = False
        self.enonce1 = enonce1
        self.enonce2_size = enonce2_size
        self.logger = logging.getLogger(__name__)

    def run(self):
        self.logger.info("starting to mine")

        pool_target = utils.bits_to_target(self.notify_msg.bits_pool)
        for enonce2_num in range(0, 2 ** (self.enonce2_size * 8)):
            enonce2 = enonce2_num.to_bytes(self.enonce2_size, byteorder="big")

            cb_txn, _ = Transaction.from_bytes(
                self.notify_msg.coinb1 + self.enonce1 + enonce2 + self.notify_msg.coinb2)
            cb = CompactBlock(self.notify_msg.height,
                              self.notify_msg.version,
                              Hash(self.notify_msg.prev_block_hash),
                              self.notify_msg.ntime,
                              self.notify_msg.nbits,  # lower difficulty work for testing
                              self.notify_msg.merkle_edge,
                              cb_txn)
            for nonce in range(0xffffffff):
                cb.block_header.nonce = nonce
                h = cb.block_header.hash.to_int('little')
                if h < pool_target:
                    self.logger.info("Found Share")
                    share = Share(
                        enonce2=enonce2,
                        nonce=nonce,
                        work_id=self.notify_msg.work_id,
                        otime=self.notify_msg.ntime)
                    self.event_loop.call_soon_threadsafe(
                        asyncio.async,
                        self.handle_found_cb(share)
                    )
                    time.sleep(0.3)

class CPUWorkMaster(object):
    def __init__(self, enonce1, enonce2_size, num_workers=1):
        self.enonce1 = enonce1  # For now, gets set during an AuthReplyYes msg
        self.enonce2_size = enonce2_size  # Actually gets set during an AuthReplyYes msg
        self.num_workers = num_workers
        self.worker = []
        self.logger = logging.getLogger(__name__)

    def load_work(self, notify_msg, event_loop, notify_cb):

        if len(self.worker) < self.num_workers:

            self.logger.info(
                "starting on new work: job_id={} @ difficulty={}".format(notify_msg.work_id,
                                                                         notify_msg.bits_pool))
            th = CPUMiner(self.enonce1, self.enonce2_size, notify_msg, event_loop, notify_cb)
            self.worker.append(th)
            th.start()

