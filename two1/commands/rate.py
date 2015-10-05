from math import floor

import click
from two1.config import pass_config, TWO1_HOST, TWO1_DEV_HOST
from two1.lib import login
from two1.lib.rest_client import TwentyOneRestClient
from two1.lib.machine_auth import MachineAuth
#from decimal import Decimal, localcontext, ROUND_DOWN


@click.command()
@click.argument('purchase', nargs=1)
@click.argument('rating', nargs=1, type=click.FLOAT)
#@click.option('--review', prompt=False, default=None,
#              help='A written review of the sale')
@pass_config
def rate(config, purchase, rating):
    """Rate the purchase.

    Args:

        purchase (str): uuid of the purchased service that you wish to rate
        rating (float): rating as a number from 0.0 - 5.0 (higher the better)
        review (Optional[str]): a written review of the sale

    Returns:

        response of successful completion, raises error, or error message

    Raises:

        BadParameter: rating is invalid

    Example:

        $ two1 rate 0d66c381-77ad-4448-b6ab-ba45b6307b22 4.1
    """

    try:
        clean_rating = round(rating, 1)
    except Exception as e:
        config.log(str(e), fg="red")
        raise click.BadParameter('Error: issue with rounding rating')

    if clean_rating < 0.0 or clean_rating > 5.0:
        raise click.BadParameter('Rating should be a number between 0.0 - 5.0')

    # Note: Testing using TWO1_DEV_HOST (dev) instead of TWO1_HOST (live)
    try:
        rest_client = TwentyOneRestClient(TWO1_DEV_HOST,
                                          MachineAuth, config.username)

        # GET, r.status_code == 200 purchase_id exists do PUT, 404 does not exist and do POST
        r = rest_client.mmm_rating_get(purchase, clean_rating)

        #if (purchase == None):
        #    print("TODO: Use last transaction")

        # Do a PUT because purchase uuid exists
        if (r.status_code == 200):

            # Get current number of updates
            response_data = r.json()
            num_updates = response_data["num_updates"]

            r_put = rest_client.mmm_rating_put(purchase, clean_rating, num_updates)
            if (r_put.status_code == 200):  # 200 == PUT, Success
                click.echo("Success! You replaced purchase %s's old rating with the new rating of %s" % (purchase, clean_rating))
            else:
                click.echo("Error: Unable to update, you had a previous rating for this purchase.")

        # Do a POST because purchase uuid does not exist
        else:
            r_post = rest_client.mmm_rating_post(purchase, clean_rating)
            #click.echo('You input a Rating of %s to %s' % (clean_rating, purchase))
            if (r_post.status_code == 201):  # 201 == Created, Success
                click.echo("Success! You created a rating of %s for %s" % (purchase, clean_rating))
            elif (r_post.status_code == 400):
                click.echo("Error: Bad request: check if purchase uuid is valid")
                #click.exit_code = 1
                #raise click.UsageError("Error: Bad request, check if purchase uuid is valid")
            else:
                click.echo("Error: Unable to create a rating for %s" % (purchase))


        # Record the purchase
        #config.log('You gave %s a rating of %s' % (purchase, clean_rating))
        #click.echo(r.status_code)
        #click.echo("%s (%s): %s" % (r.status_code, r.reason, r.text))

        #return r.status_code

    except Exception as e:
        config.log(str(e), fg="red")
