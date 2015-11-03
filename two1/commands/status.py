import click
from tabulate import tabulate
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
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
            if chunk == b"":
                s.close()
                break

            buf += chunk
            while b"\n" in buf:
                pos = buf.find(b"\n")
                data = buf[0:pos].decode('utf-8')
                buf = buf[pos+1:]
                event = json.loads(data)
                if (event['type'] == "StatisticsEvent"):
                    # 5min, 15min, 60min Hashrate
                    hashrate = max( event['payload']['statistics']['hashrate'][i] for i in ("5min", "15min", "60min"))
                    break
            if hashrate:
                break
    except:
        pass
    # non zero hashrate
    if hashrate > 1.0:
        ret = "~{0:.1f} GH/s".format(hashrate / 1e+9)
    else:
        ret = UxString.Error.data_unavailable
    return ret


def status_mining(config, client):
    has_chip = has_bitcoinkit()
    if has_chip:
        bk = "21 mining chip running (/run/minerd.pid)"
        mined = client.get_mined_satoshis()
        hashrate = get_hashrate()
    else:
        bk, mined, hashrate = None, None, None
    data = dict(mining=click.style("Mining", fg='magenta'),
                is_mining=bk,
                hashrate=hashrate,
                mined=mined,
                minecmd=click.style("21 mine --dashboard", bold=True))
    if has_chip:
        out = UxString.status_mining.format(**data)
        config.log(out)


@click.command()
@click.option("--json/--no-json", default=False)
@click.pass_context
def status(ctx, json):
    """View your bitcoin balance and address.
    """
    config = ctx.obj['config']
    _status(config)


@capture_usage
def _status(config):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
    status_account(config)
    status_mining(config, client)
    status_wallet(config, client)

    config.log("")
    # status_endpoints(config)
    # status_bought_endpoints(config)


def status_account(config):

    status_account = UxString.status_account.format(
        account=click.style("21.co Account", fg='magenta'),
        username=config.username,
        address=config.wallet.current_address)
    config.log(status_account)

SEARCH_UNIT_PRICE = 800
ARTICLE_UNIT_PRICE = 4000
MESSAGE_UNIT_PRICE = 8000


def status_wallet(config, client):
    """Print wallet status to the command line.
    """
    twentyone_balance, onchain, pending_transactions, flushed_earnings = \
        _get_balances(config, client)

    try:
        bitcoin_address = config.wallet.current_address
    except AttributeError:
        bitcoin_address = "Not Set"

    status_wallet = UxString.status_wallet.format(balance=click.style("Balance", fg='magenta'),
                                                  twentyone_balance=twentyone_balance,
                                                  onchain=onchain,
                                                  flushing=flushed_earnings,
                                                  )
    config.log(status_wallet)
    total_balance = twentyone_balance + onchain
    buyable_searches = int(total_balance / SEARCH_UNIT_PRICE)
    buyable_articles = int(total_balance / ARTICLE_UNIT_PRICE)
    buyable_messages = int(total_balance / MESSAGE_UNIT_PRICE)
    status_buyable = UxString.status_buyable.format(
        click.style("How many API calls can you buy?", fg='magenta'),
        buyable_searches,
        SEARCH_UNIT_PRICE,
        buyable_articles,
        ARTICLE_UNIT_PRICE,
        buyable_messages,
        MESSAGE_UNIT_PRICE)
    config.log(status_buyable, nl=False)

    if total_balance == 0:
        config.log(UxString.status_empty_wallet.format(click.style("21 mine",
                                                                   bold=True)))
    else:
        buy21 = click.style("21 buy", bold=True)
        buy21help = click.style("21 buy --help", bold=True)
        config.log(UxString.status_exit_message.format(buy21, buy21help),
                   nl=False)


def _get_balances(config, client):
    balance_c = config.wallet.confirmed_balance()
    balance_u = config.wallet.unconfirmed_balance()
    pending_transactions = balance_u - balance_c

    data = client.get_earnings()
    twentyone_balance = data["total_earnings"]
    flushed_earnings = data["flush_amount"]

    return twentyone_balance, balance_c, pending_transactions, flushed_earnings


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
