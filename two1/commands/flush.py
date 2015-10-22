import click
from two1.commands.config import pass_config
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.util.uxstring import UxString


@click.command()
@click.pass_context
def flush(ctx):
    """Flush your 21.co balance to the blockchain.

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
    response = client.flush_earnings(config.username)
    if response.ok:
        config.log(UxString.flush_success)
    else:
        config.log(UxString.Error.server_err)
