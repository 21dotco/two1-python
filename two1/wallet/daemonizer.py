import subprocess
import sys
import xml.etree.ElementTree as ET

import locale
import re
import shutil
import tempfile
from path import Path
from two1.wallet.exceptions import DaemonizerError
from two1.wallet.exceptions import WalletError


def get_daemonizer():
    """ Returns the appropriate daemonizer class for the system.

    Returns:
        Daemonizer: A daemonizer class that can be used to install/uninstall,
            enable/disable, and start/stop the daemon. If the init system of
            the OS is not supported, this will be None.
    """
    rv = None
    if sys.platform == 'darwin':
        rv = Launchd
    elif sys.platform == 'linux':
        if Systemd.check_systemd():
            rv = Systemd
        else:
            raise OSError("Currently the only supported linux init system is systemd.")
    else:
        raise OSError("Currently only Mac OS X (launchd) and linux (systemd) system daemons are supported.")

    return rv


class Daemonizer(object):
    """ Abstract base class for installing/enabling/disabling the two1
        wallet daemon.

        All methods are class methods and as such do not require an instance
        for functionality.
    """

    @classmethod
    def installed(self):
        """ Returns whether or not the daemon has been installed into
        the init system.

        Returns:
            bool: True if the daemon has been installed, False otherwise.
        """
        raise NotImplementedError

    @classmethod
    def install(self):
        """ Installs the daemon into the init system.

        Returns:
            bool: True if the daemon was successfully installed, False
                otherwise.
        """
        raise NotImplementedError

    @classmethod
    def uninstall(self):
        """ Un-installs the daemon from the init system.

        Returns:
            bool: True if the daemon was successfully un-installed, False
                otherwise.
        """
        raise NotImplementedError

    @classmethod
    def enabled(self):
        """ Returns whether or not the daemon has been enabled in
        the init system.

        Returns:
            bool: True if the daemon has been enabled, False otherwise.
        """
        raise NotImplementedError

    @classmethod
    def enable(self):
        """ Enables the daemon within the init system.

        Returns:
            bool: True if the daemon was successfully enabled, False
                otherwise.
        """
        raise NotImplementedError

    @classmethod
    def disable(self):
        """ Disables the daemon within the init system.

        Returns:
            bool: True if the daemon was successfully disabled, False
                otherwise.
        """
        raise NotImplementedError

    @classmethod
    def started(self):
        """ Returns whether or not the daemon has been started and is
        currently running.

        Returns:
            bool: True if the daemon is running, False otherwise.
        """
        raise NotImplementedError

    @classmethod
    def start(self):
        """ Starts the daemon.

        Returns:
            bool: True if the daemon was successfully started, False
                otherwise.
        """
        raise NotImplementedError

    @classmethod
    def stop(self):
        """ Stops the daemon.

        Returns:
            bool: True if the daemon was successfully stopped, False
                otherwise.
        """
        raise NotImplementedError


class Systemd(Daemonizer):
    """ Class for installing/enabling/disabling the two1 wallet daemon
        on linux systems using systemd as their init system.

        All methods are class methods and as such do not require an instance
        for functionality.
    """
    ENV_FILE_PATH = Path("/etc/sysconfig/two1")
    SERVICE_NAME = "two1-wallet.service"
    SERVICE_FILE_PATH = Path("/etc/systemd/user/").joinpath(SERVICE_NAME)
    SERVICE_FILE = """[Unit]
Description=two1 wallet daemon
After=network.target

[Service]
ExecStart=%s
EnvironmentFile=%s

[Install]
WantedBy=default.target
""" % (shutil.which('walletd'),
       ENV_FILE_PATH)

    @staticmethod
    def check_systemd():
        """ Checks to see if systemd/systemctl are installed.

        Returns:
            bool: True if both systemd and systemctl are installed and
                in the path.
        """
        return shutil.which("systemctl") is not None

    @classmethod
    def _service_status(cls):
        """ Parses the output of systemctl --user status to determine
            the current status of the two1-wallet service.

        Returns:
            dict: Containing two keys "service_found" and "status".
                service_found will be True if the service was found and
                has a status to report. status will be one of [enabled,
                disabled, active] or None.
        """
        rv = dict(service_found=False, status=None)
        try:
            sc = subprocess.check_output(["systemctl",
                                          "--user",
                                          "status",
                                          cls.SERVICE_NAME],
                                         stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError as e:
            sc = e.output

        m1 = re.search("Loaded:\s+(\S+)\s+\(([^\)]+)\)", sc.decode())
        m2 = re.search("Active:\s+(\S+)", sc.decode())
        if m1 and len(m1.groups()) == 2:
            if m1.group(1) == "loaded":
                rv['service_found'] = True
                if "enabled" in m1.group(2):
                    if m2 and len(m2.groups()) == 1:
                        rv['status'] = m2.group(1)
                    else:
                        rv['status'] = "enabled"
                elif "disabled" in m1.group(2):
                    rv['status'] = "disabled"

        return rv

    @classmethod
    def _write_env_file(cls, text):
        """ Writes a file containing environment variables that
            should be set to run the daemon.

        Args:
            text (str): The complete text that should be written to the
                file.

        Returns:
            bool: True if the file was successfully created and written to,
                False otherwise.
        """
        rv = False
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(text.encode())
            tf.flush()
            try:
                subprocess.check_output(["sudo",
                                         "mkdir",
                                         "-p",
                                         cls.ENV_FILE_PATH.dirname()])
                subprocess.check_output(["sudo",
                                         "cp",
                                         tf.name,
                                         cls.ENV_FILE_PATH])
                subprocess.check_output(["sudo",
                                         "chmod",
                                         "644",
                                         cls.ENV_FILE_PATH])

                rv = cls.ENV_FILE_PATH.exists()
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't create environment file: %s" %
                                      (e))

        return rv

    @classmethod
    def _write_service_file(cls, text):
        """ Writes a file containing the parameters required for systemd
            to daemonize the process.

        Args:
            text (str): The complete text that should be written to the
                file.

        Returns:
            bool: True if the file was successfully created and written to,
                False otherwise.
        """
        rv = False
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(text.encode())
            tf.flush()
            try:
                subprocess.check_output(["sudo",
                                         "cp",
                                         tf.name,
                                         cls.SERVICE_FILE_PATH])
                subprocess.check_output(["sudo",
                                         "chmod",
                                         "644",
                                         cls.SERVICE_FILE_PATH])

                rv = cls.SERVICE_FILE_PATH.exists()
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't create service file: %s" % (e))

        return rv

    @classmethod
    def installed(cls):
        """ Returns whether or not the daemon has been installed into
        systemd's user config area.

        Returns:
            bool: True if the daemon has been installed, False otherwise.
        """
        return cls.SERVICE_FILE_PATH.exists() and cls.ENV_FILE_PATH.exists()

    @classmethod
    def install(cls, data_provider_options={}):
        """ Installs the daemon into the user config area of /etc/systemd.

        Args:
            data_provider_options (dict): A dict containing the following
                key/value pairs:
                'provider': Name of the blockchain data provider to use.
                'api_key_id': The API key to use (if required by the provider).
                'api_key_secret': The API secret to use (if required)

        Returns:
            bool: True if the daemon was successfully installed, False
                otherwise.
        """
        rv = False
        if cls.installed():
            rv = True
        else:
            # Make sure systemd is installed
            if cls.check_systemd():
                text = "\n"
                if data_provider_options.get('provider', None) == 'chain':
                    # Create an environment file
                    text = "CHAIN_API_KEY_ID='%s'\n" % data_provider_options['api_key_id']
                    text += "CHAIN_API_KEY_SECRET='%s'\n" % data_provider_options['api_key_secret']

                # Add default locale info based on current user's settings
                locale_info = ".".join(locale.getlocale())
                for env_var in ["LC_ALL", "LANG"]:
                    text += "{}={}\n".format(env_var, locale_info)

                # Create ENV file (even if empty)
                cls._write_env_file(text)

                # Create service file
                cls._write_service_file(cls.SERVICE_FILE)
                rv = cls.installed()

        return rv

    @classmethod
    def uninstall(cls):
        """ Un-installs the daemon from systemd by removing the service
        file from /etc/systemd/user.

        Returns:
            bool: True if the daemon was successfully un-installed, False
                otherwise.
        """
        if cls.SERVICE_FILE_PATH.exists():
            cls.SERVICE_FILE_PATH.unlink()

        return not cls.SERVICE_FILE_PATH.exists()

    @classmethod
    def enabled(cls):
        """ Returns whether or not the daemon has been enabled in systemd.

        Returns:
            bool: True if the daemon has been enabled, False otherwise.
        """
        res = cls._service_status()
        return res['service_found'] and res['status'] != "disabled"

    @classmethod
    def enable(cls):
        """ Enables the daemon within systemd.

        Returns:
            bool: True if the daemon was successfully enabled, False
                otherwise.
        """
        rv = False
        if not cls.installed():
            cls.install()

        if cls.installed():
            try:
                sc = subprocess.check_output(["systemctl",
                                              "--user",
                                              "enable",
                                              cls.SERVICE_NAME],
                                             stderr=subprocess.STDOUT)
                rv = cls.enabled()
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't enable service: %s" % e)
                rv = False

        return rv

    @classmethod
    def disable(cls):
        """ Disables the daemon within systemd.

        Returns:
            bool: True if the daemon was successfully disabled, False
                otherwise.
        """
        rv = False
        try:
            subprocess.check_output(["systemctl",
                                     "--user",
                                     "disable",
                                     cls.SERVICE_NAME],
                                    stderr=subprocess.STDOUT)
            rv = not cls.enabled()
        except subprocess.CalledProcessError as e:
            raise DaemonizerError("Couldn't disable service: %s" % e)

        return rv

    @classmethod
    def started(cls):
        """ Returns whether or not the daemon has been started and is
        currently running.

        Returns:
            bool: True if the daemon is running, False otherwise.
        """
        res = cls._service_status()
        return res['service_found'] and res['status'] == "active"

    @classmethod
    def start(cls):
        """ Starts the daemon.

        Returns:
            bool: True if the daemon was successfully started, False
                otherwise.
        """
        rv = False
        if not cls.enabled():
            cls.enable()

        if cls.enabled():
            try:
                subprocess.check_output(["systemctl",
                                         "--user",
                                         "start",
                                         cls.SERVICE_NAME],
                                        stderr=subprocess.STDOUT)
                rv = cls.started()
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't start service: %s" % e)

        return rv

    @classmethod
    def stop(cls):
        """ Stops the daemon.

        Returns:
            bool: True if the daemon was successfully stopped, False
                otherwise.
        """
        rv = False

        if cls.started():
            try:
                subprocess.check_output(["systemctl",
                                         "--user",
                                         "stop",
                                         cls.SERVICE_NAME])
                rv = not cls.started()
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't stop service: %s" % e)

        return rv


class Launchd(Daemonizer):
    """ Class for installing/enabling/disabling the two1 wallet daemon
        on Mac OS X systems using launchd as their init system.

        All methods are class methods and as such do not require an instance
        for functionality.
    """
    PLIST_FILE_PATH = Path("~/Library/LaunchAgents/com.two1.walletd.plist").expanduser()
    AGENT_LABEL = "com.two1.walletd"

    @staticmethod
    def indent(elem, level=0):
        """ Pretty-ifies XML string output.
        """
        i = "\n" + level*"  "
        if len(elem):
            if not elem.text or not elem.text.strip():
                elem.text = i + "  "
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
            for elem in elem:
                Launchd.indent(elem, level+1)
            if not elem.tail or not elem.tail.strip():
                elem.tail = i
        else:
            if level and (not elem.tail or not elem.tail.strip()):
                elem.tail = i

    @classmethod
    def _list_to_xml(cls, l):
        x = ET.Element("array")
        for i in l:
            if isinstance(i, str):
                ve = ET.Element("string")
                ve.text = i
            elif isinstance(i, bool):
                ve = ET.Element("true" if i else "false")
            elif isinstance(i, list) or isinstance(i, tuple):
                ve = cls._list_to_xml(i)
            elif isinstance(i, dict):
                ve = cls._dict_to_xml(i)

            x.append(ve)

        return x

    @classmethod
    def _dict_to_xml(cls, d):
        x = ET.Element("dict")
        for k, v in d.items():
            ke = ET.Element("key")
            ke.text = k
            x.append(ke)

            ve = None
            if isinstance(v, str):
                ve = ET.Element("string")
                ve.text = v
            elif isinstance(v, bool):
                ve = ET.Element("true" if v else "false")
            elif isinstance(v, list) or isinstance(v, tuple):
                ve = cls._list_to_xml(v)
            elif isinstance(v, dict):
                ve = cls._dict_to_xml(v)

            x.append(ve)

        return x

    @classmethod
    def _create_plist_file(cls, env_vars={}):
        """ Creates a PLIST file for launchd.

            PLIST files are XML docs with certain parameters
            required to start the daemon.
        """
        walletd_path = shutil.which('walletd')
        if walletd_path is None:
            raise WalletError("walletd has not been installed correctly!")

        locale_info = ".".join(locale.getlocale())
        for l in ["LC_ALL", "LANG"]:
            if l not in env_vars:
                env_vars[l] = locale_info

        d = dict(EnvironmentVariables=env_vars,
                 KeepAlive=True,
                 Label=cls.AGENT_LABEL,
                 ProcessType="Background",
                 ProgramArguments=[walletd_path])

        pl = ET.Element("plist", dict(version="1.0"))
        pl.append(cls._dict_to_xml(d))

        cls.indent(pl)

        xml_str = b'<?xml version="1.0" encoding="UTF-8"?>\n'
        xml_str += b'<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">\n'
        xml_str += ET.tostring(pl, encoding='UTF-8')

        cls.PLIST_FILE_PATH.write_text(xml_str.decode(), encoding='UTF-8')

    @classmethod
    def installed(cls):
        """ Returns whether or not the daemon has been installed into
        launchd.

        Returns:
            bool: True if the daemon has been installed, False otherwise.
        """
        return cls.PLIST_FILE_PATH.exists()

    @classmethod
    def install(cls, data_provider_options={}):
        """ Installs the launchd agent into ~/Library/LaunchAgents

        Args:
            data_provider_options (dict): A dict containing the following
                key/value pairs:
                'provider': Name of the blockchain data provider to use.
                'api_key_id': The API key to use (if required by the provider).
                'api_key_secret': The API secret to use (if required)

        Returns:
            bool: True if the daemon was successfully installed, False
                otherwise.
        """
        dpo = data_provider_options
        rv = False

        if cls.installed():
            rv = True
        else:
            # Figure out data provider stuff
            env_vars = {}
            if dpo.get('provider', None) == 'chain':
                env_vars["CHAIN_API_KEY_ID"] = dpo['api_key_id']
                env_vars["CHAIN_API_KEY_SECRET"] = dpo['api_key_secret']

            try:
                cls._create_plist_file(env_vars)
                rv = cls.installed()
            except WalletError as e:
                raise DaemonizerError("Couldn't install launchd agent: %s" % e)

        return rv

    @classmethod
    def uninstall(cls):
        """ Un-installs the agent from launchd by removing the PLIST
        file from ~/Library/LaunchAgents.

        Returns:
            bool: True if the daemon was successfully un-installed, False
                otherwise.
        """
        cls.stop()
        if cls.PLIST_FILE_PATH.exists():
            cls.PLIST_FILE_PATH.unlink()

        return not cls.PLIST_FILE_PATH.exists()

    @classmethod
    def enabled(cls):
        """ Returns whether or not the agent has been enabled. For launchd,
        this is equivalent to installing the PLIST file.

        Returns:
            bool: True if the agent has been installed, False otherwise.
        """
        return cls.installed()

    @classmethod
    def enable(cls):
        """ Enables the agent within launchd. Since installing is the
        equivalent of enabling in launchd, this simply returns whether
        the agent has been installed or not.

        Returns:
            bool: True if the agent is installed, False otherwise.
        """
        return cls.installed()

    @classmethod
    def disable(cls):
        """ Disables the agent by removing the PLIST file.

        Returns:
            bool: True if the agent was successfully uninstalled, False
                otherwise.
        """
        return cls.uninstall()

    @classmethod
    def started(cls):
        """ Returns whether or not the agent has been started and is
        currently running.

        Returns:
            bool: True if the agent is running, False otherwise.
        """
        rv = False
        lc = ""
        try:
            lc = subprocess.check_output(['launchctl',
                                          'list',
                                          cls.AGENT_LABEL],
                                         stderr=subprocess.STDOUT)
            m = re.search('"PID"\s+=\s+(\d+)', lc.decode())
            rv = m is not None
        except subprocess.CalledProcessError:
            # Means that the process wasn't found
            pass

        return rv

    @classmethod
    def start(cls):
        """ Starts the agent.

        Returns:
            bool: True if the agent was successfully started, False
                otherwise.
        """
        rv = False
        if not cls.enabled():
            cls.enable()

        if cls.started():
            rv = True
        elif cls.enabled():
            try:
                subprocess.check_output(['launchctl',
                                         'load',
                                         '-w',
                                         cls.PLIST_FILE_PATH],
                                        stderr=subprocess.STDOUT)
                rv = cls.started()
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't enable daemon using launchctl: %s" % e)

        return rv

    @classmethod
    def stop(cls):
        """ Stops the agent.

        Returns:
            bool: True if the agent was successfully stopped, False
                otherwise.
        """
        rv = True
        if cls.started():
            try:
                subprocess.check_output(['launchctl',
                                         'unload',
                                         '-w',
                                         cls.PLIST_FILE_PATH],
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                raise DaemonizerError("Couldn't disable daemon using launchctl: %s" % e)

        return rv
