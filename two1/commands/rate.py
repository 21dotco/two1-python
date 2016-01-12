"""
Rate the seller of a machine-payable endpoint
"""
import click
from two1.lib.server.rest_client import ServerRequestError
from two1.lib.util.uxstring import UxString
from two1.lib.server import rest_client
from two1.commands.config import TWO1_HOST


@click.command()
@click.pass_context
@click.option('--list', is_flag=True, default=False,
              help='Show the list of all the apps you have rated')
@click.argument('app_id', required=False, type=click.STRING)
@click.argument('rating', required=False, type=click.INT)
def rate(ctx, list, app_id, rating):
    """Rate a marketplace app.
\b
Usage
-----
Rate an app
$ 21 rate XYZ 3
    - XYZ is the id of the app you want to rate and can be found when searching for the app in the
      marketplace.
    - 3 is your rating. Ratings should be numbers between 1 to 5.
You can always change the rating for your app by doing another 21 rate.

\b
See all the apps that you have rates:
$ 21 rate --list
    """
    if list:
        _list(ctx.obj["config"])
    else:
        if not (app_id and rating):
            # print help and exit
            click.secho(ctx.command.help)
            return
        _rate(ctx.obj["config"], app_id, rating)


def _list(config):
    print("listing all the rated apps")


def _rate(config, app_id, rating):
    if rating < 1 or rating > 5:
        click.secho(UxString.bad_rating, fg="red")
        return

    client = rest_client.TwentyOneRestClient(TWO1_HOST,
                                             config.machine_auth,
                                             config.username)
    try:
        client.rate_app(app_id, rating)
    except ServerRequestError as e:
        if e.status_code == 404:
            click.secho(UxString.rating_app_not_found.format(app_id))
            return
        raise e

    click.secho(UxString.rating_success.format(rating, app_id))
    pass
