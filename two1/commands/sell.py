import os
import click
import tempfile
import subprocess
from tabulate import tabulate
from two1.lib.util.uxstring import UxString


dir_to_absolute = lambda dirname: os.getcwd() + "/" + dirname


def install_requirements():
    """Install requirements needed to host an app
    using nginx.

    Returns:
        bool: True if the requirements were succesfully installed,
            False otherwise.
    """
    rv = False
    try:
        subprocess.check_output(
            "sudo apt-get install -y nginx && sudo pip3 install gunicorn",
            shell=True
        )
        rv = True
    except subprocess.CalledProcessError as e:
        raise e
    return rv


def create_default_nginx_server():
    """Creates a default server that hosts multiple
    nginx locations.

    Returns:
        bool: True if the process was succesfully completed,
            False otherwise.
    """
    rv = False
    with tempfile.NamedTemporaryFile() as tf:
        tf.write("""server {
       include /etc/nginx/site-includes/*;
}""".encode())
        tf.flush()
        try:
            subprocess.check_output([
                "sudo",
                "cp",
                tf.name,
                "/etc/nginx/sites-enabled/two1baseserver"
            ])
            subprocess.check_output([
                "sudo",
                "chmod",
                "644",
                "/etc/nginx/sites-enabled/two1baseserver"
            ])
            rv = True
        except subprocess.CalledProcessError:
            pass
    return rv


def create_site_includes():
    """Creates an /etc/nginx/site-includes.

    This contains nginx "location" blocks,
    http://nginx.org/en/docs/http/ngx_http_core_module.html#location
    which pertain to individual apps.

    Returns:
        bool: True if the process was succesfully completed,
            False otherwise.
    """
    rv = False
    if not os.path.isdir("/etc/nginx/site-includes"):
        subprocess.check_output([
                "sudo",
                "mkdir",
                "-p",
                "/etc/nginx/site-includes"
            ])
        rv = True
    return rv


def validate_directory(dirname):
    """Validate that the directory speicified
    has correct contents within it.

    ie. filen with name "index.py"
        - which has a variable "app" within it.

    Args:
        dirname (string): directory the app is located in.

    Returns:
        bool: True if the directory structure is valid,
            False otherwise.
    """
    rv = False
    try:
        appdir = dir_to_absolute(dirname)
        os.stat(appdir)
        indexpath = appdir + "index.py"
        with open(indexpath, "r") as indexfile:
            lines = indexfile.readlines()
            # quick check
            rv = len([l for l in lines if "app=" in l or "app =" in l]) > 0
    except (FileNotFoundError, OSError):
        pass
    return rv


def create_systemd_file(dirname):
    """Create a systemd file that manages the starting/stopping
    of the gunicorn process.

    All processes are bound to a socket by default within the
    app directory.

    Args:
        dirname (string): directory the app is located in.

    Returns:
        bool: True if the process was succesfully completed,
            False otherwise.
    """
    rv = False
    appdir = dir_to_absolute(dirname)
    appname = dirname.rstrip("/")
    # write systemd shit to tempfile
    with tempfile.NamedTemporaryFile() as tf:
        systemd_file = """[Unit]
Description=gunicorn daemon for %s
After=network.target

[Service]
WorkingDirectory=%s
ExecStart=/usr/local/bin/gunicorn index:app --workers 1 --bind unix:%s%s.sock

[Install]
WantedBy=default.target
        """ % (
            appname,
            appdir,
            appdir,
            appname
        )
        tf.write(systemd_file.encode())
        tf.flush()
        try:
            subprocess.check_output([
                "sudo",
                "cp",
                tf.name,
                "/etc/systemd/user/{}.service".format(appname)
            ])
            subprocess.check_output([
                "sudo",
                "chmod",
                "644",
                "/etc/systemd/user/{}.service".format(appname)
            ])
            subprocess.check_output([
                'systemctl',
                '--user',
                'enable',
                appname
            ])
            subprocess.check_output([
                'systemctl',
                '--user',
                'start',
                appname
            ])
            rv = True
        except subprocess.CalledProcessError as e:
            raise e
    return rv


def create_nginx_config(dirname):
    """Create a nginx location file that redirects
    all request with the prefix of the appname to the
    correct socket & process belonging to that app.

    i.e. curl 0.0.0.0/myapp1 shoudl redirect requests
    to unix:/mysocketpath.sock @ the route /

    This allows for multiple apps to be namespaced and
    hosted on a single machine.

    Args:
        dirname (string): directory the app is located in.

    Returns:
        bool: True if the process was succesfully completed,
            False otherwise.
    """
    rv = False
    appdir = dir_to_absolute(dirname)
    appname = dirname.rstrip("/")
    with tempfile.NamedTemporaryFile() as tf:
        nginx_site_includes_file = """location /%s {
        rewrite ^/%s(.*) /$1 break;
        proxy_pass http://unix:%s%s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
}""" % (
            appname, appname, appdir, appname
        )
        tf.write(nginx_site_includes_file.encode())
        tf.flush()
        try:
            subprocess.check_output([
                "sudo",
                "cp",
                tf.name,
                "/etc/nginx/sites-available/{}".format(appname)
            ])
            subprocess.check_output([
                "sudo",
                "chmod",
                "644",
                "/etc/nginx/sites-available/{}".format(appname)
            ])
            subprocess.check_output([
                "sudo",
                "rm",
                "-f",
                "/etc/nginx/site-includes/{}".format(appname)
            ])
            subprocess.check_output([
                "sudo",
                "ln",
                "-s",
                "/etc/nginx/sites-available/{}".format(appname),
                "/etc/nginx/site-includes/{}".format(appname),
            ])
            subprocess.check_output([
                "sudo",
                "service",
                "nginx",
                "restart"
            ])
            rv = True
        except subprocess.CalledProcessError as e:
            raise e
    return rv


@click.group()
def sell():
    """
    Sell 21 Apps on your 21 Bitcoin Computer.

\b
Usage
_____
Host your app in a production enviornment
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
def create(dirname):
    """
    Host your app on your 21 Bitcoin Computer in a production enviornment.

    Given a folder with specific files inside:
        -index.py
        -requirements.txt
    Host said app on host using nignx + gunicorn
    """
    if validate_directory(dirname):
        click.echo(UxString.app_directory_valid)
    else:
        click.echo(UxString.app_directory_invalid)
        return
    install_requirements()
    click.echo(UxString.installed_requirements)
    create_default_nginx_server()
    click.echo(UxString.created_nginx_server)
    create_site_includes()
    click.echo(UxString.created_site_includes)
    create_systemd_file(dirname)
    click.echo(UxString.created_systemd_file)
    create_nginx_config(dirname)
    click.echo(UxString.created_app_nginx_file)
    click.echo(UxString.hosted_app_location.format(dirname.rstrip("/")))


@sell.command()
def list():
    """
    List all currently running apps
\b
(as seen in /etc/nginx/site-includes/)
    """
    if os.path.isdir("/etc/nginx/site-includes/") \
            and len(os.listdir("/etc/nginx/site-includes/")) > 0:
        enabled_apps = os.listdir("/etc/nginx/site-includes/")
        click.echo(UxString.listing_enabled_apps)
        enabled_apps_table = []
        headers = ('No.', 'App name', 'Url')
        for i, enabled_app in enumerate(enabled_apps):
            enabled_apps_table.append([
                i,
                enabled_app,
                "http://0.0.0.0/{}".format(enabled_app)
                ])
        click.echo(tabulate(
            enabled_apps_table,
            headers=headers,
            tablefmt="psql",
        )
        )
    else:
        click.echo(UxString.no_apps_currently_running)


@sell.command()
@click.argument('appname')
def destroy(appname):
    """
    Stop/Remove a current app that is currently
    being run on the host.

\b
Stop worker processes and disable site from sites-enabled
    """
    if appname in os.listdir("/etc/nginx/site-includes/"):
        subprocess.check_output([
            "sudo",
            "rm",
            "-f",
            "/etc/nginx/site-includes/{}".format(appname)
        ])
        subprocess.check_output([
            "sudo",
            "rm",
            "-f",
            "/etc/systemd/user/{}.service".format(appname)
        ])
        subprocess.check_output([
            "systemctl",
            "--user",
            "stop",
            "{}".format(appname)
        ])
        subprocess.check_output([
            "sudo",
            "service",
            "nginx",
            "restart"
        ])
        click.echo(UxString.succesfully_stopped_app.format(appname))
    else:
        click.echo(UxString.app_not_enabled)


if __name__ == "__main__":
    sell()
