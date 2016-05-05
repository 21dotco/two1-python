# Testing two1 and dotco with Docker

## Single two1 instance

Here is how you test two1 and dotco locally on your machine.

### Dotco setup 

Set the environment variables

```
DATABASE_URL=postgres://dotcouser:dotcopass@localhost/dotcodb
DOTCO_API_URL=http://localhost:8000
``` 

This is needed because the website and API are considered separate entities,
and you have to tell the website to talk to the API and vice versa. Otherwise,
e.g., email activation on your local instance will try to send you to the
staging API. Moreover, it will use the staging API to even check if your
submitted username is taken, instead of the local database.

Note, do not run `setup/setup.sh` after the first time you set up the
repository, or else it will delete your `.env` file! You should keep a separate
`.env-local` file for your local environment variables, and a `.env-staging`
for staging, etc.

Now run

```
$ python3 manage.py makemigrations
$ python3 manage.py migrate
$ python3 manage.py loaddata dotco/store/fixtures/test.json
$ python3 manage.py runserver
```

If you're not making changes to the database models, you only need to run the
last line.

Now you can open a browser to http://127.0.0.1:8000, create a new user with any
email (since you have an empty database) and activate it. 

To check out the live dotco database from a python repl (and do things like
edit rows, delete users, etc), run

```
python manage.py shell_plus
```

### Two1 setup

In a different terminal window (since runserver took over the dotco window), go
to your local `two1` repo and set the environment variables

```
TWO1_HOST="http://127.0.0.1:8000"
TWO1_WWW_HOST="http://127.0.0.1:8000"
TWO1_PROVIDER_HOST="https://blockchain.21.co"
TWO1_LOGGER_SERVER="http://52.21.57.141:8009"
TWO1_POOL_URL="swirl+tcp://grid.21-dev.co:21006"
```

Now run `21 login` with the user/pass you just created and watch it succeed.

## Multiple two1 instances (simluated on different machines)

### CLI args: the quick and dirty way

The fastest way to test multiple two1 instances is to have multiple `two1.json`
files and multiple wallet files, and point the `21` CLI to each one for the
commands you want to run. E.g.

```
$ 21 --config-file ~/.two1/user1.json --config wallet_path ~/.two1/wallet/wallet1.json login
$ 21 --config-file ~/.two1/user1.json --config wallet_path ~/.two1/wallet/wallet1.json status
$ 21 --config-file ~/.two1/user2.json --config wallet_path ~/.two1/wallet/wallet2.json login
$ 21 --config-file ~/.two1/user2.json --config wallet_path ~/.two1/wallet/wallet2.json status
```

This works just fine, but is very annoying to work with. A cleaner solution is
to use docker.

### Docker: the clean and scalable way

First, install the docker toolbox and learn a little bit about docker. One
minor thing about docker is that it can't access localhost from inside a
container. So the first step is to grab your ip address on the local subnet

```
$ ifconfig
...
en0: flags=8863<UP,BROADCAST,SMART,RUNNING,SIMPLEX,MULTICAST> mtu 1500
    ether f4:5c:89:a6:f3:a5 
    inet6 fe80::f65c:89ff:fea6:f3a5%en0 prefixlen 64 scopeid 0x4 
    inet 192.168.128.207 netmask 0xffffff00 broadcast 192.168.128.255
    nd6 options=1<PERFORMNUD>
    media: autoselect
    status: active
...
``` 

The number I'm looking for is 192.168.128.207. Save this number for the rest of the readme.

Now when you spin up dotco, you have to use the following command

```
$ python3 manage.py runserver 0.0.0.0:8000
```

This will launch your local web server so it's listening at your local subbnet ip. In my case
navigating to http://192.168.128 would hit the website.

Not create an environment file, which I'll call `.env-local`. This will be the
environment file we provide to our docker containers.

```
LC_ALL=C.UTF-8
LANG=C.UTF-8
TWO1_HOST=http://192.168.128.207:8000
```

The `TWO1_HOST` should be your subnet ip. Next create the following `docker-compose.yml` compose file

```
version: "2"
services:
  cli:
    image: python:3-onbuild 
    env_file: .env-local
    volumes:
      - .:/two1
    command: bash -c "pip install --editable /two1 && sleep infinity"
```

What this does is define a docker image which has python3 pre-installed on it,
and then it mounts the current directory as a docker volume. A docker volume is
a logical directory in a container that allows every container running the
`cli` image to have a shared (and updated!) copy of the corresponding directory
on your filesystem. So in this case we take the current directory, containing
our local copy of two1, and mount it at `/two1` for every container. The
`command:` directive further installs from that repository so that when you
make changes to `two1` on your local filesystem, they're immediately reflected
in every container.

Now spin up the conatiners

```
docker-machine start 21
eval $(docker-machine env 21)
docker-compose up &
```

Note that currently this command only spins up one container for the `cli`
image (as `two1_cli_1`). 

To bring it down (which erases all local state, like user logins and wallets)

```
docker-compose down
```

To jump into a shell in a live container

```
docker exec -it two1_cli_1 bash
```

And now, for the clincher, to scale up to any number of independent containers,
run 

```
docker-compose scale cli=3
```

To list the containers that are running, run

```
docker ps
```

And you can jump into each one with `docker exec -it two1_cli_# bash`.
