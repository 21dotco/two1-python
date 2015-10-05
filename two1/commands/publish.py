import click

from click import ClickException

from two1.lib.rest_client import TwentyOneRestClient
from two1.lib.machine_auth import MachineAuth
from two1.config import pass_config
from two1.config import TWO1_HOST, TWO1_DEV_HOST


@click.command()
@pass_config
@click.argument('args', nargs=-1)
def publish(config, args):
    """Publishes an endpoint to the 21 market

    \b
    Args:
        path (str): the url path to the endpoint
        name (str): short name for the endpoint
        description (str): what the endpoint does
        price (int): price of endpoint in Satoshis
        device_id (uuid): uuid of device serving the endpoint

    \b
    Examples:
        two1 publish package_name 'name' 'long description' 1000 1
            - publish or update single endpoint on 21 market

        not yet implemented:
            two1 publish all
                - publish all unlisted enpoints on this device
            two publish --ednpoints
                - show list of all endpoints on this device
            two publish --unlist 127.0.0.1:8000/en2cn_v2
                - unlist single endpoint from 21 market

    """

    try:
        try:
            (path, name, description, price, device_id,
                opt_dict, errs) = validate(args)
        except Exception:
            click.echo(
                "Usage: two1 publish [OPTIONS] PATH 'NAME' " +
                "'DESCRIPTION' PRICE DEVICE_UUID"
            )
            return
    except Exception as e:
        raise ClickException(e)

    if len(errs) > 0:
        click.echo(
            "Usage: two1 publish [OPTIONS] PATH 'NAME' " +
            "'DESCRIPTION' PRICE DEVICE_UUID"
        )
        for err in errs:
            click.echo(err)
        raise ClickException('Publishing Failed')

    # todo use TwentyOneRestClient and MachineAuth instead of requests
    # machine_auth = MachineAuth.from_keyring()
    # rest_client = TwentyOneRestClient(TWO1_DEV_HOST, machine_auth)
    # response = rest_client.mmm_create_listing(
    #     path, name, description, price, device_id
    # )
    import json
    import requests
    headers = {}
    headers["Content-Type"] = "application/json"

    method = 'POST'
    url = '{}/mmm/v1/listings/'.format(TWO1_DEV_HOST)
    body = {
        "name": name,
        "description": description,
        "price": price,
        "path": path,
        "server": device_id
    }
    data = json.dumps(body)
    try:
        response = requests.request(method, url, headers=headers, data=data)
    except Exception as e:
        raise ClickException(e)

    if response is not None and response.status_code == 201:
        created_dict = response.json()
        price = created_dict.get('price')
        name = created_dict.get('name')
        uuid = created_dict.get('uuid')
        config.log("Published '{}' endpoint. Price: {}. UUID: {}".format(name, price, uuid))
    else:
        response_data = response.json()
        if 'non_field_errors' in response_data and 'The fields server, path must make a unique set.' in response_data.get('non_field_errors'):
            click.echo('Endpoint with this server and path already exists')
            raise ClickException('Publishing Failed')


def pop_option(args):
    """Return option name and value and remove from args list

    If option name is 'endpoints', option value is True

    If option name is 'unlist', option value is next arg as we allow:
    '--unlist path'
    """
    i_opt = next(((i, x) for i, x in enumerate(args) if x.startswith('--')), None)
    if not i_opt:
        return None
    idx, opt = i_opt
    if opt != 'endpoints':
        val = args[idx + 1]
        del args[idx:idx + 2]
    else:
        val = True
        del args[idx]
    return opt[2:], val


def validate(args):
    """Remove options and validate required args present
    """
    args = list(args)
    opt_dict = {}
    errs = []

    while True:
        opt_value = pop_option(args)
        if not opt_value:
            break
        opt_dict[opt_value[0]] = opt_value[1]
    options = [opt[0] for opt in opt_dict]
    if 'endpoints' in options and 'unlist' in options:
        errs.append(
            '--unlist and --endpoints options cannot be' +
            'used at the same time'
        )
    try:
        path = args[0]
    except IndexError:
        path = None
    try:
        name = args[1]
    except IndexError:
        name = None
    try:
        description = args[2]
    except IndexError:
        description = None
    try:
        price = args[3]
    except IndexError:
        price = None
    try:
        device = args[4]
    except IndexError:
        device = None
    if (path is None or name is None or description is None or price is None
            or device is None):
        if path is None:
            if 'unlist' in options and 'endpoints' not in options:
                errs.append('Missing path parameter for use with option --unlist')
            else:
                errs.append('Missing required arg PATH')
        if path != 'all':
            if name is None:
                errs.append('Missing required arg NAME')
            if description is None:
                errs.append('Missing required arg DESCRIPTION')
            if price is None:
                errs.append('Missing required arg PRICE')
            else:
                try:
                    price = int(price)
                except:
                    errs.append('arg PRICE must be a valid integer')
            if device is None:
                errs.append('Missing required arg DEVICE_UUID')
    else:
        try:
            price = int(price)
        except:
            errs.append('arg PRICE must be a valid integer')
    return path, name, description, price, device, opt_dict, errs
