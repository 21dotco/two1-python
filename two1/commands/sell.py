import json
import signal
from subprocess import Popen, PIPE

from re import split
import click
import os
from two1.config import pass_config
from two1.djangobitcoin.djangobitcoin.settings import ENDPOINTS_FILE
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


def try_config_django():
    try:
        from django.conf import settings as django_settings
        django_settings.configure()
        return True
    except Exception:
        click.echo('Error importing Django. It is installed?')
        return False


def find_endpoint(endpoint, package_name):
    try:
        package = __import__(package_name, fromlist=['urls'])
        urls = getattr(package, 'urls').urlpatterns
        if endpoint in map(lambda u: u.regex.pattern, urls):
            return package_name
    except Exception as e:
        click.echo('Error importing {0}: {1}'.format(package_name, e))
        return None


def find_process_by_attribute(attribute):
    # TODO: https://pypi.python.org/pypi/psutil/
    # http://stackoverflow.com/questions/682446/splitting-out-the-output-of-ps-using-python
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
    # Assumes gunicorn process is started via:
    # gunicorn --pythonpath two1/djangobitcoin djangobitcoin.wsgi --bind 127.0.0.1:8000
    # built-in django server is started python manage.py runserver 127.0.0.1:8000
    gunicorn_pid = find_process_by_attribute('djangobitcoin.wsgi')
    if gunicorn_pid:
        return gunicorn_pid, True
    django_svr_pid = find_process_by_attribute('runserver')
    if django_svr_pid:
        return django_svr_pid, False
    return None, None


def sell_item(item, port):
    if not try_config_django():
        return
    endpoints_path = os.path.join(dj_bt.__path__[0], ENDPOINTS_FILE)
    ep_json = json.load(open(endpoints_path))
    package = find_endpoint(item, 'two1.djangobitcoin.misc') \
              or find_endpoint(item, 'two1.djangobitcoin.scipy_aas') \
              or find_endpoint(item, 'two1.djangobitcoin.static_serve')
    if not package:
        click.echo('Endpoint {0} not found'.format(item))
        return
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
    click.echo('Endpoints configuration updated.')
    pid, is_gunicorn = find_process()
    if is_gunicorn:
        os.kill(int(pid), signal.SIGHUP)
        click.echo('Server restarted')
    elif pid:
        click.echo('Restart the server')


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
