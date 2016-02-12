"""Helper methods for the 21 sell command."""
# standard python imports
import os
import tempfile
import subprocess

# 3rd party imports
import requests


def dir_to_absolute(dirname):
    """Return absolute directory if only
    folder name is provided."""
    if dirname[-1] != "/":
        dirname = dirname + '/'
    if dirname[0] != "/":
        dirname = os.getcwd() + "/" + dirname
    return dirname


def absolute_path_to_foldername(absolute_dir):
    """Return the name of the folder given
    an absolute path."""
    return os.path.split(absolute_dir.rstrip('/'))[-1]


def install_requirements():
    """Install requirements needed to host an app
    using nginx.

    Returns:
        bool: True if the requirements were successfully installed,
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


def check_or_create_manifest(dirname):
    """Create a manifest.json in application directory if it does not already
    exist.

    Returns:
        bool: True if the manifest was successfully found or created,
            False otherwise.
    """
    rv = False
    manifest_exists = False
    appdir = dir_to_absolute(dirname)
    manifest_path = appdir + "manifest.json"
    try:
        os.stat(manifest_path)
        manifest_exists = True
    except FileNotFoundError:
        pass
    if not manifest_exists:
        manifest_req = requests.get(
            "https://manifest.21.co/",
        )
        if manifest_req.ok:
            with tempfile.NamedTemporaryFile() as tf:
                tf.write(manifest_req.text.encode())
                tf.flush()
                cp = False
                ed = False
                try:
                    subprocess.check_output([
                        "cp",
                        tf.name,
                        manifest_path
                    ])
                    cp = True
                except subprocess.CalledProcessError as e:
                    raise subprocess.CalledProcessError(
                        "Failed to copy manifest to your local directory: {}".format(e))
                try:
                    subprocess.check_call([
                        "editor",
                        manifest_path
                        ])
                    ed = True
                except subprocess.CalledProcessError as e:
                    raise subprocess.CalledProcessError(
                        "Failed to edit your manifest: {}".format(e)
                    )
                rv = cp and ed
    else:
        rv = True
    return rv


def validate_directory(dirname):
    """Validate that the directory specified
    has correct contents within it.

    ie. file with name "index.py"
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


def create_site_includes():
    """Creates an /etc/nginx/site-includes.

    This contains nginx "location" blocks,
    http://nginx.org/en/docs/http/ngx_http_core_module.html#location
    which pertain to individual apps.

    Returns:
        bool: True if the process was successfully completed,
            False otherwise.
    """
    rv = False
    if os.path.isfile("/etc/nginx/sites-enabled/default"):
        subprocess.check_output([
            "sudo",
            "rm",
            "-f",
            "/etc/nginx/sites-enabled/default"
            ])
    if not os.path.isdir("/etc/nginx/site-includes"):
        subprocess.check_output([
            "sudo",
            "mkdir",
            "-p",
            "/etc/nginx/site-includes"
            ])
        rv = True
    return rv


def create_default_nginx_server():
    """Creates a default server that hosts multiple
    nginx locations.

    Returns:
        bool: True if the process was successfully completed,
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


def create_systemd_file(dirname):
    """Create a systemd file that manages the starting/stopping
    of the gunicorn process.

    All processes are bound to a socket by default within the
    app directory.

    Args:
        dirname (string): directory the app is located in.

    Returns:
        bool: True if the process was successfully completed,
            False otherwise.
    """
    rv = False
    appdir = dir_to_absolute(dirname)
    appname = absolute_path_to_foldername(appdir)
    with tempfile.NamedTemporaryFile() as tf:
        systemd_file = """[Unit]
Description=gunicorn daemon for %s
After=network.target

[Service]
WorkingDirectory=%s
ExecStart=/usr/local/bin/gunicorn index:app --workers 1 --bind unix:%s%s.sock --access-logfile %sgunicorn.access.log --error-logfile %sgunicorn.error.log

[Install]
WantedBy=default.target
        """ % (
            appname,
            appdir,
            appdir,
            appname,
            appdir,
            appdir
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
    all requests with the prefix of the appname to the
    correct socket & process belonging to that app.

    i.e. curl 0.0.0.0/myapp1 should redirect requests
    to unix:/mysocketpath.sock @ the route /

    This allows for multiple apps to be namespaced and
    hosted on a single machine.

    Args:
        dirname (string): directory the app is located in.

    Returns:
        bool: True if the process was successfully completed,
            False otherwise.
    """
    rv = False
    appdir = dir_to_absolute(dirname)
    appname = absolute_path_to_foldername(appdir)
    with tempfile.NamedTemporaryFile() as tf:
        nginx_site_includes_file = """location /%s {
        rewrite ^/%s(.*) /$1 break;
        proxy_pass http://unix:%s%s.sock;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
}""" % (appname, appname, appdir, appname)
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


def destroy_app(appname):
    """Removes nginx/systemd files from the system
    pertaining to the app specified.

    Args:
        appname (str): name of the enabled app.

    Returns:
        bool: True if the app was successfully destroyed,
            False otherwise.
    """
    rv = False
    try:
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
        rv = True
    except subprocess.CalledProcessError:
        pass
    return rv
