import json
import signal
from subprocess import Popen, PIPE

from re import split
import click
from click import ClickException
import os
from two1.config import pass_config
from two1.djangobitcoin.djangobitcoin.settings import ENDPOINTS_FILE
import two1.djangobitcoin.djangobitcoin as dj_bt


@click.command(context_settings=dict(
    ignore_unknown_options=True,
))
@click.option('--builtin', is_flag=True, help='Show built-in endpoints.')
@click.argument('args', nargs=-1)
@pass_config
def sell(config, args, port=8000, builtin=False):
    try:
        if builtin:
            show_builtins()
            return
        items, params = process_parameters(args)
        sell_items(items, params, port)
    except Exception as e:
        raise ClickException(e)


def process_parameters(args):
    items = []
    params = {}
    last_arg = None
    for arg in args:
        if arg.startswith('--'):
            last_arg = arg[2:]
            params[last_arg] = None
        else:
            if last_arg:
                params[last_arg] = arg
                last_arg = None
            else:
                items.append(arg)
    return items, params


def try_config_django():
    from django.conf import settings as django_settings
    if not django_settings.configured:
        django_settings.configure()
    return True


def find_process_by_attribute(attribute):
    process_list = []
    sub_proc_ps = Popen(['ps', 'auxw', ], stdout=PIPE)
    sub_proc = Popen(['grep', attribute, ], stdin=sub_proc_ps.stdout, stdout=PIPE)
    sub_proc_ps.stdout.close()
    # Discard the first line (ps aux header)
    sub_proc.stdout.readline()
    for line in sub_proc.stdout:
        # The separator for splitting is 'variable number of spaces'
        proc_info = split(" *", line.decode('utf-8').strip())
        process_list.append(proc_info[1])  # pid
    if process_list:
        return min(process_list)


def find_process():
    # gunicorn process is started gunicorn --pythonpath two1/djangobitcoin djangobitcoin.wsgi --bind 127.0.0.1:8000
    # built-in django server is started python manage.py runserver 127.0.0.1:8000
    gunicorn_pid = find_process_by_attribute('djangobitcoin.wsgi')
    if gunicorn_pid:
        return gunicorn_pid, True
    django_svr_pid = find_process_by_attribute('runserver')
    if django_svr_pid:
        return django_svr_pid, False
    return None, None


def match_endpoint(endpoint, regex):
    return regex.match(endpoint)


def find_endpoint(endpoint, package_name):
    try:
        package = __import__(package_name, fromlist=['urls'])
        urls = getattr(package, 'urls')
        match = next((x.regex.pattern for x in urls.urlpatterns if match_endpoint(endpoint, x.regex)), None)
        if match:
            return package_name, match, urls.configurator
        else:
            return None
    except Exception as e:
        click.echo('Error importing {0}: {1}'.format(package_name, e))
        return None


def update_config(ep_json, package_name, pattern):
    package_element = next((x for x in ep_json if x['package'] == package_name), None)
    if not package_element:
        package_element = {'package': package_name, 'urls': []}
        ep_json.append(package_element)
    else:
        urls = package_element.get('urls', None)
        if urls:
            if pattern in urls:
                click.echo('Endpoint {0} is already selling'.format(pattern))
                return False
        else:
            package_element['urls'] = []
    package_element['urls'].append(pattern)
    return True


def save_config(endpoints_path, ep_json):
    # Save the file
    with open(endpoints_path, 'w') as outfile:
        json.dump(ep_json, outfile, indent=2)
    click.echo('Endpoints configuration updated.')
    # Check if we can restart the server
    pid, is_gunicorn = find_process()
    if is_gunicorn:
        os.kill(int(pid), signal.SIGHUP)
        click.echo('Server restarted')
    elif pid:
        click.echo('Restart the server')


def sell_item(item, params, port):
    '''
    :param item: a string indicating which endpint to sell (f.e. 'language/translate' or 'serve/kittens')
    :param params: extra parameters from the 'sell' command to be passed to the endpoint's configurator
                   they are endpoint-specific, f.e for 'serve' it can be --path ~/foo.txt
    '''
    endpoints_path = os.path.join(dj_bt.__path__[0], ENDPOINTS_FILE)
    ep_json = json.load(open(endpoints_path))
    # try to find our endpoint within builtins
    ep_found = find_endpoint(item, 'two1.djangobitcoin.static_serve') or \
               find_endpoint(item, 'two1.djangobitcoin.misc') or \
               find_endpoint(item, 'two1.djangobitcoin.scipy_aas')
    if not ep_found:
        click.echo('Endpoint {0} not found'.format(item))
        return
    package_name, pattern, configurator = ep_found
    click.echo('Selling %s on http://127.0.0.1:%d/' % (item, port))
    # Configure endpoint passing passthrough parameters to configurator
    click.echo('Configuring {0} with {1}'.format(item, params))
    configurator(item, params)
    # If the endpoint is not up yet, make it so
    if update_config(ep_json, package_name, pattern):
        save_config(endpoints_path, ep_json)


def sell_items(items, params, port):
    if not try_config_django():
        return
    for item in items:
        sell_item(item, params, port)


def try_url_imports(package_name):
    try:
        package = __import__(package_name, fromlist=['urls'])
        return package.urls.urlpatterns
    except Exception as e:
        click.echo('Error importing {0}: {1}'.format(package_name, e))
        return []


def show_builtins():
    click.echo("\nBUILTINS\n")
    if not try_config_django():
        return
    misc_urls = try_url_imports('two1.djangobitcoin.misc')
    scipy_urls = try_url_imports('two1.djangobitcoin.scipy_aas')
    static_urls = try_url_imports('two1.djangobitcoin.static_serve')
    urls = misc_urls + scipy_urls + static_urls
    for u in urls:
        click.echo(u.regex.pattern)
