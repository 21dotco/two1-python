"""
Launch a machine-payable endpoint on the current machine
"""
# standard python imports
import os

# 3rd party imports
import click
from tabulate import tabulate

# two1 imports
from two1.lib.util.uxstring import UxString
from two1.commands.helpers.sell_helpers import install_requirements
from two1.commands.helpers.sell_helpers import validate_directory
from two1.commands.helpers.sell_helpers import create_site_includes
from two1.commands.helpers.sell_helpers import create_default_nginx_server
from two1.commands.helpers.sell_helpers import create_systemd_file
from two1.commands.helpers.sell_helpers import create_nginx_config
from two1.commands.helpers.sell_helpers import destroy_app
from two1.commands.helpers.sell_helpers import dir_to_absolute
from two1.commands.helpers.sell_helpers import absolute_path_to_foldername
from two1.commands.helpers.sell_helpers import check_or_create_manifest


@click.group()
def sell():
    """
    Sell 21 Apps on your 21 Bitcoin Computer.

\b
Usage
_____
Host your app in a production environment
$ 21 sell create myapp/

\b
See the help for create
$ 21 sell create --help

\b
List all of your currently running apps
$ 21 sell list

\b
See the help for list
$ 21 sell list --help

\b
Destroy one of your currently running apps
$ 21 sell destroy myapp

\b
See the help for list
$ 21 sell destroy --help
    """
    pass


@sell.command()
@click.argument('dirname', type=click.Path(exists=True))
@click.pass_context
def create(ctx, dirname):
    """
    Host your app on your 21 Bitcoin Computer in a production environment.

Given a folder with specific files inside:
\n    -index.py
\n    -requirements.txt
\n
Host said app on host (0.0.0.0/) using nginx + gunicorn
    """
    config = ctx.obj["config"]
    if validate_directory(dirname):
        config.log(UxString.app_directory_valid)
    else:
        config.log(UxString.app_directory_invalid)
        return
    config.log(UxString.check_or_create_manifest_file)
    if check_or_create_manifest(dirname):
        config.log(UxString.success_manifest)
    else:
        config.log(UxString.manifest_fail)
    config.log(UxString.installing_requirements)
    install_requirements()
    config.log(UxString.installed_requirements)
    create_default_nginx_server()
    config.log(UxString.created_nginx_server)
    create_site_includes()
    config.log(UxString.created_site_includes)
    create_systemd_file(dirname)
    config.log(UxString.created_systemd_file)
    create_nginx_config(dirname)
    config.log(UxString.created_app_nginx_file)
    appdir = dir_to_absolute(dirname)
    appname = absolute_path_to_foldername(appdir)
    config.log(UxString.hosted_app_location.format(appname))


@sell.command()
@click.pass_context
def list(ctx):
    """
    List all currently running apps
\b
(as seen in /etc/nginx/site-includes/)
    """
    #pylint: disable=redefined-builtin
    config = ctx.obj["config"]
    if os.path.isdir("/etc/nginx/site-includes/") \
            and len(os.listdir("/etc/nginx/site-includes/")) > 0:
        enabled_apps = os.listdir("/etc/nginx/site-includes/")
        config.log(UxString.listing_enabled_apps)
        enabled_apps_table = []
        headers = ('No.', 'App name', 'Url')
        for i, enabled_app in enumerate(enabled_apps):
            enabled_apps_table.append([
                i,
                enabled_app,
                "http://0.0.0.0/{}".format(enabled_app)
                ])
        config.log(tabulate(
            enabled_apps_table,
            headers=headers,
            tablefmt="psql",))
    else:
        config.log(UxString.no_apps_currently_running)


@sell.command()
@click.argument('appname')
@click.pass_context
def destroy(ctx, appname):
    """
    Stop/Remove a current app that is currently
    being run on the host.

\b
Stop worker processes and disable site from sites-enabled
    """
    #pylint: disable=redefined-builtin
    config = ctx.obj["config"]
    if appname in os.listdir("/etc/nginx/site-includes/"):
        if destroy_app(appname):
            config.log(UxString.successfully_stopped_app.format(appname))
        else:
            config.log(UxString.failed_to_destroy_app)
    else:
        config.log(UxString.app_not_enabled)
