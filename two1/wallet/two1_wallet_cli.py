import click
import getpass

from two1.wallet.account_types import account_types
from two1.wallet.base_wallet import satoshi_to_btc
from two1.wallet.two1_wallet import Two1Wallet

WALLET_VERSION = "0.1.0"
CONTEXT_SETTINGS = dict(help_option_names=['-h', '--help'])

def get_passphrase():
    return getpass.getpass("Passphrase to unlock wallet: ")

@click.pass_context
def validate_txn_data_provider(ctx, param, value):
    txn_data_provider_params = {}
    if ctx.obj is None:
        ctx.obj = {}
    if value == 'chain':
        required = ['chain_api_key', 'chain_api_secret']

    fail = False
    for r in required:
        if r not in ctx.params:
            s = r.replace('_', '-')
            click.echo("--%s is required to use %s." % (s, value))
            fail = True
        else:
            txn_data_provider_params[r] = ctx.params[r]

    if fail:
        ctx.fail("One or more required arguments are missing.")

    ctx.obj['txn_data_provider'] = value
    ctx.obj['txn_data_provider_params'] = txn_data_provider_params
        
@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('--wallet-path', '-wp',
              default=Two1Wallet.DEFAULT_WALLET_PATH,
              metavar='PATH',
              show_default=True,
              help='Path to wallet file')
@click.option('--passphrase', '-p',
              is_flag=True,
              help='Prompt for a passphrase.')
@click.option('--transaction-data-provider', '-t',
              default='chain',
              type=click.Choice(['chain']),
              show_default=True,
              callback=validate_txn_data_provider,
              help='Transaction data provider service to use')
@click.option('--chain-api-key', '-ck',
              metavar='STRING',
              envvar='CHAIN_API_KEY',
              is_eager=True,
              help='Chain API Key (only if -t chain)')
@click.option('--chain-api-secret', '-cs',
              metavar='STRING',
              envvar='CHAIN_API_SECRET',
              is_eager=True,
              help='Chain API Secret (only if -t chain)')
@click.version_option(WALLET_VERSION)
@click.pass_context
def main(ctx, wallet_path, passphrase,
         transaction_data_provider, chain_api_key, chain_api_secret):
    """ Command-line Interface for the Two1 Wallet
    """
    if ctx.obj is None:
        ctx.obj = {}

    ctx.obj['wallet_path'] = wallet_path
    ctx.obj['passphrase'] = passphrase
    
    if ctx.invoked_subcommand != "create":
        p = get_passphrase() if passphrase else ''
            
        # instantiate a wallet object here and pass it into the context
        tdp = Two1Wallet.instantiate_data_provider(txn_data_provider_name=ctx.obj['txn_data_provider'],
                                                   txn_data_provider_params=ctx.obj['txn_data_provider_params'])
        ctx.obj['wallet'] = Two1Wallet(params_or_file=wallet_path,
                                       txn_data_provider=tdp,
                                       passphrase=p)

@click.command()
@click.option('--account-type', '-a',
              default=Two1Wallet.DEFAULT_ACCOUNT_TYPE,
              type=click.Choice(list(account_types.keys())),
              show_default=True,
              help='Type of account to create')
@click.option('--testnet', '-tn',
              is_flag=True,
              help="Create a testnet wallet.")
@click.pass_context
def create(ctx, account_type, testnet):
    """ Creates a new wallet
    """
    # txn_data_provider and related params come from the
    # global context.
    passphrase = ""    
    if ctx.obj['passphrase']:
        # Let's prompt for a passphrase
        conf = "a"
        i = 0
        while passphrase != conf and i < 3:
            passphrase = getpass.getpass("Enter desired passphrase: ")
            conf = getpass.getpass("Confirm passphrase: ")
            i += 1

        if passphrase != conf:
            ctx.fail("Passphrases don't match. Quitting.")

    options = {"account_type": account_type,
               "passphrase": passphrase,
               "txn_data_provider": ctx.obj['txn_data_provider'],
               "txn_data_provider_params": ctx.obj['txn_data_provider_params'],
               "testnet": testnet,
               "wallet_path": ctx.obj['wallet_path']}

    created = Two1Wallet.configure(options)

    if created:
        click.echo("Wallet successfully created!")
    else:
        ctx.fail("Wallet was not created.")

@click.command(name="payoutaddress")
@click.pass_context
def payout_address(ctx):
    """ Prints the current payout address
    """
    w = ctx.obj['wallet']
    click.echo(w.current_address)
        
@click.command(name="confirmedbalance")
@click.pass_context
def confirmed_balance(ctx):
    """ Prints the current confirmed balance
    """
    w = ctx.obj['wallet']
    click.echo("Confirmed balance: %f BTC" % (w.confirmed_balance() / satoshi_to_btc))

@click.command(name="unconfirmedbalance")
@click.pass_context
def unconfirmed_balance(ctx):
    """ Prints the current unconfirmed balance
    """
    w = ctx.obj['wallet']
    click.echo("Unconfirmed balance: %f BTC" % (w.unconfirmed_balance() / satoshi_to_btc))

@click.command(name="sendto")
@click.argument('address',
                metavar="STRING")
@click.argument('amount',
                type=click.FLOAT)
@click.option('--account',
              metavar="STRING",
              multiple=True)
@click.pass_context
def send_to(ctx, address, amount, account):
    """ Send bitcoin to a single address
    """
    w = ctx.obj['wallet']

    # Do we want to confirm if it's larger than some amount?
    satoshis = int(amount * satoshi_to_btc)
    print("Sending %d satoshis to %s from accounts = %r" % (satoshis, address, list(account)))

    try:
        txids = w.send_to(address=address,
                          amount=satoshis,
                          accounts=list(account))
        if txids:
            click.echo("Successfully sent %f BTC to %s. txid = %r" % (amount,
                                                                      address,
                                                                      [t['txid'] for t in txids]))
    except Exception as e:
        click.echo("Problem sending coins: %s" % e)
    
main.add_command(create)
main.add_command(payout_address)
main.add_command(confirmed_balance)
main.add_command(unconfirmed_balance)
main.add_command(send_to)
    
if __name__ == "__main__":
    main()
    
