import click
from django.conf import settings as django_settings
from two1.config import pass_config


@click.command()
@click.option('--builtin', is_flag=True, help='Show built-in endpoints.')
@pass_config
def sell(config, port=8000, builtin=False):
    "Set up a new machine-payable endpoint"
    if builtin:
        show_builtins()
        return
    endpoint = 'en2cn'
    click.echo('Selling %s on http://127.0.0.1:%d/' % (endpoint, port))
    return


def show_builtins():
    click.echo("BUILTINS")
    django_settings.configure()
    from two1.djangobitcoin.misc import urls as misc_urls
    from two1.djangobitcoin.scipy import urls as scipy_urls
    from two1.djangobitcoin.djangobitcoin import settings
    from two1.djangobitcoin.static_serve import urls as static_serve_urls
    urls = misc_urls.urlpatterns + scipy_urls.urlpatterns + static_serve_urls.urlpatterns
    for u in urls:
        click.echo(u.regex.pattern)
    pass
