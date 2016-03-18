"""Helper methods for the 21 sell command."""
# standard python imports
import os
import tempfile
import subprocess
import platform
import shutil

from two1.commands.util import exceptions
from two1.commands.util.uxstring import UxString


def detect_url(url):
    """Detect type of url specified,
    ie. git style or tarball
    Args:
        url (str): specified url
    Rasies:
        NotImplementedError: if url type
            is not supported yet.
    Returns:
        str: type of path
    """
    rv = ""
    if url.endswith(".git"):
        rv = "git"
    else:
        raise exceptions.Two1Error(UxString.error.url_not_supported)
    return rv


def clone_repo(appname, url):
    """Clone a git repo.
    Args:
        appame (str): name of the application.
        url (str): git repo url
    Returns:
        bool: success of the cloned repo.
    """
    rv = False
    if not os.path.exists(appname):
        try:
            subprocess.check_output([
                "git",
                "clone",
                url
                ])
            rv = True
        except subprocess.CalledProcessError as e:
            raise exceptions.Two1Error(
                UxString.error.repo_clone_fail.format(e))
    else:
        rv = True
    return rv


def detect_os():
    """Detect if the operating system
    that is running is either osx, debian-based
    or other.

    Returns:
        str: platform name
    Raises:
        OSError: if platform is not supported
    """
    plat = platform.system().lower()
    if plat in ['debian', 'linux']:
        return 'debian'
    elif 'darwin' in plat:
        return 'darwin'
    else:
        raise exceptions.Two1Error(UxString.unsupported_platform)


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


def install_python_requirements(dirname):
    """Install the python requirements needed
    to run the app

    Args:
        dirname (str) : directory of the app
    Returns:
        bool: True if successfully installed,
            False otherwise.
    """
    rv = False
    appdir = dir_to_absolute(dirname)
    try:
        subprocess.check_output(
            "sudo -H pip3 install -r {}requirements.txt".format(appdir),
            shell=True
            )
        rv = True
    except subprocess.CalledProcessError as e:
        raise exceptions.Two1Error(
            UxString.unsuccessfull_python_requirements.fomat(e))
    return rv


def install_server_requirements(dirname):
    """Install requirements needed to host an app
    using nginx.

    Returns:
        bool: True if the requirements were successfully installed,
            False otherwise.
    """
    rv = False
    try:
        if "debian" in detect_os():
            subprocess.check_output(
                "sudo apt-get install -y nginx \
                && sudo -H pip3 install gunicorn",
                shell=True
            )
        if "darwin" in detect_os():
            if not shutil.which("brew"):
                raise exceptions.Two1Error(
                    UxString.install_brew
                )
            subprocess.check_output(
                "brew install nginx",
                shell=True)
            subprocess.check_output(
                "sudo pip3 install gunicorn",
                shell=True
            )
        rv = True
    except (subprocess.CalledProcessError, OSError) as e:
        raise exceptions.Two1Error(
            UxString.unsuccessfull_server_requirements.fomat(e))
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
    plat = detect_os()
    rv = False

    if os.path.isfile("{}/etc/nginx/sites-enabled/default".format(
        "/usr/local" if "darwin" in plat else "")
    ):
        subprocess.check_output([
            "sudo",
            "rm",
            "-f",
            "{}/etc/nginx/sites-enabled/default".format(
                "/usr/local" if "darwin" in plat else "")
            ])
    if not os.path.isdir("{}/etc/nginx/site-includes".format(
        "/usr/local" if "darwin" in plat else "")
    ):
        subprocess.check_output([
            "sudo",
            "mkdir",
            "-p",
            "{}/etc/nginx/site-includes".format(
                "/usr/local" if "darwin" in plat else "")
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
    plat = detect_os()
    rv = False
    with tempfile.NamedTemporaryFile() as tf:
        server = """server {
       include %s/etc/nginx/site-includes/*;
}""" % ("/usr/local" if "darwin" in plat else "")
        tf.write(server.encode())
        tf.flush()
        try:
            subprocess.check_output([
                "sudo",
                "cp",
                tf.name,
                "{}/etc/nginx/sites-enabled/two1baseserver".format(
                    "/usr/local" if "darwin" in plat else ""
                )
            ])
            subprocess.check_output([
                "sudo",
                "chmod",
                "644",
                "{}/etc/nginx/sites-enabled/two1baseserver".format(
                    "/usr/local" if "darwin" in plat else ""
                )
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
    plat = detect_os()
    if "darwin" in plat:
        raise exceptions.Two1Error(
                UxString.unsupported_platform
            )
    appdir = dir_to_absolute(dirname)
    appname = absolute_path_to_foldername(appdir)
    with tempfile.NamedTemporaryFile() as tf:
        systemd_file = """[Unit]
Description=gunicorn daemon for %s
After=network.target

[Service]
WorkingDirectory=%s
ExecStart=/usr/local/bin/gunicorn ping21-server:app --workers 1 --bind unix:%s%s.sock --access-logfile %sgunicorn.access.log --error-logfile %sgunicorn.error.log

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
    plat = detect_os()
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
                "{}/etc/nginx/sites-available/{}".format(
                    "/usr/local" if "darwin" in plat else "",
                    appname
                )
            ])
            subprocess.check_output([
                "sudo",
                "chmod",
                "644",
                "{}/etc/nginx/sites-available/{}".format(
                        "/usr/local" if "darwin" in plat else "",
                        appname
                    )
            ])
            subprocess.check_output([
                "sudo",
                "rm",
                "-f",
                "{}/etc/nginx/site-includes/{}".format(
                        "/usr/local" if "darwin" in plat else "",
                        appname
                    )
            ])
            subprocess.check_output([
                "sudo",
                "ln",
                "-s",
                "{}/etc/nginx/sites-available/{}".format(
                    "/usr/local" if "darwin" in plat else "",
                    appname),
                "{}/etc/nginx/site-includes/{}".format(
                    "/usr/local" if "darwin" in plat else "",
                    appname)
            ])
            if "darwin" in plat:
                if os.path.exists("/usr/local/var/run/nginx.pid"):
                    subprocess.check_output("sudo nginx -s stop", shell=True)
                subprocess.check_output("sudo nginx", shell=True)
            else:
                subprocess.check_output([
                    "sudo",
                    "service",
                    "nginx",
                    "restart"
                ])
            rv = True
        except subprocess.CalledProcessError as e:
            raise exceptions.Two1Error(
                UxString.failed_configuring_nginx.format(e))
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
