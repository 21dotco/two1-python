import click
from two1.commands.config import TWO1_HOST, TWO1_WEB_HOST
from two1.lib.util.exceptions import TwoOneError
from two1.lib.server import rest_client
from two1.lib.server.analytics import capture_usage
from two1.lib.util.decorators import json_output
from two1.lib.util.uxstring import UxString


@click.group(invoke_without_command=True)
@click.option('-e', '--exchange', default='coinbase', type=click.Choice(['coinbase']),
              help="Select the exchange to buy Bitcoins from")
@click.option('--pair', is_flag=True, default=False,
              help="Connects your Bitcoin Computer to your exchange account")
@click.argument('amount', default=0, type=click.FLOAT)
@click.argument('unit', default='satoshi', type=click.Choice(['usd', 'btc', 'satoshi']))
@json_output
def buybitcoin(click_config, pair, exchange, amount, unit):
    """Buy Bitcoins from an exchange
    """
    return _buybitcoin(click_config, pair, exchange, amount, unit)


@capture_usage
def _buybitcoin(click_config, pair, exchange, amount, unit):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             click_config.machine_auth,
                                             click_config.username)

    if pair:
        return buybitcoin_config(click_config, client, exchange)
    else:
        if amount <= 0:
            return buybitcoin_show_status(click_config, client, exchange)
        else:
            return buybitcoin_buy(click_config, client, exchange, amount, unit)


def buybitcoin_show_status(config, client, exchange):
    resp = client.get_coinbase_status()
    if not resp.ok:
        raise TwoOneError("Failed to get exchange status")

    coinbase = resp.json()["coinbase"]

    if not coinbase:
        # Not linked, prompt user to pair
        return buybitcoin_config(config, client, exchange)
    else:
        payment_method_string = click.style("No Payment Method linked yet.", fg="red", bold=True)
        if coinbase["payment_method"] is not None:
            payment_method_string = "Linked Payment Method: {}".format(
                click.style(coinbase["payment_method"]["name"], fg="magenta", bold=True))
        config.log(UxString.buybitcoin_exchange_status.format(
                click.style(exchange.capitalize(), fg="yellow"),
                click.style(coinbase["name"], fg="cyan", bold=True),
                click.style(coinbase["account_name"], fg="magenta", bold=True),
                payment_method_string
        ))
        if coinbase["payment_method"] is None:
            ADD_PAYMENT_METHOD_URL = "https://coinbase.com/quickstarts/payment"
            config.log(UxString.buybitcoin_no_payment_method.format(
                    exchange.capitalize(),
                    click.style(ADD_PAYMENT_METHOD_URL, fg="blue", bold=True)
            ))
        else:
            config.log(UxString.buybitcoin_instructions.format(exchange.capitalize()))
        return coinbase


def buybitcoin_config(config, client, exchange):
    config.log(UxString.buybitcoin_pairing.format(click.style(exchange.capitalize()),
                                                  config.username))


def buybitcoin_buy(config, client, exchange, amount, unit):
    config.log(UxString.buybitcoin_buying.format(
            click.style(str(amount), bold=True),
            click.style(unit, bold=True)
    ))
    resp = client.buy_bitcoin_from_exchange(amount, unit)
    if not resp.ok:
        raise TwoOneError("Failed to execute buybitcoin {} {}".format(amount, unit))
    buy_result = resp.json()
    if "err" in buy_result:
        config.log(
            UxString.buybitcoin_error.format(click.style(buy_result["err"], bold=True, fg="red")))
        return buy_result

    if buy_result["status"] == "canceled":
        config.log(
            UxString.buybitcoin_error.format(click.style("Buy was canceled.", bold=True, fg="red")))
        return buy_result

    # success
    config.log(
            UxString.buybitcoin_success.format(
                    click.style("{} {}".format(buy_result["amount"]["amount"],
                                               buy_result["amount"]["currency"]), bold=True),
                    click.style("{} {}".format(buy_result["total"]["amount"],
                                               buy_result["total"]["currency"]), bold=True),
            )
    )

    if "payout_at" in buy_result:
        config.log(UxString.buybitcoin_success_payout_time.format(buy_result["payout_at"]))

    # if instant buy, transfer the funds into your bitcoin account now
    if buy_result["instant"] and buy_result["amount"]["currency"] == "BTC":
        resp = client.send_bitcoin_from_exchange(buy_result["amount"]["amount"])
        if not resp.ok:
            raise TwoOneError("Failed to send bitcoin from {} to your 21 wallet.".format(exchange))
        send_result = resp.json()
        # print(send_result)
        config.log(UxString.buybitcoin_success_instant)
        buy_result["send"] = send_result

    return buy_result
