"""
Mine bitcoin on a 21 Bitcoin Computer.
"""
# standard python imports
from collections import namedtuple
import base64
import json
import logging
import os
import random
import subprocess
import sys
import time

# 3rd party imports
import click

# two1 imports
import two1
from two1.bitcoin.block import CompactBlock
from two1.bitcoin.txn import Transaction
from two1.server import message_factory
from two1.commands.util import decorators
from two1.commands import status
from two1.commands.util import bitcoin_computer
from two1.bitcoin.hash import Hash
from two1.commands.util import exceptions
from two1.commands.util import uxstring
from two1.commands.util.uxstring import ux
import two1.bitcoin.utils as utils


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.option('--dashboard', default=False, is_flag=True,
              help="Dashboard with mining details (only for Bitcoin Computer users)")
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
@decorators.check_notifications
def mine(ctx, dashboard):
    """Mine bitcoin at the command line.

\b
Usage
-----
Invoke this with no arguments to start mining.
$ 21 mine

\b
Then view your new balance.
$ 21 status

\b
View aggregated logs to see your mining progress.
$ 21 log

\b
See a mining dashboard for low-level mining details (only for Bitcoin Computer users)
$ 21 mine --dashboard

\b
Stop the ASIC miner from mining in the background.
$ sudo minerd --stop
"""
    _mine(ctx.obj['config'], ctx.obj['client'], ctx.obj['wallet'], dashboard=dashboard)


def _mine(config, client, wallet, dashboard=False):
    """ Start a mining chip if not already running. Otherwise mine at CLI.

    On a 21 Bitcoin Computer, we attempt to start the mining chip if
    is not already running. If it is already running, repeated
    invocation of 21 mine will result in buffered mining (advances
    against the next day's mining proceeds). Finally, if we are
    running the 21 software on an arbitrary device (i.e. not on a
    Bitcoin Computer), we prompt the user to use 21 earn instead.

    Args:
        config (Config): config object used for getting .two1 information
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        wallet (two1.wallet.Wallet): a user's wallet instance
        dashboard (bool): shows minertop dashboard if True
    """
    if bitcoin_computer.has_mining_chip():
        if not is_minerd_running():
            start_minerd(config, dashboard)
        elif dashboard:
            show_minertop(dashboard)
        # if minerd is running and we have not specified a dashboard
        # flag do a cpu mine
        else:
            start_cpu_mining(config.username, client, wallet)
    else:
        logger.info(uxstring.UxString.use_21_earn_instead)
        sys.exit(1)


def is_minerd_running():
    """ Check if minerd is already running and mining.

    Here, minerd is the miner client daemon.

    Returns:
        bool: True if minerd is already mining, False otherwise
    """
    rc = True
    import socket
    try:
        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/tmp/minerd.sock")
        s.close()
    except Exception:
        rc = False
    return rc


def show_minertop(show_dashboard):
    """ Start minertop, the mining dashboard.

    Args:
        show_dashboard (bool): shows the dashboard if True
    """
    if show_dashboard:
        click.pause(uxstring.UxString.mining_show_dashboard_prompt)
        subprocess.call("minertop", shell=True)
    else:
        logger.info(uxstring.UxString.mining_show_dashboard_context)


def start_minerd(config, show_dashboard=False):
    """ Start minerd, a bitcoin mining client.

    Args:
        config (Config): config object used for getting .two1 information
        show_dashboard (bool): shows the dashboard if True
    """
    # Check if it's already up and running by checking pid file.
    minerd_pid_file = "/run/minerd.pid"
    logger.info(uxstring.UxString.mining_chip_start)
    # Read the PID and check if the process is running
    if os.path.isfile(minerd_pid_file):
        pid = None
        with open(minerd_pid_file, "r") as f:
            pid = int(f.read().rstrip())

        if pid is not None:
            if check_pid(pid):
                # Running, so fire up minertop...
                logger.info(uxstring.UxString.mining_chip_running)
                show_minertop(show_dashboard)
                return
            else:
                # Stale PID file, so delete it.
                subprocess.call(["sudo", "minerd", "--stop"])

    # Not running, let's start it
    minerd_cmd = ["sudo", "minerd", "-u", config.username,
                  two1.TWO1_POOL_URL]
    try:
        subprocess.check_output(minerd_cmd, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        logger.info("\nError starting minerd: {}".format(e))

    # Now call minertop after it's started
    show_minertop(show_dashboard)


def start_cpu_mining(username, client, wallet, prefix='mining'):
    """ Mine bitcoin on the command line by using the CPU of the system.

    Note that this is primarily used to rate limit mining
    advances. CPU mining, or foreground mining, is when the pool sets
    the difficulty very low and the CPU finds a valid solution.

    Args:
        username (str): username from .two1/two1.json
    """
    enonce1, enonce2_size, reward = set_payout_address(client, wallet)

    start_time = time.time()
    ux(prefix + '_start', username, reward)

    # gets work from the server
    work = get_work(client)

    # kicks off cpu miner to find a solution
    found_share = mine_work(work, enonce1=enonce1, enonce2_size=enonce2_size)

    paid_satoshis = save_work(client, found_share)

    end_time = time.time()
    duration = end_time - start_time

    ux(prefix + '_success', username, paid_satoshis, duration, fg='magenta')

    ux(prefix + '_status')
    status.status_wallet(client, wallet)

    status21 = click.style("21 status", bold=True)
    buy21 = click.style("21 buy", bold=True)
    ux(prefix + '_finish', status21, buy21)


def set_payout_address(client, wallet):
    """ Set a new address from the HD wallet for payouts.

    Note that is set server-side on a per-account basis. Thus, in the
    case where a single user has different wallets on different
    machines, all mining proceeds on all machines are sent to this
    address.

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api
        wallet (two1.wallet.Wallet): a user's wallet instance

    Returns:
        bytes: extra nonce 1 which is required for computing the coinbase transaction
        int: the size in bytes of the extra nonce 2
        int: reward amount given upon sucessfull solution found
    """
    payout_address = wallet.current_address
    auth_resp = client.account_payout_address_post(payout_address)

    user_info = json.loads(auth_resp.text)
    enonce1_base64 = user_info["enonce1"]
    enonce1 = base64.decodebytes(enonce1_base64.encode())
    enonce2_size = user_info["enonce2_size"]
    reward = user_info["reward"]

    return enonce1, enonce2_size, reward


def check_pid(pid):
    """ Make a few checks to see if the given pid is valid.

    Args:
        pid (int): a pid number

    Returns:
        bool: True if the PID is valid, False otherwise
    """
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # There is a process but we don't have permissions
        return True
    except:
        raise

    return True


def get_work(client):
    """ Get work from the pool using the rest client.

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Returns:
        WorkNotification: a Swirl work notification message
    """
    try:
        response = client.get_work()
    except exceptions.ServerRequestError as e:
        if e.status_code == 403 and "detail" in e.data and "TO200" in e.data["detail"]:
            raise exceptions.BitcoinComputerNeededError(
                msg=uxstring.UxString.mining_bitcoin_computer_needed, response=response)
        elif e.status_code == 403 and e.data.get("detail") == "TO201":
            raise exceptions.MiningDisabledError(uxstring.UxString.Error.suspended_account)
        elif e.status_code == 403 and e.data.get("detail") == "TO501":
            raise exceptions.MiningDisabledError(uxstring.UxString.monthly_mining_limit_reached)
        elif e.status_code == 403 and e.data.get("detail") == "TO502":
            raise exceptions.MiningDisabledError(uxstring.UxString.lifetime_earn_limit_reached)
        elif e.status_code == 403 and e.data.get("detail") == "TO503":
            raise exceptions.MiningDisabledError(uxstring.UxString.no_earn_allocations.format(
                two1.TWO1_WWW_HOST, client.username))
        elif e.status_code == 404:
            if bitcoin_computer.has_mining_chip():
                raise exceptions.MiningDisabledError(uxstring.UxString.monthly_mining_limit_reached)
            else:
                raise exceptions.MiningDisabledError(uxstring.UxString.earn_limit_reached)
        else:
            raise e

    msg_factory = message_factory.SwirlMessageFactory()
    msg = base64.decodebytes(response.content)
    work = msg_factory.read_object(msg)
    return work


Share = namedtuple('Share', ['enonce2', 'nonce', 'otime', 'work_id'])
Work = namedtuple('Work', ['work_id', 'enonce2', 'cb'])


def mine_work(work_msg, enonce1, enonce2_size):
    """ Mine the work using a CPU to find a valid solution.

    Loop until the CPU finds a valid solution of the given work.

    Todo:
        Slow down the click echo when on a 21BC.

    Args:
        work_msg (WorkNotification): the work given by the pool API
        enonce1 (bytes): extra nonce required to make the coinbase transaction
        enonce2_size (int): size of the extra nonce 2 in bytes
    """
    pool_target = utils.bits_to_target(work_msg.bits_pool)
    for enonce2_num in range(0, 2 ** (enonce2_size * 8)):
        enonce2 = enonce2_num.to_bytes(enonce2_size, byteorder="big")

        cb_txn, _ = Transaction.from_bytes(
            work_msg.coinb1 + enonce1 + enonce2 + work_msg.coinb2)
        cb = CompactBlock(work_msg.height,
                          work_msg.version,
                          Hash(work_msg.prev_block_hash),
                          work_msg.ntime,
                          work_msg.nbits,  # lower difficulty work for testing
                          work_msg.merkle_edge,
                          cb_txn)

        row_counter = 0
        for nonce in range(0xffffffff):

            if nonce % 6e3 == 0:
                logger.info(click.style(u'█', fg='green'), nl=False)
                row_counter += 1
            if row_counter > 40:
                row_counter = 0
                logger.info("")

            cb.block_header.nonce = nonce
            h = cb.block_header.hash.to_int('little')
            if h < pool_target:
                share = Share(
                    enonce2=enonce2,
                    nonce=nonce,
                    work_id=work_msg.work_id,
                    otime=int(time.time()))
                # adds a new line at the end of progress bar
                logger.info("")
                return share

        logger.info("Exhausted enonce1 space. Changing enonce2")


def save_work(client, share):
    """ Submit the share to the pool using the rest client.

    Args:
        client (TwentyOneRestClient): rest client used for communication with the backend api
        share (Share): namedtuple Share object which had the enonce2, nonce, work_if, and otime

    Returns:
        int: payout amount
    """
    message_id = random.randint(1, 1e5)
    msg_factory = message_factory.SwirlMessageFactory()
    req_msg = msg_factory.create_submit_share_request(message_id=message_id,
                                                      work_id=share.work_id,
                                                      enonce2=share.enonce2,
                                                      otime=share.otime,
                                                      nonce=share.nonce)

    payment_result = client.send_work(data=req_msg)
    payment_details = json.loads(payment_result.text)
    amount = payment_details["amount"]
    return amount
