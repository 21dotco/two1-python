import math
import requests
import two1.wallet.baseWallet

DEFAULT_MAX_REQUEST_PRICE=100000 # Satoshi
DEFAULT_MAX_RETRY_DELAY=15000 # ms
DEFAULT_BASE_BACKOFF_DELAY=1000

# This is our map of available methods, we are using re
REQ_MAP = {
	"GET": requests.get,
	"PUT": requests.put,
	"POST": requests.post,
	"OPTIONS": requests.options,
	"HEAD": request.head,
	"DELETE": requests.delete,
}

def _create_request_for(
		url, 
		method='GET', 
		data=None, 
		headers=None, 
		files=None, 
		cookies=None, 
		allow_redirects=False,
		timeout=30
	):
	""" Creates a request object that can be mutated and used to perform a HTTP request.
	Args:
		url (str): A rfc3986 compliant URL string.
		method (str): The HTTP verb as defined in rfc2616(sec9) to be used in the request.
		data (str): The body of the HTTP request.
		headers (dict): A dict of custom headers for the request.
		files (dict): A dict of files to upload.
		cookies (dict): dict of of cookies for the request to use.
		allow_redirects (bool): States if the request should follow redirects.
		timeout (float): The number of seconds it takes for the request to timeout.
	Returns:	
		(dict): The request object.
	"""
	# Validate that the given request method is allowed available in our mapped methods via REQ_MAP
	if not isinstance(method, str) or not method in REQ_MAP.keys():
		raise ValueError('Method must be one of [\'' + '\', \''.join( REQ_MAP.keys() ) + '\']' )

	# Create our request object, TODO: Create class so we can do instance validation.
	return {
		'url': url,
		'method': method,
		'data': data,
		'headers': headers,
		'cookies': cookies,
		'allow_redirects': allow_redirects,
		'timeout': timeout
	}

def _fetch_for(req):
	# Gets the function for the request method using REQ_MAP and calls it with the request object parameters.
	return REQ_MAP[ req['method'] ]( 
		req['url'], 
		data=req['data'], 
		files=req['file'], 
		cookies=req['cookies'], 
		allow_redirects=req['allow_redirects'],
		timeout=req['timeout'], 
		headers=req['headers']
		)

def _handle_402_response(wallet, res, req, max_request_price=DEFAULT_MAX_REQUEST_PRICE, goal_price=0):
	"""  Handles the 402 payment portion of the request.
	Args:
		wallet (baseWallet): The wallet to use for payment.
		res (response): The response object to pay for.
		req (request): The request to mutate with the payment headers.
		goal_price (number): The price you wish to pay for the request.
	Return:
		request (request): The mutated request object which should retrieve the paid asset.
	"""
	# Extract Bitcoin Payment Headers
	amount = _get_price_for_goal(res.headers['Price'], goal_price=goal_price)
	address = str(res.headers['Bitcoin-Address'])

	# Check price is within our bounds
	if amount == 0:
		return req

	# If the 402 requested amount exceeds the set maximum amount then abort.
	if amount > max_request_price:
		e = ValueError( '402 payment amount exceeds max_request_price. (' + str(amount) + ' > ' + str(max_request_price) + ' ).' )
		e.max_amount = max_request_price
		e.requested_amount = amount
		e.requested_address = address
		e.res = res 
		raise e

	# Pay to the requested address
	tx = wallet.make_signed_transaction_for( address, amount )

	# TODO: Use native transaction object to ensure the tx is properly serialized
	txHex = tx['hex']

	# Modify the request headers to respond to the quote
	req['headers']['Bitcoin-Transaction'] = txHex;

	# Optional quote persistance token.
	if 'Price-Token' in res.headers:
		req['headers']['Price-Token'] = res.headers['Price-Token'];

	return req

def _retrieve_paid_asset( req, delay=DEFAULT_BASE_BACKOFF_DELAY, backoff_max_delay=DEFAULT_MAX_RETRY_DELAY ):
	""" Tries to retrieve the paid asset. 
	Args:
		request (request): The request object to get the asset for.
		delay (float): The base delay to use for our exponential back off.
		backoff_max_delay (float): The max back off delay before aborting.
	returns:
		response (response): the response associated with the 2XX status code.
	"""
	# Perform the request
	res = _fetch_for(req)

	# If we got a 2XX status code then return the response and body
	if math.floor(res.status_code / 100) == 2:
		return res

	# We failed to get the asset try again, create delay for exponential back off, validate that 
	newDelay = delay * 2
	if newDelay >=  backoff_max_delay:
		# Provide the request with the payment headers in the error so the caller can manually retry via bitcurl_for()
		e = ValueError('Aborting: The request delay exceeded the max back off delay.')
		e.req = req
		raise e

	# Sleep for back off
	time.sleep(newDelasy)

	# Recursively retry 
	return self._retrive_paid_asset(req, delay=newDelay, backoff_max_delay=backoff_max_delay )

def _get_price_for_goal(price_object, goal_price=0):
	""" Processes the price object and gets the price closest to the goal price.
	Args:	
		price_object (*): The price object to get the price from.
		goal_price (number): The price we will attempt to reach withing the bounds of the price rules.
	Returns:
		amount (number): The amount that 
	"""

	# Check for static price
	if isinstance(price_object, int):
		return price_object

	# Validate that it is supported quote object.
	if not isinstance(price_object, dict):
		raise ValueError("Unsupported price object type.");

	# Validate that on of the rules exist in the price object.
	if 'min' not in price_object and 'max' not in price_object:
		raise ValueError("A price object must have one or more rules.");

	# Get the current values.
	if 'min' not in price_object:
		return min( goal_price, price_object['max'] );
	if 'max' not in price_object:
		return max( goal_price, price_object['min'] );

	# Both exist
	max_v = price_object['max']
	min_v = price_object['min']
	if min > max:
		raise ValueError('min / max rule conflict.')

	# Get the best fit price for the specified rules.
	# goal_value within min & max not below 0
	return max( min( max( goal_price, min_v ), max_v ), 0 )

# # # # # # Public Interfaces # # # # # # 

def bitcurl(
		url, 
		wallet, 
		method='GET', 
		data=None, 
		headers=None, 
		files=None, 
		cookies=None, 
		allow_redirects=False, 
		timeout=30, 
		max_request_price=DEFAULT_MAX_REQUEST_PRICE,
		backoff_delay=DEFAULT_BASE_BACKOFF_DELAY
		backoff_max_delay=DEFAULT_MAX_RETRY_DELAY,
		goal_price=0
	):
	""" Performs a HTTP request, if the initial request responds with 402 it will pay for the asset using the given wallet.
	Args:
		url (str): A rfc3986 compliant URL string.
		wallet (baseWallet): The wallet to use when paying for the request if the server responds with 402.
		method (str): The HTTP verb as defined in rfc2616-sec9 to be used in the request.
		data (str): The body of the HTTP request.
		headers (dict): A dict of custom headers for the request.
		files (dict): A dict of files to upload.
		cookies (dict): dict of of cookies for the request to use.
		allow_redirects (bool): States if the request should follow redirects.
		timeout (float): The number of seconds it takes for the request to timeout.
		max_request_price (int): The maximum price to allow for the request.
		backoff_delay (float): The base number of seconds the exponential back off delay will start at.
		backoff_max_delay (float): The maximum time the back off delay can be before aborting.
	Returns:
		res (response): The final response for the request.
	"""
	req = _create_request_for(
			url, 
			method=method, 
			data=data, 
			headers= 
			headers, 
			files=files, 
			cookies=cookies, 
			allow_redirects=allow_redirects, 
			timeout=timeout
		) 
	return bitcurl_for( req, wallet, max_request_price=max_request_price, backoff_delay=backoff_delay,
	 						backoff_max_delay=backoff_max_delay, goal_price=goal_price );

def bitcurl_for( 
		req, 
		wallet, 
		max_request_price=DEFAULT_MAX_REQUEST_PRICE, 
		backoff_delay=DEFAULT_BASE_BACKOFF_DELAY, 
		backoff_max_delay=DEFAULT_MAX_RETRY_DELAY,
		goal_price=0
	):
	""" Performs a HTTP request, if the initial request responds with 402 it will pay for the asset using the given wallet.
	Args:
		req (dict): The request object to perform the request for.
		wallet (baseWallet): The wallet to use for request payment.
		max_request_price (int): The maximum price to allow for the request.
		backoff_delay (float): The base number of seconds the exponential back off delay will start at.
		backoff_max_delay (float): The maximum time the back off delay can be before aborting.
		goal_price (number): The price you wish to pay for the request.
	Returns:
		res (response): The final response for the request.
	"""
	# Perform Initial Request
	res = _fetchFor(req);

	# If not a 402 request then do not handle request sequence. 
	if res.status_code != 402:
		return res

	# Make payment and update request
	req = _handle_402_response( wallet, res, req , max_request_price=max_request_price, goal_price=goal_price)

	# Get the final response
	finalRes = _retrieve_paid_asset( req, delay=backoff_delay, backoff_max_delay=backoff_max_delay )

	# Give the caller access to the initial response headers.
	for header in res.headers.keys():
		finalRes.headers['X-Initial-' + header] = res.headers[header];

	# Return the asset
	return finalRes
