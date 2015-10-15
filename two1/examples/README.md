# bitcoin_auth

Demonstrates how to implement 402 [Payment Required](https://en.wikipedia.org/wiki/List_of_HTTP_status_codes#4xx_Client_Error) endpoints that accept payment with Bitcoin using Django & Django REST Framework.

## Install two1 dependencies.

Read about performing this step [here](https://github.com/21dotco/two1#developer-installation)

## Running locally

Given that you have already set up a two1 wallet & account perform the following steps:

```bash

$ python two1/examples/manage.py migrate
$ heroku local

```


## Install w/ Heroku

The app already includes the required files to configure and run on Heroku:

```bash

$ heroku create
$ git push heroku devel:master
$ heroku config:set TWO1_USERNAME="yourusername" # Your TWO1 Username as seen in `$21 status`
$ heroku config:set BITSERV_DEFAULT_PAYMENT_ADDRESS="1yourbitcoinaddress" # The address you want to collect payment to 
$ heroku run python two1/examples/manage.py migrate
$ heroku config:set BITCHEQUE_VERIFICIATION_URL=$DOTCO_BITCHEQUE_API_ENDPOINT # obtain this via your dotco deployment.

```


### Purchasing a 402 endpoint via 21 buy 

```bash

# Purchase using earnings
$ 21 buy http://rocky-peak-2931.herokuapp.com/weather/current-temperature?place=94103
# Purchase using onchain bitcoin
$ 21 buy http://rocky-peak-2931.herokuapp.com/weather/current-temperature?place=94103 --onchain
<Response [402]> {"status_code":402,"detail":"Payment Required"}

```

### Curling a 402 endpoint with manual payment 

Obtain the Bitcoin address & payment amount in Satoshi:

```bash

$ curl -i -H "Content-Type: application/json" \
     -X POST -d '{"Text":"Translate this into Spanish"}' \
     http://<app-name>.herokuapp.com/translate/

HTTP/1.0 402 PAYMENT REQUIRED
Date: Sun, 05 Jul 2015 07:01:27 GMT
Server: WSGIServer/0.2 CPython/3.4.2
Content-Type: text/html; charset=utf-8
X-Frame-Options: SAMEORIGIN
price: 0.0005
bitcoin-address: 1BHZExCqojqzmFnyyPEcUMWLiWALJ32Zp5

```

Make a payment and use the Transaction hash: 

```bash

$ curl -i -H "Content-Type: application/json" \
       -X POST -d '{"Text":"Translate this into Spanish"}' \
       http://<app-name>..herokuapp.com/translate/?tx=b5828f9c10bdfcd03bd4650d98fbed09d2f4a8f13554c92f2f7c6142064e314e

HTTP/1.0 200 OK
Date: Sun, 05 Jul 2015 07:04:34 GMT
Server: WSGIServer/0.2 CPython/3.4.2
Content-Type: application/json
X-Frame-Options: SAMEORIGIN

{"translated": "Traducir esto en espa\u00f1ol"}

```

### Browse/Use API's using the frontend

All the endpoints are automatically added to the fontend available at:

```

https://<app-name>..herokuapp.com/docs/

```

![API Endpoints](/docs/api_docs_page.png)





