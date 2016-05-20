""" Two1 command to rate a marketplace app """
# standard python imports
import logging

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1 import util
from two1.commands.util import uxstring
from two1.commands.util import exceptions
from two1.commands.util import decorators


# Creates a ClickLogger
logger = logging.getLogger(__name__)


@click.command()
@click.pass_context
@click.option('--list', is_flag=True, default=False,
              help='List all the apps that you have rated.')
@click.argument('app_id', required=False, type=click.STRING)
@click.argument('rating', required=False, type=click.INT)
@decorators.catch_all
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
    # pylint: disable=redefined-builtin
    if list:
        _list(ctx.obj["client"])
    else:
        if not (app_id and isinstance(rating, int)):
            # print help and exit
            logger.info(ctx.command.help)
            return
        _rate(ctx.obj["client"], app_id, rating)


def _list(client):
    """ Lists all of the apps that the user has rated

    If no apps have been rated, then an empty formatted list is printed

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.

    Raises:
        ServerRequestError: If server error occurs other than a 404
    """
    logger.info(uxstring.UxString.rating_list)

    try:
        ratings = client.get_ratings()
        headers = ["id", "App title", "Creator", "Rating", "Rating Date"]
        ratings = ratings.json()["ratings"]
        rows = []
        for rating in ratings:
            rating_date = util.format_date(rating["rating_date"])
            rating_score = "{}/5".format(rating["rating"])
            rows.append([rating["app_id"], rating["app_title"], rating["app_creator"],
                         rating_score, rating_date])

        logger.info(tabulate(rows, headers, tablefmt="simple"))

    except exceptions.ServerRequestError as e:
        if e.status_code == 404:
            logger.info(uxstring.UxString.no_ratings)
            return
        else:
            raise e


def _rate(client, app_id, rating):
    """ Rate an app listed in the marketplace

    Args:
        client (two1.server.rest_client.TwentyOneRestClient) an object for
            sending authenticated requests to the TwentyOne backend.
        app_id (str): Unique app id used to identify which app to rate
        rating (int): rating number (1-5)

    Raises:
        ServerRequestError: If any other server error occurs other than a 404
    """
    if rating < 1 or rating > 5:
        logger.info(uxstring.UxString.bad_rating, fg="red")
        return

    try:
        client.rate_app(app_id, rating)
    except exceptions.ServerRequestError as e:
        if e.status_code == 404:
            logger.info(uxstring.UxString.rating_app_not_found.format(app_id))
            return
        elif e.status_code == 400:
            logger.info(e.data['error'])
            return
        raise e

    logger.info(uxstring.UxString.rating_success.format(rating, app_id))
