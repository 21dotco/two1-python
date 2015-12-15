import os
import click
import tempfile
import subprocess
from tabulate import tabulate


dir_to_absolute = lambda dirname: os.getcwd() + "/" + dirname


def install_requirements():
    """Install requirements needed to host an app
    using nginx.
    """
    try:
        subprocess.check_output(
            "sudo apt-get install -y nginx && sudo pip3 install gunicorn",
            shell=True
        )
    except subprocess.CalledProcessError as e:
        raise e


def create_default_nginx_server():
    """Creates a default server that hosts multiple
    nginx locations.
    """
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
            return True
        except subprocess.CalledProcessError:
            return False


def create_site_includes():
    """Creates an /etc/nginx/site-includes.

    This contains nginx "location" blocks,
    http://nginx.org/en/docs/http/ngx_http_core_module.html#location
    which pertain to individual apps.
    """
    if not os.path.isdir("/etc/nginx/site-includes"):
        subprocess.check_output([
                "sudo",
                "mkdir",
                "-p",
                "/etc/nginx/site-includes"
            ])


def validate_directory(dirname):
    """Validate that the directory speicified
    has correct contents within it.

    ie. filen with name "index.py"
        - which has a variable "app" within it.
    """
    try:
        appdir = dir_to_absolute(dirname)
        os.stat(appdir)
        indexpath = appdir + "index.py"
        with open(indexpath, "r") as indexfile:
            lines = indexfile.readlines()
            # quick check
            return len([l for l in lines if "app=" in l or "app =" in l]) > 0
    except (FileNotFoundError, OSError):
        return False


def create_systemd_file(dirname):
    """Create a systemd file that manages the starting/stopping
    of the gunicorn process."""
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
WantedBy=multi-user.target
        """ % (
            appname,
            appdir,
            appdir,
            appname
        )
        print(systemd_file)
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
        except subprocess.CalledProcessError as e:
            raise e


def create_nginx_config(dirname):
    """Create a nginx config file to redirect
    the socket from the gunicorn process into
    0.0.0.0/."""
    appdir = dir_to_absolute(dirname)
    appname = dirname.rstrip("/")
    with tempfile.NamedTemporaryFile() as tf:
        nginx_enabled_site_file = """location /%s {
        rewrite ^/%s(.*) /$1 break;
        proxy_pass http://unix:%s%s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }""" % (
            appname, appname, appdir, appname
        )
        print(nginx_enabled_site_file)
        tf.write(nginx_enabled_site_file.encode())
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
        except subprocess.CalledProcessError as e:
            raise e


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
        click.echo(click.style("App Directory Valid...", fg="magenta"))
    else:
        click.echo(click.style("App Directory Invalid. Please ensure \
            your directory and it's contents are correct,\
            refer to 21.co/app for futher instructions.", fg="red"))
        return
    install_requirements()
    click.echo(click.style("Installed requirements...", fg="magenta"))
    create_default_nginx_server()
    click.echo(click.style("Created default 21 nginx server...", fg="magenta"))
    create_site_includes()
    click.echo(click.style("Created site-includes to host apps...",
                           fg="magenta"))
    create_systemd_file(dirname)
    click.echo(click.style("Systemd file created...", fg="magenta"))
    create_nginx_config(dirname)
    click.echo(click.style("Nginx file created...", fg="magenta"))
    click.echo(
        click.style(
            "Your app is now hosted at http://0.0.0.0/{}".format(
                dirname.rstrip("/")
            ),
            fg="magenta"
        )
    )


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
        click.echo(click.style("Listing enabled apps...", fg="magenta"))
        enabled_apps_table = []
        headers = ('No.', 'App name')
        for i, enabled_app in enumerate(enabled_apps):
            enabled_apps_table.append([i, enabled_app])
        click.echo(tabulate(
            enabled_apps_table,
            headers=headers,
            tablefmt="psql",
        )
        )
    else:
        click.echo(click.style(
            "No apps currently running, refer to 21.co/sell to host some...",
            fg="red")
        )


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
        click.echo(
            click.style(
                "Succesfully stopped {}...".format(appname),
                fg="magenta")
        )
    else:
        click.echo(
            click.style("This app is not within your enabled apps.", fg="red"))

if __name__ == "__main__":
    sell()
