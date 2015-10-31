# Django Bitserv Payment Decorator

This django app exposes a `402: Payment Required` api route decorator for use with the two1 wallet.

### Installation

`setup.py`

``` python
packages=[
      . . .
    'two1.lib.bitserv.django'
]
```

`settings.py`

``` python
from two1.lib.wallet import Wallet

INSTALLED_APPS = (
      . . .  
   'two1.lib.bitserv.django'
)

WALLET = Wallet()

APPEND_SLASH = False
```

urls.py

``` python
url(r'^payments/', include('two1.lib.bitserv.django.urls'))
```


### Usage

`weather.py`

``` python
from rest_framework.decorators import api_view
from two1.lib.bitserv.django import payment


@api_view(['GET'])
@payment.required(50)
def current_temperature(request):
    return 'Probably about 65 degrees Fahrenheit.'

```
