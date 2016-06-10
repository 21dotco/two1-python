# 21: Build the Machine-payable Web [![Build Status](https://travis-ci.com/21dotco/two1-python.svg?branch=master)](https://travis-ci.com/21dotco/two1-python)

![21 logo](docs/img/21_banner.png "21")

`two1` is an open source project containing a command line tool and python library that enable you to build the [machine-payable web](https://21.co).

You can buy bitcoin at the command line or earn it by selling machine-payable APIs that you've published to the [21 Marketplace](https://21.co/mkt). Use this bitcoin to purchase other API calls or send it to another address you control. The package includes:

- an HD wallet to securely manage your bitcoin
- crypto and bitcoin libraries to build bitcoin/blockchain applications
- a [micropayment-channels](https://21.co/learn/intro-to-micropayment-channels/) client and server
- containerized microservices you can sell to earn bitcoin

and much more.

## Security

Please note that the 21 software is in beta. To protect the security of your systems while using 21, we highly recommend you install the software on a device other than your main laptop (e.g. 21 Bitcoin Computer, an old laptop, or an Amazon Virtual Machine) while the product is still in beta. You can read more security-related information [here](https://21.co/learn/security/). Please send an email to [security@21.co](mailto://support@21.co) regarding any issue concerning security.

## Getting Started

[Create an account](https://21.co) or install the library and CLI (python3.4+ is required):

``` bash
$ curl https://21.co | sh
```

`two1` can also be installed via pip:

``` bash
$ sudo pip3 install two1
```

Start with the command line tool:

``` bash
$ 21 help
```

Read the [Introduction to 21](https://21.co/learn/intro-to-21/) guide and the `two1` [documentation](https://21.co/learn/#reference-21-library).

## Developers

If you'd like to contribute to `two1`, please use the following steps to clone the repository and get it set up on your system.

Clone this repository:

``` bash
$ git clone https://github.com/21dotco/two1-python.git
$ cd two1-python/
```

Install the requirements:

``` bash
$ pip3 install -r requirements.txt
```

Install 21 as an editable python library:

``` bash
$ pip3 install -e .
```

Your changes to the source will now be reflected in your system installation in real-time. When you open a PR against this repository, your code will automatically be built and tested.

Run the tests:

``` bash
$ python3 -m pytest
```

## Docker

You can pull pre-built [Docker](https://www.docker.com/) images with `two1` installed from the [21 Docker Hub repository](https://hub.docker.com/r/21dotco/two1).

``` bash
$ docker pull 21dotco/two1
```

Run the latest base image:

``` bash
$ docker run -it 21dotco/two1 sh
```

## Community

Join our [global development community](https://slack.21.co) to chat with other users or to get in touch with support.

## Licensing

`two1` is licensed under the FreeBSD License. See [LICENSE](https://github.com/21dotco/two1-python/blob/master/LICENSE) for the full license text.
