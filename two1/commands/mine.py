"""
Mine Bitcoin locally via a CPU or built-in mining chip
"""
# standard python imports
import json
import subprocess
import time
import os
import random
from collections import namedtuple
import base64

# 3rd party imports
import click

# two1 imports
from two1.lib.bitcoin.block import CompactBlock
from two1.lib.bitcoin.txn import Transaction
from two1.lib.server import rest_client, message_factory
from two1.lib.server.analytics import capture_usage
import two1.commands.config as cmd_config
from two1.commands import status
from two1.commands.status import has_bitcoinkit
from two1.lib.bitcoin.hash import Hash
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.decorators import check_notifications
from two1.lib.util.exceptions import MiningDisabledError
from two1.lib.util.uxstring import UxString
import two1.lib.bitcoin.utils as utils


@click.command()
@click.option('--dashboard', default=False, is_flag=True,
              help="Dashboard with mining details")
@click.pass_context
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
See a mining dashboard for low-level mining details.
$ 21 mine --dashboard
"""
    config = ctx.obj['config']
    _mine(config, dashboard=dashboard)


@check_notifications
@capture_usage
def _mine(config, dashboard=False):
    """ Starts the mining ASIC if not mining and cpu mines if already mining

    Args:
        config (Config): config object used for getting .two1 information
        dashboard (bool): shows minertop dashboard if True
    """

    if has_bitcoinkit():
        if not is_minerd_running():
            start_minerd(config, dashboard)
        elif dashboard:
            show_minertop(dashboard)
        # if minerd is running and we have not specified a dashboard flag
        # do a cpu mine
        else:
            start_cpu_mining(config)
    else:
        config.log(UxString.buy_ad, fg="magenta")
        start_cpu_mining(config)


def is_minerd_running():
    """ Checks if minerd id already running and mining

        minerd is the miner client daemon.

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
    """ Fires up minertop, the mining dashboard

    Args:
        show_dashboard (bool): shows the dashboard if True
    """
    if show_dashboard:
        click.pause(UxString.mining_show_dashboard_prompt)
        subprocess.call("minertop")
    else:
        click.echo(UxString.mining_show_dashboard_context)


def start_minerd(config, show_dashboard=False):
    """ Starts minerd, a bitcoin mining client

    Args:
        config (Config): config object used for getting .two1 information
        show_dashboard (bool): shows the dashboard if True
    """
    # Check if it's already up and running by checking pid file.
    minerd_pid_file = "/run/minerd.pid"
    config.log(UxString.mining_chip_start)
    # Read the PID and check if the process is running
    if os.path.isfile(minerd_pid_file):
        pid = None
        with open(minerd_pid_file, "r") as f:
            pid = int(f.read().rstrip())

        if pid is not None:
            if check_pid(pid):
                # Running, so fire up minertop...
                click.echo(UxString.mining_chip_running)
                show_minertop(show_dashboard)
                return
            else:
                # Stale PID file, so delete it.
                subprocess.call(["sudo", "minerd", "--stop"])

    # Not running, let's start it
    # TODO: make sure config exists in /etc
    # TODO: replace with sys-ctrl command
    minerd_cmd = ["sudo", "minerd", "-u", config.username,
                  cmd_config.TWO1_POOL_URL]
    try:
        o = subprocess.check_output(minerd_cmd, universal_newlines=True)
    except subprocess.CalledProcessError as e:
        config.log("\nError starting minerd: %r" % e)

    # Now call minertop after it's started
    show_minertop(show_dashboard)


def start_cpu_mining(config):
    """ Mines bitcoin on the command line by using the CPU of the system

    CPU mining, or foreground mining, is when the pool sets the difficulty
    very low and the CPU finds a valid solution.

    Args:
        config (Config): config object used for getting .two1 information
    """

    client = rest_client.TwentyOneRestClient(cmd_config.TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    enonce1, enonce2_size, reward = set_payout_address(config, client)

    start_time = time.time()
    config.log(UxString.mining_start.format(config.username, reward))



    work = get_work(config, client)

    found_share = mine_work(work, enonce1=enonce1, enonce2_size=enonce2_size)

    paid_satoshis = save_work(client, found_share, config.username)

    end_time = time.time()
    duration = end_time - start_time

    config.log(
        UxString.mining_success.format(config.username, paid_satoshis, duration),
        fg="magenta")

    click.echo(UxString.mining_status)
    status.status_wallet(config, client)

    click.echo(UxString.mining_finish.format(
        click.style("21 status", bold=True), click.style("21 buy", bold=True)))


def set_payout_address(config, client):
    """ Set a new address from the HD wallet for payouts

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Returns:
        bytes: extra nonce 1 which is required for computing the coinbase transaction
        int: the size in bytes of the extra nonce 2
        int: reward amount given upon sucessfull solution found
    """
    payout_address = config.wallet.current_address
    auth_resp = client.account_payout_address_post(payout_address)

    user_info = json.loads(auth_resp.text)
    enonce1_base64 = user_info["enonce1"]
    enonce1 = base64.decodebytes(enonce1_base64.encode())
    enonce2_size = user_info["enonce2_size"]
    reward = user_info["reward"]

    return enonce1, enonce2_size, reward


def check_pid(pid):
    """ Makes a few checks to see if the given pid is valid

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


def get_work(config, client):
    """ Gets work from the pool using the rest client

    Args:
        config (Config): config object used for getting .two1 information
        client (TwentyOneRestClient): rest client used for communication with the backend api

    Returns:
        WorkNotification: a Swirl work notification message
    """
    try:
        work_msg = client.get_work()
    except ServerRequestError as e:
        if e.status_code == 404 or e.status_code == 403:
            click.echo(UxString.mining_limit_reached)
            raise MiningDisabledError(UxString.mining_limit_reached)
        else:
            raise e

    msg_factory = message_factory.SwirlMessageFactory()
    msg = base64.decodebytes(work_msg.content)
    work = msg_factory.read_object(msg)
    return work


Share = namedtuple('Share', ['enonce2', 'nonce', 'otime', 'work_id'])
Work = namedtuple('Work', ['work_id', 'enonce2', 'cb'])


def mine_work(work_msg, enonce1, enonce2_size):
    """ Mines the work using a CPU to find a valid solution

        Loops until the CPU finds a valid solution of the given work.

    Todo:
        slow down the click echo when on a 21BC

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
                click.echo(click.style(u'█', fg='green'), nl=False)
                row_counter += 1
            if row_counter > 40:
                row_counter = 0
                click.echo("")

            cb.block_header.nonce = nonce
            h = cb.block_header.hash.to_int('little')
            if h < pool_target:
                share = Share(
                    enonce2=enonce2,
                    nonce=nonce,
                    work_id=work_msg.work_id,
                    otime=int(time.time()))
                # adds a new line at the end of progress bar
                click.echo("")
                return share

        click.echo("Exhausted enonce1 space. Changing enonce2")


def save_work(client, share, username):
    """ Submits the share to the pool using the rest client

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
