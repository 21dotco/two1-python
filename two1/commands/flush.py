import click
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.uxstring import UxString


@click.command()
@click.pass_context
def flush(ctx):
    """Flush your 21.co buffer to the blockchain.

"""
    config = ctx.obj['config']
    _flush(config)


@capture_usage
def _flush(config):
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    flush_earnings(config, client)

    config.log("")


def flush_earnings(config, client):
    try:
        response = client.flush_earnings()
        if response.ok:
            success_msg = UxString.flush_success.format(
                click.style("Flush to Blockchain", fg='magenta'),
                config.wallet.current_address,
                click.style("21 mine", bold=True)
                )
            config.log(success_msg, nl=False)
    except ServerRequestError as e:
        if e.status_code == 401:
            click.echo(UxString.flush_insufficient_earnings)
        else:
            raise e

