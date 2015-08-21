import click
from two1.config import pass_config
from two1.debug import dlog
import time
import datetime

@click.command()
@click.argument('resource',nargs=1)
@click.option('--data', default="{}", help="The data/body to send to the seller")
@click.option('--max_price',  default=5000, help="The max amount to pay for the resource")
@pass_config
def buy(config,resource,data,max_price):
    """Buy internet services with Bitcoin
    	resource - The digital resource to buy from.

    	example: two1 buy en2cn --data {'text':'This is SPARTA'}
    """
    #dlog("two1.buy" + str(type(resource)) + str(resource))
    config.log("Looking for best price for {}...".format(resource))
    time.sleep(1.0)
    seller = "peaceful_beast"
    price = 4000
    config.log("Best price from seller: {} price: {}".format(seller,price))
    if price > max_price:
    	config.log("Best price:{} exceeds maximum price: {}".format(price,max_price))
    else:
    	config.log("Fetching resource {}/{}...".format(seller,resource))
    	time.sleep(1.0)
    	config.log("Success.")
    	config.log_purchase(s=seller,r=resource,p=price,d=str(datetime.datetime.today()))


    

