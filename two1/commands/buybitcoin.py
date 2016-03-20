# standard python imports
from datetime import datetime
import logging

# 3rd party imports
import click

# two1 imports
from two1.commands.util import exceptions
from two1.commands.util import decorators
from two1.commands.util import uxstring


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.option('--info', is_flag=True, default=False,
              help="Shows instructions on how to connect you Bitcoin Computer to an exchange "
                   "account")
@click.option('--status', is_flag=True, default=False,
              help="Shows the current status of your exchange integrations")
@click.option('--history', is_flag=True, default=False,
              help="Shows your history of Bitcoin purchases")
@click.argument('amount', default=0, type=click.FLOAT)
@click.pass_context
@decorators.catch_all
@decorators.json_output
@decorators.capture_usage
def buybitcoin(ctx, info, status, amount, history):
    """Buy Bitcoins from Coinbase

To use this command, you need to connect your 21 account with your Coinbase account.
Use 21 buybitcoin --info to see instructions on how to do so.

\b
Buy 100000 Satoshis from Coinbase
$ 21 buybitcoin 100000

\b
See history of your purchases
$ 21 buybitcoin --history

\b
See the status of your 21 and Coinbase account integration
$ 21 buybitcoin --status

\b
See instructions on how to integrate your 21 and Coinbase account
$ 21 buybitcoin --info


When you buy Bitcoins through this command, you can decide where the Bitcoins will be deposited to.

    1- 21.co balance: The Bitcoins will be immediately deposited to your 21.co balance which is available for off chain purchases.\n
    2- Blockchain balance: The Bitcoins will be deposited to the wallet on your 21 Bitcoin Computer once your purchase completes on Coinbase. If you have Instant Buy enabled on your Coinbase account the purchase will be immediate. If you don't have Instant Buy, it may take up to 5 days for the purchase to be completed.
\b
    """
    exchange = "coinbase"
    return _buybitcoin(ctx.obj['config'], ctx.obj['client'], info, status, exchange, amount, history)


def _buybitcoin(config, client, info, status, exchange, amount, history):
    if info:
        return buybitcoin_config(config, client, exchange)
    elif history:
        return buybitcoin_history(config, client)
    else:
        if amount <= 0 or status:
            return buybitcoin_show_status(config, client, exchange)
        else:
            return buybitcoin_buy(config, client, exchange, amount)


def buybitcoin_show_status(config, client, exchange):
    resp = client.get_coinbase_status()
    if not resp.ok:
        raise exceptions.Two1Error("Failed to get exchange status")

    coinbase = resp.json()["coinbase"]

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


def buybitcoin_history(config, client):
    resp = client.get_coinbase_history()
    history = resp.json()["history"]

    lines = [uxstring.UxString.coinbase_history_title]

    for entry in history:
        amount = entry["amount"]
        deposit_status = entry["deposit_status"]
        payout_time = datetime.fromtimestamp(entry["payout_time"]).strftime("%Y-%m-%d %H:%M:%S")

        description = "N/A"
        if deposit_status == "COMPLETED":
            if entry["payout_type"] == "WALLET":
                description = uxstring.UxString.coinbase_wallet_completed.format(payout_time)
            elif entry["payout_type"] == "TO_BALANCE":
                description = uxstring.UxString.coinbase_21_completed.format(payout_time, amount)
        else:
            if entry["payout_type"] == "WALLET":
                description = uxstring.UxString.coinbase_wallet_pending.format(payout_time)
            elif entry["payout_type"] == "TO_BALANCE":
                description = uxstring.UxString.coinbase_21_pending.format(payout_time, amount)

        created = datetime.fromtimestamp(entry["created"]).strftime("%Y-%m-%d %H:%M:%S")
        payout_type = uxstring.UxString.coinbase_deposit_type_mapping[entry["payout_type"]]
        lines.append(uxstring.UxString.coinbase_history.format(created, amount, payout_type, description))

    if len(history) == 0:
        lines.append(uxstring.UxString.coinbase_no_bitcoins_purchased)

    prints = "\n\n".join(lines)
    logger.info(prints, pager=True)


def buybitcoin_config(config, client, exchange):
    logger.info(uxstring.UxString.buybitcoin_pairing.format(click.style(exchange.capitalize()), config.username))


def buybitcoin_buy(config, client, exchange, amount):
    deposit_type = get_deposit_info()
    get_price_quote(client, amount, deposit_type)

    try:
        buy_bitcoin(client, amount, deposit_type)
    except click.exceptions.Abort:
        logger.info("\nPurchase canceled", fg="magenta")


def get_price_quote(client, amount, deposit_type):
    # first get a quote
    resp = client.buy_bitcoin_from_exchange(amount, "Satoshis", commit=False)

    if not resp.ok:
        raise exceptions.Two1Error("Failed to execute buybitcoin {} {}".format(amount, "Satoshis"))

    buy_result = resp.json()
    if "err" in buy_result:
        # TODO: remove the secho and use the exception to print message
        logger.info(uxstring.UxString.buybitcoin_error.format(click.style(buy_result["err"], bold=True, fg="red")))
        raise exceptions.Two1Error("Failed to execute buybitcoin {} {}".format(amount, "Satoshis"))

    fees = buy_result["fees"]
    total_fees = ["{} {}".format(float(f["amount"]["amount"]), f["amount"]["currency"]) for f in
                  fees]
    total_fees = click.style(" + ".join(total_fees), bold=True)
    total_amount = buy_result["total"]
    total = click.style("{} {}".format(total_amount["amount"], total_amount["currency"]), bold=True)
    bitcoin_amount = click.style("{} {}".format(int(amount), "Satoshis"), bold=True)

    deposit_type = {"TO_BALANCE": "21.co balance", "WALLET": "Blockchain balance"}[deposit_type]
    logger.info(uxstring.UxString.buybitcoin_confirmation.format(total, bitcoin_amount, total, total_fees,
                                                                 deposit_type))


def buy_bitcoin(client, amount, deposit_type):
    if click.confirm(uxstring.UxString.buybitcoin_confirmation_prompt):
        logger.info(uxstring.UxString.coinbase_purchase_in_progress)
        resp = client.buy_bitcoin_from_exchange(amount, "satoshi", commit=True,
                                                deposit_type=deposit_type)
        buy_result = resp.json()
        if buy_result["status"] == "canceled":
            logger.info(uxstring.UxString.buybitcoin_error.format(click.style("Buy was canceled.", bold=True, fg="red")))

            return buy_result

        amount_bought = int(float(buy_result["amount"]["amount"]) * 1e8)
        btc_bought = "{} {}".format(amount_bought,
                                    buy_result["amount"]["currency"])

        dollars_paid = "{} {}".format(buy_result["total"]["amount"],
                                      buy_result["total"]["currency"])

        logger.info(uxstring.UxString.buybitcoin_success.format(btc_bought, dollars_paid))

        if deposit_type == "TO_BALANCE":
            logger.info(uxstring.UxString.buybitcoin_21_balance_success)
            if "payout_at" in buy_result:
                payout_time = datetime.fromtimestamp(buy_result["payout_at"]).strftime("%Y-%m-%d "
                                                                                       "%H:%M:%S")

                logger.info(uxstring.UxString.buybitcoin_21_balance_time.format(payout_time,
                                                                                int(amount_bought),
                                                                                "Satoshis"))

        elif "instant" in buy_result and buy_result["instant"]:
            logger.info(uxstring.UxString.buybitcoin_success_instant)
        elif "payout_at" in buy_result:
            payout_time = datetime.fromtimestamp(buy_result["payout_at"]).strftime("%Y-%m-%d "
                                                                                   "%H:%M:%S")

            logger.info(uxstring.UxString.buybitcoin_success_payout_time.format(payout_time))
    else:
        logger.info("\nPurchase canceled", fg="magenta")


def get_deposit_info():
    logger.info(uxstring.UxString.deposit_type_question)
    deposit_types = [{"msg": uxstring.UxString.deposit_type_off_chain, "value": "TO_BALANCE"},
                     {"msg": uxstring.UxString.deposit_type_on_chain, "value": "WALLET"}]
    index_to_deposit = {}
    for i, deposit_type in enumerate(deposit_types):
        logger.info("{}. {}".format(i + 1, deposit_type["msg"]))
        index_to_deposit[i] = deposit_types[i]["value"]

    logger.info(uxstring.UxString.deposit_type_explanation)
    try:
        deposit_index = -1
        while deposit_index <= 0 or deposit_index > len(deposit_types):
            deposit_index = click.prompt(uxstring.UxString.deposit_type_prompt, type=int)
            if deposit_index <= 0 or deposit_index > len(deposit_types):
                logger.info(uxstring.UxString.deposit_type_invalid_index.format(1, len(deposit_types)))

        deposit_type = index_to_deposit[deposit_index - 1]
        return deposit_type

    except click.exceptions.Abort:
        raise exceptions.UnloggedException(click.style("\nPurchase canceled", fg="magenta"))
