import asyncio
from collections import deque, namedtuple
import random
import threading
import queue
import time

from two1.bitcoin.block import CompactBlock
from coinbase import CoinbaseTransactionBuilder
from two1.bitcoin.txn import TransactionOutput
from two1.bitcoin.utils import bytes_to_str

Share = namedtuple('Share', ['enonce2', 'nonce', 'otime', 'job_id'])
Work = namedtuple('Work', ['job_id', 'enonce2', 'cb'])

"""

Client:
    1. The client receives work from the pool server, either via stratum or
       laminar.
    2. A CompactBlock object is created from the received work.
    3. The mining application creates a coinbase transaction, using
       CoinbaseTransactionBuilder.
    4. The coinbase transaction is provided to the CompactBlock object which
       will complete the merkle edge and provide a merkle_root_hash. It will
       also compute the "midstate" of the block (useful only if not Bitshare).
    5. Mining application sends work to a hasher and waits for "founds".
    6. Upon receiving a "found", the validity can be determined by calling
       CompactBlock.check_valid_nonce(nonce)
    7. If valid, the share is submitted to the pool server.
"""

class CPUMiner(threading.Thread):

    def __init__(self, work, event_loop, handle_found_cb):
        threading.Thread.__init__(self)
        self.current_work = work
        self.event_loop = event_loop
        self.handle_found_cb = handle_found_cb
        self.stop = False

    def run(self):
        for nonce in range(0xffffffff):
            if nonce % int(1e5) == 0:
                if self.stop:
                    self.stop = False
                    print("Exiting Worker....")
                    break

            if (nonce % int(2 * 1e6)) == 1 or self.current_work.cb.check_valid_nonce(nonce):
                # notify we have a found!!!
                # call the callbacks on the main loop

                share = Share(
                    enonce2=self.current_work.enonce2,
                    nonce=nonce,
                    job_id=self.current_work.job_id,
                    otime=int(time.time()))

                # TODO investigate: Maybe BaseEventLoop.run_in_executor() is better
                # option vs call_soon
                print("Found a nonce: 0x%08x for job_id %g " %
                      (nonce, share.job_id))
                self.event_loop.call_soon_threadsafe(
                    asyncio.async,
                    self.handle_found_cb(share)
                )


class CPUWorkMaster(object):

    def __init__(self, num_workers=1):
        self.enonce1 = b'0000'  # For now, gets set during an AuthReplyYes msg
        self.enonce2_size = 4  # Actually gets set during an AuthReplyYes msg
        self.num_workers = num_workers
        self.worker = []

    # previously running work will be stopped and new work will be reloaded
    # calls notify_cb on notify_loop when something is found
    def load_work(self, notify_msg, event_loop, notify_cb):
        print("*** Client starting on new work *** job_id %g " % notify_msg.work_id)
        # must be of type laminar.Notify
        if len(self.worker) > 0:
            for th in self.worker:
                th.stop = True
                # th.join()
            self.worker = []

        outputs = [TransactionOutput.from_bytes(
            x)[0] for x in notify_msg.outputs]
        # The pool iscript0 includes the height and enonce length bytes so
        # slice those off prior to creating the CoinbaseTransaction.
        # This will get fixed in pool2
        iscript0 = notify_msg.iscript0[4:-1]
        cb_builder = CoinbaseTransactionBuilder(
            notify_msg.block_height, iscript0, notify_msg.iscript1,
            len(self.enonce1), self.enonce2_size, outputs, 0
        )

        for w in range(self.num_workers):
            enonce2 = bytes([random.randrange(0, 256)
                             for n in range(self.enonce2_size)])
            cb_txn = cb_builder.build(self.enonce1, enonce2)
            print(bytes_to_str(cb_txn.client_serialize()))

            edge = [e for e in notify_msg.edge]

            cb = CompactBlock(notify_msg.block_height,
                              notify_msg.block_version,
                              notify_msg.prev_block_hash,
                              notify_msg.itime,
                              0x1dffffff,  # lower difficulty work for testing
                              edge,
                              cb_txn)
            # print(notify_msg)
            print([bytes_to_str(e) for e in edge])
            # Append the work to the queue for the worker
            work = Work(job_id=notify_msg.work_id,
                        enonce2=enonce2,
                        cb=cb)

            # set and start CPU mining
            th = CPUMiner(work, event_loop, notify_cb)
            self.worker.append(th)
            th.start()
