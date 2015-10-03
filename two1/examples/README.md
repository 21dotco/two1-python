# djangobitcoin

Demonstrates how to implement 402 endpoints that accept payment with Bitcoin using the Django framework.

## Install w/ VirtualEnv

Get a VirtualEnv setup with Python 3.4 using the instructions here: http://hackercodex.com/guide/python-development-environment-on-mac-osx/

Install requirements.

```bash

$ git clone git@github.com:21dotco/djangobitcoin.git
$ pip install -r requirements.txt

```

Start a local server:

```bash

$ python manage.py runserver

Performing system checks...

System check identified no issues (0 silenced).
July 05, 2015 - 06:46:11
Django version 1.8.2, using settings 'server.settings'
Starting development server at http://127.0.0.1:8000/
Quit the server with CONTROL-C.

```


## Install w/ Heroku

The app already includes the required files to configure and run on Heroku:

```bash

$ heroku create

Creating lit-bastion-5032 in organization heroku... done, stack is cedar-14
http://lit-bastion-5032.herokuapp.com/ | https://git.heroku.com/litbastion-503.git
Git remote heroku added

```

```bash

$ git push heroku master

Counting objects: 6, done.
Delta compression using up to 8 threads.
Compressing objects: 100% (6/6), done.
Writing objects: 100% (6/6), 878 bytes | 0 bytes/s, done.
...
...

```


### Curling a 402 endpoint with bitcurl

```bash

$ bitcurl -X POST \
          -d '{"Text":"Translate this into Spanish"}' \
          http://<app-name>..herokuapp.com/translate/

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





