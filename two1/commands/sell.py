import json
import signal
import click
from django.conf import settings as django_settings
from two1.djangobitcoin.djangobitcoin.settings import ENDPOINTS_FILE
import os
from two1.config import pass_config
import two1.djangobitcoin.djangobitcoin as dj_bt


@click.command()
@click.option('--builtin', is_flag=True, help='Show built-in endpoints.')
@click.argument('items', nargs=-1)
@pass_config
def sell(config, items, port=8000, builtin=False):
    if builtin:
        show_builtins()
        return
    for item in items:
        sell_item(item, port)
    return


def find_endpoint(endpoint, package_name):
    package = __import__(package_name, fromlist=['urls'])
    urls = getattr(package, 'urls').urlpatterns
    if endpoint in map(lambda u: u.regex.pattern, urls):
        return package_name


def find_process():
    # TODO find process, possibly with psutil
    # gunicorn process is started gunicorn --pythonpath two1/djangobitcoin djangobitcoin.wsgi --bind 127.0.0.1:8000
    # python process is started python manage.py runserver 127.0.0.1:8000
    pass


def sell_item(item, port):
    endpoints_path = os.path.join(dj_bt.__path__[0], ENDPOINTS_FILE)
    ep_json = json.load(open(endpoints_path))
    django_settings.configure()
    package = find_endpoint(item, 'two1.djangobitcoin.misc') \
              or find_endpoint(item, 'two1.djangobitcoin.scipy_aas') \
              or find_endpoint(item, 'two1.djangobitcoin.static_serve')
    if not package:
        click.echo('Endpoint {0} not found'.format(item))
    click.echo('Selling %s on http://127.0.0.1:%d/' % (item, port))
    package_element = next((x for x in ep_json if x['package'] == package), None)
    if not package_element:
        package_element = {'package': package, 'urls': []}
        ep_json += package_element
    else:
        if item in package_element['urls']:
            click.echo('Endpoint {0} is already selling'.format(item))
            return None
    package_element['urls'].append(item)
    with open(endpoints_path, 'w') as outfile:
        json.dump(ep_json, outfile, indent=2)
    pid, is_gunicorn = find_process()
    if is_gunicorn:
        os.kill(pid, signal.SIGHUP)
    elif pid:
        click.echo('Endpoints configuration updated. Restart the server')


def show_builtins():
    click.echo("BUILTINS")
    django_settings.configure()
    from two1.djangobitcoin.misc import urls as misc_urls
    from two1.djangobitcoin.scipy_aas import urls as scipy_urls
    from two1.djangobitcoin.static_serve import urls as static_serve_urls
    urls = misc_urls.urlpatterns + scipy_urls.urlpatterns + static_serve_urls.urlpatterns
    for u in urls:
        click.echo(u.regex.pattern)
