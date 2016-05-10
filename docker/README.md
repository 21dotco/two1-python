21 DockerHub Blueprints
=======================

This directory contains the blueprints for docker images distributed by 21.
These are used extensively for the `21 sell` service manager.

## Components

### Base

This is the base Alpine Linux image with `two1` installed via pip.

### Router

This is the Alpine Linux image with `Nginx` used for routing to the individual
microservices and payments server.

### Payments

This is the payments server that manages the payment channels for all
microservices in a deployment.

### Services

All machine-payable microservices are prefixed with the string `service-`.  For
example, the ping microservice blueprint directory is called `service-ping`.
