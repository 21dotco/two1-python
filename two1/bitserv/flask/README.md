# Flask Bitserv Payment Decorator

This flask module exposes a `402: Payment Required` api route decorator for use with the two1 wallet.


### Usage

`weather.py`

``` python
from flask import Flask, request
from two1.wallet import Wallet
from two1.bitserv.flask import Payment

app = Flask(__name__)
wallet = Wallet()
payment = Payment(app, wallet)

@app.route('/current-temperature')
@payment.required(50)
def current_temperature(request):
    return 'Probably about 65 degrees Fahrenheit.'

if __name__ == '__main__':
    app.debug = True
    app.run(host='0.0.0.0')
```
