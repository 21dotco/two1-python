import click
import subprocess
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST
from two1.lib.server.analytics import capture_usage
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.uxstring import UxString
from two1.lib.util import zerotier


@click.command()
@click.argument("network")
@click.pass_context
def join(ctx, network):
    """Join a peer2peer network over zerotier.

\b
Usage
-----
21 join 21market
"""
    config = ctx.obj['config']
    _join(config, network)


@capture_usage
def _join(config, network):
    """Perform the rest_client join"""
    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)

    try:
        config.log(UxString.update_superuser)
        start_zerotier_command = [
            "sudo", "service", "zerotier-one", "start"
        ]
        subprocess.check_output(start_zerotier_command)
        zt_device_address = zerotier.device_address()
        response = client.join(network, zt_device_address)
        if response.ok:
            join_command = [
                "sudo", "zerotier-cli", "join",
                response.json().get("networkid")
            ]
            subprocess.check_output(join_command)
            config.log(UxString.successful_join.format(
                click.style(network, fg="magenta")
                )
            )
    except ServerRequestError as e:
        if e.status_code == 401:
            config.log(UxString.invalid_network)
        else:
            raise e
    except subprocess.CalledProcessError as e:
        config.log(str(e))
