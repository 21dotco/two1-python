# standard python imports
import datetime

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1.lib.server import rest_client
from two1.commands.util import uxstring
from two1.commands.util import exceptions


@click.command()
@click.pass_context
@click.option('--list', is_flag=True, default=False,
              help='List all the apps that you have rated.')
@click.argument('app_id', required=False, type=click.STRING)
@click.argument('rating', required=False, type=click.INT)
def rate(ctx, list, app_id, rating):
    """Rate an app listed in the 21 Marketplace.

\b
Usage
_____
Rate an app.
$ 21 rate Xe8 3
    - Xe8 is the id of the app that you want to rate.  This id can be found with `21 search`.
    - 3 is the rating to apply. A rating should be an integer between 1-5.
You can update the rating for an app at anytime with `21 rate`.


\b
List all the apps that you have rated.
$ 21 rate --list
    """
    #pylint: disable=redefined-builtin
    if list:
        _list(ctx.obj["config"], ctx.obj["client"])
    else:
        if not (app_id and rating):
            # print help and exit
            click.secho(ctx.command.help)
            return
        _rate(ctx.obj["config"], ctx.obj["client"], app_id, rating)


def _list(config, client):
    """ Lists all of the apps that the user has rated

    If no apps have been rated, then an empty formatted list is printed

    Args:
        config (Config): Config object used for user specific information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.

    Raises:
        ServerRequestError: If server error occurs other than a 404
    """
    click.secho(uxstring.UxString.rating_list)

    try:
        ratings = client.get_ratings()
        headers = ["id", "App title", "Creator", "Rating", "Rating Date"]
        ratings = ratings.json()["ratings"]
        rows = []
        for rating in ratings:
            rating_date = datetime.datetime.fromtimestamp(
                rating["rating_date"]).strftime("%Y-%m-%d %H:%M")
            rating_score = "{}/5".format(rating["rating"])
            rows.append([rating["app_id"], rating["app_title"], rating["app_creator"],
                         rating_score, rating_date])

        click.echo(tabulate(rows, headers, tablefmt="grid"))

    except exceptions.ServerRequestError as e:
        if e.status_code == 404:
            click.secho(uxstring.UxString.no_ratings)
            return
        else:
            raise e


def _rate(config, client, app_id, rating):
    """ Rate an app listed in the marketplace

    Args:
        config (Config): Config object used for user specific information
        client (two1.lib.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        app_id (str): Unique app id used to identify which app to rate
        rating (int): rating number (1-5)

    Raises:
        ServerRequestError: If any other server error occurs other than a 404
    """
    if rating < 1 or rating > 5:
        click.secho(uxstring.UxString.bad_rating, fg="red")
        return

    try:
        client.rate_app(app_id, rating)
    except exceptions.ServerRequestError as e:
        if e.status_code == 404:
            click.secho(uxstring.UxString.rating_app_not_found.format(app_id))
            return
        raise e

    click.secho(uxstring.UxString.rating_success.format(rating, app_id))
