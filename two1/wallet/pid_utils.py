import os
import platform

from path import Path


def get_pid_file_dir():
    system = platform.system()
    pid_file_dir = ""
    if system == "Darwin":
        # pid_file_dir = Path("/private/var/run")
        pid_file_dir = Path("~/.two1/wallet").expanduser()
    elif system == "Linux":
        pid_file_dir = Path("/var/run")
    else:
        raise None

    return pid_file_dir


def get_pid_file():
    pid_file_dir = get_pid_file_dir()
    if pid_file_dir is None:
        ValueError("Unsupported system: %s" % platform.system())

    return pid_file_dir.joinpath("walletd.pid")


def check_pid_file():
    """ Checks for existence of a PID file.

        If it exists, return true if the PID is running
        or false if it doesn't.
    """
    pid_file = get_pid_file()
    rv = pid_file.exists()
    if rv:
        # See if the process is running
        pid = None
        with open(pid_file, "r") as p:
            pid = int(p.read().strip())

        if pid is not None:
            if check_pid(pid):
                rv = True
            else:
                # Stale pid file
                pid_file.unlink()
                rv = False
        else:
            rv = False

    return rv


def write_pid_file():
    rv = False
    if check_pid_file():
        rv = False
    else:
        pid_file = get_pid_file()
        with open(pid_file, 'w') as p:
            p.write("%d" % os.getpid())

        rv = check_pid_file()

    return rv


def cleanup_pid_file():
    pid_file = get_pid_file()
    if pid_file.exists():
        pid_file.unlink()


# Copied from: http://stackoverflow.com/questions/568271/how-to-check-if-there-exists-a-process-with-a-given-pid
def check_pid(pid):
    if pid < 0:
        return False
    if pid == 0:
        # According to "man 2 kill" PID 0 refers to every process
        # in the process group of the calling process.
        # On certain systems 0 is a valid PID but we have no way
        # to know that in a portable fashion.
        raise ValueError('invalid PID 0')
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        # There is a process but we don't have permissions
        return True
    except:
        raise

    return True
