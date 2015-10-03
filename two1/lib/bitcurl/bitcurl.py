import math
import json
import requests

DEFAULT_MAX_REQUEST_PRICE = 100000  # Satoshi
DEFAULT_MAX_RETRY_DELAY = 15000  # ms
DEFAULT_BASE_BACKOFF_DELAY = 1000


def _conditional_log(message, logger=None):
    if logger:
        logger(message)


def _handle_402_response(wallet, res, req, max_request_price=DEFAULT_MAX_REQUEST_PRICE, goal_price=0, logger=None):
    """  Handles the 402 payment portion of the request.
    Args:
            wallet (BaseWallet): The wallet to use for payment.
            res (response): The response object to pay for.
            req (request): The request to mutate with the payment headers.
            goal_price (number): The price you wish to pay for the request.
    Return:
            request (request, paid_amount): The mutated request object which should retrieve the paid asset.
    """
    # Extract Bitcoin Payment Headers
    amount = _get_price_for_goal(
        res.headers['Price'], goal_price=goal_price, logger=logger)
    address = str(res.headers['Bitcoin-Address'])
    _conditional_log("402: Server requested " +
                     str(amount) + " satoshi be paid to " + address, logger)

    # Check price is within our bounds
    if amount == 0:
        _conditional_log("402: Requested amount was 0, will return initial response", logger)
        return (req, amount)

    # If the 402 requested amount exceeds the set maximum amount then abort.
    if amount > max_request_price:
        e = ValueError("402 Abort: Payment amount of " + str(amount) + " satoshi exceeds max price of " + str(max_request_price) + " satoshi " )
        e.max_amount = max_request_price
        e.requested_amount = amount
        e.requested_address = address
        e.res = res
        raise e

    # Pay to the requested address
    _conditional_log( "402: Creating transaction", logger)
    txHex = wallet.make_signed_transaction_for(address, amount)
    _conditional_log( "402: Will pay with '" + txHex + "'", logger)

    # Modify the request headers to respond to the quote
    req['headers']['Bitcoin-Transaction'] = txHex

    # Optional quote persistance token.
    if 'Price-Token' in res.headers:
        req['headers']['Price-Token'] = res.headers['Price-Token']
        _conditional_log(
            "402: Persisted price token '" + req['headers']['Price-Token'] + "'", logger)

    return (req, amount)


def _retrieve_paid_asset(req, delay=DEFAULT_BASE_BACKOFF_DELAY, backoff_max_delay=DEFAULT_MAX_RETRY_DELAY, logger=None):
    """ Tries to retrieve the paid asset. 
    Args:
            request (request): The request object to get the asset for.
            delay (float): The base delay to use for our exponential back off.
            backoff_max_delay (float): The max back off delay before aborting.
    returns:
            response (response): the response associated with the 2XX status code.
    """
    # Perform the request
    _conditional_log("Attempting to fetch paid item...", logger)
    res = requests.request(req['method'], req['url'],
                           **{your_key: req[your_key] for your_key in req.keys() if your_key not in ['url', 'method']})

    # If we got a 2XX status code then return the response and body
    _conditional_log("Fetch got: " + str(res.status_code), logger)
    if math.floor(res.status_code / 100) == 2:
        return res

    # We failed to get the asset try again, create delay for exponential back
    # off, validate that
    newDelay = delay * 2
    if newDelay >= backoff_max_delay:
        # Provide the request with the payment headers in the error so the
        # caller can manually retry via bitcurl_for()
        e = ValueError(
            'Aborting: The request delay exceeded the max back off delay.')
        e.req = req
        raise e

    # Sleep for back off
    _conditional_log("Will retry in " + str(newDelay) + "ms", logger)
    time.sleep(newDelasy)

    # Recursively retry
    return _retrieve_paid_asset(req, delay=newDelay, backoff_max_delay=backoff_max_delay)


def _get_price_for_goal(price_object, goal_price=0, logger=None):
    """ Processes the price object and gets the price closest to the goal price.
    Args:   
            price_object (*): The price object to get the price from.
            goal_price (number): The price we will attempt to reach withing the bounds of the price rules.
    Returns:
            amount (number): The amount that 
    """
    price_object = json.loads(price_object)

    # Check for static price
    if isinstance(price_object, int):
        _conditional_log(
            "402: Has fixed price of " + str(price_object) + " satoshi", logger)
        return price_object

    # Validate that it is supported quote object.
    if not isinstance(price_object, dict):
        raise ValueError("Aborting: Price object is unsupported, got '" +
                         str(price_object) + "' expected 'dict' or 'int'")

    # Validate that on of the rules exist in the price object.
    if 'min' not in price_object and 'max' not in price_object:
        raise ValueError("A price object must have one or more rules.")

    # Get the current values.
    if 'min' not in price_object:
        _conditional_log("402: Price object defined max payment amount to " +
                         str(price_object['max']) + " satoshi", logger)
        return min(goal_price, price_object['max'])
    if 'max' not in price_object:
        _conditional_log("402: Price object defined min payment amount to " +
                         str(price_object['min']) + " satoshi", logger)
        return max(goal_price, price_object['min'])

    # Both exist
    max_v = price_object['max']
    min_v = price_object['min']
    _conditional_log("402: Price object defined payment range of ( min: " +
                     str(min_v) + ", max: " + str(max_v) + " )", logger)
    if min > max:
        raise ValueError("Aborting: Price object rule conflict.")

    # Get the best fit price for the specified rules.
    # goal_value within min & max not below 0
    return max(min(max(goal_price, min_v), max_v), 0)

# # # # # # Public Interfaces # # # # # #


def bitcurl(
    url,
    wallet,
    **kwargs
):
    """ Performs a HTTP request, if the initial request responds with 402 it will pay for the asset using the given wallet.
    Args:
            req (dict): The request object to perform the request for.
            wallet (BaseWallet): The wallet to use for request payment.
            max_request_price (int): The maximum price to allow for the request.
            backoff_delay (float): The base number of seconds the exponential back off delay will start at.
            backoff_max_delay (float): The maximum time the back off delay can be before aborting.
            goal_price (number): The price you wish to pay for the request.
    Returns:
            res (response): The final response for the request.
    """
    # Set Defaults
    kwargs.setdefault('method', 'GET')
    kwargs.setdefault('params', None)
    kwargs.setdefault('data', None)
    kwargs.setdefault('headers', {})
    kwargs.setdefault('cookies', None)
    kwargs.setdefault('files', None)
    kwargs.setdefault('auth', None)
    kwargs.setdefault('timeout', None)
    kwargs.setdefault('allow_redirects', True)
    kwargs.setdefault('proxies', None)
    kwargs.setdefault('stream', None)
    kwargs.setdefault('verify', None)
    kwargs.setdefault('cert', None)
    kwargs.setdefault('json', None)

    kwargs.setdefault('backoff_max_delay', DEFAULT_MAX_RETRY_DELAY)
    kwargs.setdefault('backoff_delay', DEFAULT_BASE_BACKOFF_DELAY)
    kwargs.setdefault('max_request_price', DEFAULT_MAX_REQUEST_PRICE)
    kwargs.setdefault('goal_price', 0)
    kwargs.setdefault('logger', None)

    backoff_delay = kwargs['backoff_delay']
    backoff_max_delay = kwargs['backoff_max_delay']

    max_request_price = kwargs['max_request_price']
    goal_price = kwargs['goal_price']

    logger = kwargs['logger']

    # Build Req object, filter out non request arguments
    req = {your_key: kwargs[your_key] for your_key in kwargs.keys()
           if your_key not in ['max_request_price', 'backoff_delay', 'backoff_max_delay', 'backoff_max_delay', 'goal_price', 'logger']}
    req['url'] = url

    # Perform Initial Request
    _conditional_log('{} {}'.format(req['method'], req['url']), logger)
    res = requests.request(req['method'], req['url'],
                           **{your_key: req[your_key] for your_key in req.keys() if your_key not in ['url', 'method']})

    # If not a 402 request then do not handle request sequence.
    if res.status_code != 402:
        _conditional_log(
            "Aborting payment: Server responded with " + str(res.status_code), logger)
        res.paid_amount = 0
        return res

    # Make payment and update request
    _conditional_log("402: Was received, will attempt to pay", logger)
    mod_req = _handle_402_response(
        wallet, res, req, max_request_price=max_request_price, goal_price=goal_price, logger=logger)
    req = mod_req[0]

    # Get the final response
    finalRes = _retrieve_paid_asset(
        req, delay=backoff_delay, backoff_max_delay=backoff_max_delay, logger=logger)
    finalRes.paid_amount = finalRes[1]

    # Give the caller access to the initial response headers.
    for header in res.headers.keys():
        finalRes.headers['X-Initial-' + header] = res.headers[header]

    # Return the asset
    return finalRes
