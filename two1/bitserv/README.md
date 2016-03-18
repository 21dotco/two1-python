# The 21 BitServ Library

## Overview

The BitServ library adds a simple API for servers to create payable resources in both Flask and Django frameworks. It enables a server (also referred to as a merchant) to receive payment from a client (also referred to as a customer) for a resource. See the [bitrequests readme](https://github.com/21dotco/two1/blob/devel/two1/bitrequests/docs/README.md) for more information on the `402 payment-resource exchange`.


## Payment Methods

The bitserv library provides a base set of [payment_methods](https://github.com/21dotco/two1/blob/devel/two1/bitserv/payment_methods.py) that framework-specific decorators can use to accept different payment types (e.g. `OnChain`, `Payment Channel` and `BitTransfer` types). Payment methods should implement the following methods:

  * **get_402_headers()** provides a list of headers that the *server* returns to the client in the initial `402 PAYMENT REQUIRED` response.

  * **payment_headers()** provides a list of headers that the *client* sends to the server to inform how payment is being made.

  * **redeem_payment()** runs payment validation and any steps necessary to complete payment processing from the client to the server.


## Payment Decorators

Decorators for a framework should ideally expose a similar public interface for wrapping routes and gating resource access contingent on payment. If possible with respect to any framework's design methodology, any bitserv library should expose a `payment` object with a `required` method that defines the acceptable `price`. The `payment.required()` method should be a function wrapper that can decorate a python function. The argument `price` should be flexible and accept both a static `int` type and `function` type (or any `callable` type for that matter).

Example API Usage:

``` python
# Static Price
@payment.required(100)
def current_temperature():
    return 65

# Dynamic price
@payment.required(lambda req: req.args.get('important_var') * 100)
def current_temperature():
    return 65
```


### Flask

The decorator for the [Flask](http://flask.pocoo.org/) framework acts by attaching itself to an instance of a flask app and then further injecting wallet functionality with a `two1.wallet.Wallet` object.

``` python
from flask import Flask
from two1.wallet import Wallet
from two1.bitserv.flask import Payment

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet)

```

For payment channel negotiation, the decorator also adds an REST API `/payment` route. This namespace can be configured by changing the `endpoint` keyword argument during instantiation of the `Payment` object (e.g. `payment = Payment(app, wallet, endpoint='/pay-up')`)


### Django

The decorator for the [Django](https://www.djangoproject.com/) framework is an installable django app package. It automagically will search your `settings.py` file for a `WALLET` variable and instantiate a new `Payment` object. This makes usage in any particular module a little simpler, but adds a few extra configuration steps.

`setup.py`

``` python
packages=[
      . . .
    'two1.bitserv.django'
]
```

`settings.py`

``` python
from two1.wallet import Wallet

INSTALLED_APPS = (
      . . .  
   'two1.bitserv.django'
)

WALLET = Wallet()

APPEND_SLASH = False
```

`urls.py`

``` python
url(r'^payments/', include('two1.bitserv.django.urls'))
```

`views.py`
``` python
from two1.bitserv.django import payment
```

To finalize Django setup, be sure to run the following command (or equivalent) to make sure that the database models are properly added to your project.

```
python manage.py migrate
```

## Payment Server

[payment_server.py](https://github.com/21dotco/two1/blob/devel/two1/bitserv/payment_server.py) is concerned with managing the server side of payment channels. The `PaymentServer` object is generic enough to be used by various communication protocols, though it is presently only implemented over HTTP REST as a core part of the `bitserv` library.

The `PaymentServer` - and to some extent, each `PaymentBase` method - relies on state being maintained by the application. It consumes the [models.py](https://github.com/21dotco/two1/blob/devel/two1/bitserv/models.py) API in order to store and retrieve channel state. The default database implementation uses the `sqlite3` standard library to communicate with an SQLite database. The django-specific database implementation provides an adapter that hooks into the django ORM to allow payment methods to keep their data with the rest of the django application.

The `PaymentServer` also uses a custom `wallet.py` wrapper to provide added transaction-building functionality. You can set up a barebones payment server by passing it a two1 wallet instance

``` python
from two1.wallet import Wallet
from two1.bitserv import PaymentServer

wallet = Wallet()
payment_server = PaymentServer(wallet)
```
