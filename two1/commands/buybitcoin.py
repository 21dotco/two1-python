"""Buy bitcoin through Coinbase."""
# standard python imports
import logging

# 3rd party imports
import click

# two1 imports
from two1.commands.util import exceptions
from two1.commands.util import decorators
from two1.commands.util import uxstring
from two1.commands.util import currency
from two1 import util


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.option('--info', is_flag=True, default=False,
              help="Shows the current status of your exchange integrations.")
@click.option('--history', is_flag=True, default=False,
              help="Shows your history of Bitcoin purchases.")
@click.option('--price', is_flag=True, default=False,
              help="Quotes the price of Bitcoin.")
@click.argument('amount', default=0.0, type=click.FLOAT)
@click.argument('denomination', default='', type=click.STRING)
@click.pass_context
@decorators.catch_all
@decorators.capture_usage
def buybitcoin(ctx, info, amount, denomination, history, price):
    """Buy bitcoin through Coinbase.

\b
To use this command, you need to connect your 21 account with your Coinbase account.
You can find the instructions here: https://21.co/learn/21-buybitcoin/

\b
Quote the price of 100000 satoshis.
$ 21 buybitcoin 1000000 --price

\b
Buy 100000 satoshis from Coinbase.
$ 21 buybitcoin 100000 satoshis
You can use the following denominations: satoshis, bitcoins, and USD.

\b
Buy 5 dollars of bitcoin from Coinbase.
$ 21 buybitcoin 5 usd

\b
See history of your purchases.
$ 21 buybitcoin --history

\b
See the status of your 21 and Coinbase account integration.
$ 21 buybitcoin --info


The Bitcoins you purchase through this command will be deposited to
your local wallet.

If you have Instant Buy enabled on your Coinbase account, the purchase
will be immediate. If you don't have Instant Buy, it may take up to 5
days for the purchase to be completed.

    """
    exchange = "coinbase"
    if amount != 0.0:
        if denomination == '':
            confirmed = click.confirm(uxstring.UxString.default_price_denomination, default=True)
            if not confirmed:
                raise exceptions.Two1Error(uxstring.UxString.cancel_command)
            denomination = currency.Price.SAT
        amount = currency.Price(amount, denomination).satoshis
    return _buybitcoin(ctx, ctx.obj['config'], ctx.obj['client'], info, exchange, amount,
                       history, price, denomination)


def _buybitcoin(ctx, config, client, info, exchange, amount, history, price, denomination):
    if history:
        return buybitcoin_history(config, client, exchange)
    elif price:
        return quote_bitcoin_price(config, client, exchange, amount, denomination)
    else:
        if info:
            return buybitcoin_show_info(config, client, exchange)
        elif amount <= 0:
            logger.info(buybitcoin.get_help(ctx))
        else:
            return buybitcoin_buy(config, client, exchange, amount)


def buybitcoin_show_info(config, client, exchange):
    resp = client.get_coinbase_status()
    if not resp.ok:
        raise exceptions.Two1Error("Failed to get exchange status")

    coinbase = resp.json().get("coinbase")

    if not coinbase:
        # Not linked, prompt user to info
        return buybitcoin_config(config, client, exchange)
    else:
        payment_method_string = click.style("No Payment Method linked yet.", fg="red", bold=True)
        if coinbase["payment_method"] is not None:
            payment_method_string = coinbase["payment_method"]["name"]

        logger.info(uxstring.UxString.exchange_info_header)
        logger.info(uxstring.UxString.exchange_info.format(exchange.capitalize(), coinbase["name"],
                                                           coinbase["account_name"], payment_method_string))
        if coinbase["payment_method"] is None:
            ADD_PAYMENT_METHOD_URL = "https://coinbase.com/quickstarts/payment"
            logger.info(uxstring.UxString.buybitcoin_no_payment_method.format(
                exchange.capitalize(),
                click.style(ADD_PAYMENT_METHOD_URL, fg="blue", bold=True)
            ))
        else:
            logger.info(uxstring.UxString.buybitcoin_instruction_header)
            logger.info(uxstring.UxString.buybitcoin_instructions.format(exchange.capitalize()))
        return coinbase


def buybitcoin_history(config, client, exchange):
    resp = client.get_coinbase_status()
    if not resp.ok:
        raise exceptions.Two1Error("Failed to get exchange status")

    coinbase = resp.json()["coinbase"]

    if not coinbase:
        # Not linked, prompt user to info
        return buybitcoin_config(config, client, exchange)
    else:
        resp = client.get_coinbase_history()
        history = resp.json()["history"]

        lines = [uxstring.UxString.coinbase_history_title]

        for entry in history:
            amount = entry["amount"]
            deposit_status = entry["deposit_status"]
            payout_time = util.format_date(entry["payout_time"])
            payout_address = entry["payout_address"]

            description = "N/A"
            if deposit_status == "COMPLETED":
                description = uxstring.UxString.coinbase_wallet_completed.format(payout_time)
            else:
                description = uxstring.UxString.coinbase_wallet_pending.format(payout_time)

            created = util.format_date(entry["created"])
            lines.append(uxstring.UxString.coinbase_history.format(
                created, amount, payout_address, description))

        if len(history) == 0:
            lines.append(uxstring.UxString.coinbase_no_bitcoins_purchased)

        prints = "\n\n".join(lines)
        logger.info(prints, pager=True)


def quote_bitcoin_price(config, client, exchange, amount, denomination):
    amount = amount or 1e8
    result = client.quote_bitcoin_price(amount)
    data = result.json()
    price = data["price"]

    if price >= 0.1:
        price = '{:.2f}'.format(price)
    else:
        price = '{:.7f}'.format(price).rstrip('0')

    btc_unit = data["bitcoin_unit"].lower()
    currency_unit = data["currency_unit"]
    if denomination in 'usd':
        logger.info(
            uxstring.UxString.coinbase_quote_price_dollars.format(
                int(amount), btc_unit, price, currency_unit))
    else:
        logger.info(
            uxstring.UxString.coinbase_quote_price_satoshis.format(
                int(amount), btc_unit, price, currency_unit))


def buybitcoin_config(config, client, exchange):
    logger.info(uxstring.UxString.buybitcoin_pairing.format(click.style(exchange.capitalize()), config.username))


def buybitcoin_buy(config, client, exchange, amount):

    resp = client.get_coinbase_status()
    if not resp.ok:
        raise exceptions.Two1Error("Failed to get exchange status")

    coinbase = resp.json().get("coinbase")

    if not coinbase:
        return buybitcoin_config(config, client, exchange)

    try:
        get_price_quote(client, amount)
    except ValueError:
        return

    try:
        buy_bitcoin(client, amount)
    except click.exceptions.Abort:
        logger.info("\nPurchase canceled", fg="magenta")


def get_price_quote(client, amount):
    # first get a quote
    try:
        resp = client.buy_bitcoin_from_exchange(amount, "satoshis", commit=False)
    except exceptions.ServerRequestError as e:
        if e.status_code == 400:
            if e.data.get("error") == "TO700":
                logger.info(uxstring.UxString.minimum_bitcoin_purchase)
            elif e.data.get("error") == "TO704":
                logger.info(uxstring.UxString.coinbase_amount_too_high)
            raise ValueError()
        elif e.status_code == 403:
            if e.data.get("error") == "TO703":
                logger.info(uxstring.UxString.coinbase_max_buy_reached)
            raise ValueError()

    buy_result = resp.json()
    if "err" in buy_result:
        logger.info(uxstring.UxString.buybitcoin_error.format(
            click.style(buy_result["err"], bold=True, fg="red")))
        raise exceptions.Two1Error("Failed to execute buybitcoin {} {}".format(amount, "satoshis"))

    fees = buy_result["fees"]
    total_fees = ["{:.2f} {} {} {}".format(
                  float(fee["amount"]["amount"]), fee["amount"]["currency"],
                  "fee from your" if fee["type"] == "bank" else "fee from",
                  "Coinbase" if fee["type"] == "coinbase" else fee["type"])
                  for fee in fees]
    total_fees = click.style(" and ".join(total_fees), bold=True)
    total_amount = buy_result["total"]
    total = click.style("{} {}".format(total_amount["amount"], total_amount["currency"]), bold=True)
    bitcoin_amount = click.style("{} {}".format(int(amount), "satoshis"), bold=True)

    logger.info(uxstring.UxString.buybitcoin_confirmation.format(total, bitcoin_amount, total, total_fees))


def buy_bitcoin(client, amount):
    if click.confirm(uxstring.UxString.buybitcoin_confirmation_prompt):
        logger.info(uxstring.UxString.coinbase_purchase_in_progress)
        try:
            resp = client.buy_bitcoin_from_exchange(amount, "satoshis", commit=True)
        except exceptions.ServerRequestError as e:
            PHOTO_ID_ERROR = "Before you will be able to complete this buy, "\
                "you must provide additional information at "\
                "https://www.coinbase.com/photo-id"
            USERNAME_ERROR = "To process payments we require a valid user name. "\
                "Please go to settings to update your information."
            if e.status_code == 403 and e.data.get("error") == "TO703":
                logger.error(uxstring.UxString.coinbase_max_buy_reached)
                return
            elif e.status_code == 500 and e.data.get("error") == PHOTO_ID_ERROR:
                logger.error(uxstring.UxString.coinbase_needs_photo_id)
                return
            elif e.status_code == 500 and e.data.get("error") == USERNAME_ERROR:
                logger.error(uxstring.UxString.coinbase_needs_username)
                return

        buy_result = resp.json()
        if buy_result["status"] == "canceled":
            logger.info(uxstring.UxString.buybitcoin_error.format(
                click.style("Buy was canceled.", bold=True, fg="red")))

            return buy_result

        amount_bought = int(float(buy_result["amount"]["amount"]) * 1e8)
        btc_bought = "{} {}".format(amount_bought, 'satoshis')

        dollars_paid = "{} {}".format(buy_result["total"]["amount"],
                                      buy_result["total"]["currency"])

        logger.info(uxstring.UxString.buybitcoin_success.format(btc_bought, dollars_paid))

        if "instant" in buy_result and buy_result["instant"]:
            logger.info(uxstring.UxString.buybitcoin_success_instant)
        elif "payout_at" in buy_result:
            payout_time = util.format_date(buy_result["payout_at"])

            logger.info(uxstring.UxString.buybitcoin_success_payout_time.format(payout_time))
    else:
        logger.info("\nPurchase canceled", fg="magenta")
