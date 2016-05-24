# What is 21?

`21` allows you to earn bitcoin on every HTTP request. Start by installing 21
(Beta) on an internet-connected device to get some bitcoin. Then use 21 to
build, buy, and sell machine-payable services with developers all around the
world.  Learn more at [https://21.co](https://21.co).

# Supported tags

## `base`

This is a base [Alpine Linux](http://www.alpinelinux.org/) image with the
`21` python3 libraries installed via pip.

## `router`

This is an Alpine Linux image with `nginx` added and used for routing to
the individual microservices and payments server.

## `payments`

This is the payments server that manages the
[payment channels](https://21.co/learn/intro-to-micropayment-channels) for all
microservices in a `21 sell` deployment.

## `services-*`

All machine-payable microservices available for you to start selling are prefixed
with the string `service-`.  For example, the `ping` microservice image tag
`service-ping`.

# How to use this image

The images provided in this repository are designed to work with the `21 sell`
service manager that is included with your installation of `21`.
[Sign up](https://21.co) to install `21` and learn more about the `21 sell` tool
[here](https://21.co/learn/21-sell).

# Terms of Use

Please see our Terms of Use [here](https://21.co/terms-of-use).

# Supported Docker versions

These images are supported on Docker version 1.11.0 and up.

# Issues

If you have any problems with or questions about this image, please contact
[support@21.co](mailto: support@21.co).
