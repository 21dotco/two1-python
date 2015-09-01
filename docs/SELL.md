# two1 sell

The **two1 sell** command configures local web server to sell API calls or static content. Two1 software comes with sample built-in API's that can be configured for sale right away, or you can create ones your own. One of the built-in API's is a "static server", that allows you to put any file or folder to be sold with bitcoin. 

To start, explore built-in API's with --builtin option: 

```bash

$ two1 sell --builtin

BUILTINS

barcode/generate-qr
...
serve/*

```

To publish one of the built-in endpoints, specify its url path and a package name:

```bash

$ two1 sell barcode/generate-qr two1.djangobitcoin.misc
Selling language/translate on http://127.0.0.1:8000/
Configuring language/translate with {}
Endpoints configuration updated.

```

If you want to start selling a folder, call **two1 sell** specifying **serve** endpoint and static_serve built-in package:

```bash

$ two1 sell serve/kittens two1.djangobitcoin.static_serve --path ~/Documents/Kittens --price 10000
Selling serve/kittens on http://127.0.0.1:8000/
Configuring serve/kittens with {'price': '10000', 'path': '~/Documents/Kittens'}
Endpoints configuration updated.

```
It is possible to sell a single file, too:
```bash

$ two1 sell serve/kittens/kitty.jpg two1.djangobitcoin.static_serve --path ~/Documents/Kittens/red.jpeg --price 10000
Selling serve/kittens/kitty.jpg on http://127.0.0.1:8000/
Configuring serve/kittens/kitty.jpg with {'path': '~/Documents/Kittens/red.jpeg', 'price': '10000'}
Endpoint ^serve/* is already selling
```
Note: if you're selling a folder, endpoint must not have an extension, and if you sell a single file, the endpoint must have an extension.

![](https://github.com/21dotco/two1/blob/sergey-sell-static/docs/two1_sell.gif)
 
