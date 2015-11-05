import click
from tabulate import tabulate
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString

def has_bitcoinkit():
    """Quick check for presence of mining chip via file presence.

    The full test is to actually try to boot the chip, but we
    only try that if this file exists.

    We keep this file in two1/commands/status to avoid a circular
    import.
    """
    try:
        with open("/proc/device-tree/hat/product", "r") as f:
            bitcoinkit_present = f.read().startswith('21 Bitcoin')
    except FileNotFoundError:
        bitcoinkit_present = False
    return bitcoinkit_present


def get_hashrate():
    """Return hashrate of mining chip on current system.
    """
    hashrate = None

    try:
        import socket
        import json

        s = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        s.connect("/tmp/minerd.sock")

        buf = b""

        while True:
            chunk = s.recv(4096)

            # If server disconnected
            if not chunk:
                s.close()
                break

            buf += chunk
            while b"\n" in buf:
                pos = buf.find(b"\n")
                data = buf[0:pos].decode('utf-8')
                buf = buf[pos+1:]

                event = json.loads(data)

                if event['type'] == "StatisticsEvent":
                    # Use 15min hashrate, if uptime is past 15min
                    if event['payload']['statistics']['uptime'] > 15*60:
                        hashrate = "{:.1f} GH/s".format(event['payload']['statistics']['hashrate']['15min']/1e9)
                    else:
                        hashrate = "~50 GH/s (warming up)"

                    break

            if hashrate:
                break
    except:
        pass

    return hashrate or UxString.Error.data_unavailable


def status_mining(config, client):
    has_chip = has_bitcoinkit()
    if has_chip:
        bk = "21 mining chip running (/run/minerd.pid)"
        mined = client.get_mined_satoshis()
        hashrate = get_hashrate()
        if hashrate == UxString.Error.data_unavailable:
            bk = "Run {} to start mining".format(click.style("21 mine", bold=True))
    else:
        bk, mined, hashrate = None, None, None
    data = dict(is_mining=bk,
                hashrate=hashrate,
                mined=mined)
    if has_chip:
        out = UxString.status_mining.format(**data)
        config.log(out)

    return data


@click.command("status")
@click.option("--detail",
              is_flag=True,
              default=False,
              help="List non-zero balances for each address")
@json_output
def status(config, detail):
    """View your bitcoin balance and address.
    """
    return _status(config, detail)


@capture_usage
def _status(config, detail):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)


    status = {
        "account": status_account(config),
        "mining": status_mining(config, client),
        "wallet": status_wallet(config, client, detail)
    }

    config.log("")
    # status_endpoints(config)
    # status_bought_endpoints(config)

    return status

def status_account(config):
    status_account = {
        "username": config.username,
        "address": config.wallet.current_address
    }
    config.log(UxString.status_account.format(**status_account))
    return status_account

SEARCH_UNIT_PRICE = 800
SMS_UNIT_PRICE = 1000


def status_wallet(config, client, detail=False):
    """Print wallet status to the command line.
    """
    twentyone_balance, onchain, pending_transactions, flushed_earnings = \
        _get_balances(config, client)

    if detail:
        # show balances by address for default wallet
        address_balances = config.wallet.balances_by_address(0)
        byaddress = ["Addresses:"]
        for addr, balances in address_balances.items():
            if balances['confirmed'] > 0 or balances['total'] > 0:
                byaddress.append("{}: {} (confirmed), {} (total)".format(
                    addr, balances['confirmed'], balances['total']))
        byaddress = '\n      '.join(byaddress)
    else:
        byaddress = "To see all wallet addresses, do 21 status --detail"

    status_wallet = {
        "twentyone_balance": twentyone_balance,
        "onchain": onchain,
        "flushing": flushed_earnings,
        "byaddress": byaddress
    }
    config.log(UxString.status_wallet.format(**status_wallet))

    total_balance = twentyone_balance + onchain
    buyable_searches = int(total_balance / SEARCH_UNIT_PRICE)
    buyable_sms = int(total_balance / SMS_UNIT_PRICE)
    status_buyable = {
        "buyable_searches": buyable_searches,
        "search_unit_price": SEARCH_UNIT_PRICE,
        "buyable_sms": buyable_sms,
        "sms_unit_price": SMS_UNIT_PRICE
    }
    config.log(UxString.status_buyable.format(**status_buyable), nl=False)

    if total_balance == 0:
        config.log(UxString.status_empty_wallet.format(click.style("21 mine",
                                                                   bold=True)))
    else:
        buy21 = click.style("21 buy", bold=True)
        buy21help = click.style("21 buy --help", bold=True)
        config.log(UxString.status_exit_message.format(buy21, buy21help),
                   nl=False)

    return {
        "wallet" : status_wallet,
        "buyable": status_buyable
    }


def _get_balances(config, client):
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()
    pending_transactions = balance_u - balance_c

    spendable_balance = min(balance_c, balance_u)

    data = client.get_earnings()
    twentyone_balance = data["total_earnings"]
    flushed_earnings = data["flushed_amount"]

    return twentyone_balance, spendable_balance, pending_transactions, flushed_earnings


def status_earnings(config, client):
    data = client.get_earnings()
    total_earnings = data["total_earnings"]
    total_payouts = data["total_payouts"]
    config.log('\nMining Proceeds', fg='magenta')
    config.log('''\
    Total Earnings           : {}
    Total Payouts            : {}'''
               .format(none2zero(total_earnings),
                       none2zero(total_payouts))
               )

    if "flush_amount" in data and data["flush_amount"] > 0:
        flush_amount = data["flush_amount"]
        config.log('''\
    Flushed Earnings         : {}'''
                   .format(none2zero(flush_amount)),
                   )
        config.log("\n" + UxString.flush_status % flush_amount, fg='green')


def status_shares(config, client):
    try:
        share_data = client.get_shares()
    except:
        share_data = None
    headers = ("", "Total", "Today", "Past Hour")
    data = []

    if share_data:
        try:
            for n in ["good", "bad"]:
                data.append(map(none2zero, [n, share_data["total"][n],
                                            share_data["today"][n],
                                            share_data["hour"][n]]))
        except KeyError:
            data = []  # config.log(UxString.Error.data_unavailable)

        if len(data):
            config.log("\nShare statistics:", fg="magenta")
            config.log(tabulate(data, headers=headers, tablefmt='psql'))
            # else:
            #    config.log(UxString.Error.data_unavailable)


def none2zero(x):
    # function to map None values of shares to 0
    return 0 if x is None else x
