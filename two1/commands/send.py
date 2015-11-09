import decimal
import subprocess
import click
from two1.lib.wallet.cli import send_to

send = send_to

# from two1.lib.wallet.base_wallet import convert_to_btc
# from two1.lib.util.decorators import json_output

# @click.command("send")
# @click.argument('address', type=click.STRING)
# @click.argument('satoshis', type=click.INT)
# @json_output
# def send(config, address, satoshis):
#     """Send the specified address some satoshis.

# \b
# Usage
# -----
# Mine bitcoin at 21.co, flush it to the Blockchain, and then send 5000
# to the Apache Foundation.
# $ 21 mine
# $ 21 flush
# # Wait ~10-20 minutes for flush to complete and block to mine
# $ 21 send 1BtjAzWGLyAavUkbw3QsyzzNDKdtPXk95D 1000 
# """
#     btc = str(convert_to_btc(satoshis))
#     return subprocess.check_output(["wallet","sendto", address, btc])
    
    # w = config.wallet.w
    # FEES = 0
    # balance = w.confirmed_balance()
    # if balance > satoshis + FEES:
    #     txids = w.send_to(address=address,
    #                       amount=satoshis)
    # else:
    #     click.echo("Insufficient Blockchain balance of %s satoshis.\n"\
    #                "Cannot send %s satoshis to %s.\n"\
    #                "Do %s, then %s to increase your Blockchain balance." %
    #                (balance, satoshis, address,
    #                 click.style("21 mine", bold=True),
    #                 click.style("21 flush", bold=True)))
    #     txids = []
    # return txids

    
    
