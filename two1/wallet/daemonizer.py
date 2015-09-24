import locale
import re
import shutil
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

from path import Path

from two1.wallet.exceptions import WalletError


def get_daemonizer():
    rv = None
    if sys.platform == 'darwin':
        rv = Launchd
    elif sys.platform == 'linux':
        if Systemd.check_systemd():
            rv = Systemd
        else:
            print("Currently the only supported linux init system is systemd.")
    else:
        print("Currently only Mac OS X (launchd) and linux (systemd) system daemons are supported.")

    return rv


class Daemonizer(object):
    """ Abstract base class for installing/enabling/disabling the two1
        wallet daemon.
    """

    @classmethod
    def installed(self):
        raise NotImplementedError

    @classmethod
    def install(self):
        raise NotImplementedError

    @classmethod
    def uninstall(self):
        raise NotImplementedError

    @classmethod
    def enabled(self):
        raise NotImplementedError

    @classmethod
    def enable(self):
        raise NotImplementedError

    @classmethod
    def disable(self):
        raise NotImplementedError

    @classmethod
    def started(self):
        raise NotImplementedError

    @classmethod
    def start(self):
        raise NotImplementedError

    @classmethod
    def stop(self):
        raise NotImplementedError


class Systemd(Daemonizer):
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
       ENV_FILE_PATH.joinpath('two1'))

    @staticmethod
    def check_systemd():
        return shutil.which("systemd") is not None and \
            shutil.which("systemctl") is not None

    @classmethod
    def _service_status(cls):
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
        rv = False
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(text)
            try:
                subprocess.check_output(["sudo",
                                         "mkdir -p",
                                         cls.ENV_FILE_PATH.dirname()])
                subprocess.check_output(["sudo",
                                         "cp",
                                         tf.name,
                                         cls.ENV_FILE_PATH])
                rv = cls.ENV_FILE_PATH.exists()
            except subprocess.CalledProcessError as e:
                print("Error creating environment file: %s" % (e))
                rv = False

        return rv

    @classmethod
    def _write_service_file(cls, text):
        rv = False
        with tempfile.NamedTemporaryFile() as tf:
            tf.write(text)
            try:
                subprocess.check_output(["sudo",
                                         "cp",
                                         tf.name,
                                         cls.SERVICE_FILE_PATH])
                rv = cls.SERVICE_FILE_PATH.exists()
            except subprocess.CalledProcessError as e:
                print("Error creating service file: %s" % (e))
                rv = False

        return rv

    @classmethod
    def installed(cls):
        return cls.SERVICE_FILE_PATH.exists() and cls.ENV_FILE_PATH.exists()

    @classmethod
    def install(cls, data_provider_options):
        rv = False
        if cls.installed():
            rv = True
        else:
            # Make sure systemd is installed
            if cls.check_systemd():
                try:
                    if data_provider_options['provider'] == 'chain':
                        # Create an environment file
                        text = "CHAIN_API_KEY_ID='%s'\n" % data_provider_options['api_key_id']
                        text += "CHAIN_API_KEY_SECRET='%s'\n" % data_provider_options['api_key_secret']

                        cls._write_env_file(text)

                    # Create service file
                    cls._write_service_file(cls.SERVICE_FILE)
                    rv = cls.installed()
                except PermissionError:
                    print("Please re-run this script with sudo.")

        return rv

    @classmethod
    def uninstall(cls):
        # Remove the service file
        if cls.SERVICE_FILE_PATH.exists():
            cls.SERVICE_FILE_PATH.unlink()

        return not cls.SERVICE_FILE_PATH.exists()

    @classmethod
    def enabled(cls):
        res = cls._service_status()
        return res['service_found'] and res['status'] != "disabled"

    @classmethod
    def enable(cls):
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
                print("Error enabling service: %s" % e)
                rv = False

        return rv

    @classmethod
    def disable(cls):
        rv = False
        try:
            subprocess.check_output(["systemctl",
                                     "--user",
                                     "disable",
                                     cls.SERVICE_NAME],
                                    stderr=subprocess.STDOUT)
            rv = not cls.enabled()
        except subprocess.CalledProcessError as e:
            print("Error disabling service: %s" % e)
            rv = False

        return rv

    @classmethod
    def started(cls):
        res = cls._service_status()
        return res['service_found'] and res['status'] == "active"

    @classmethod
    def start(cls):
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
                print("Error starting service: %s" % e)
                rv = False

        return rv

    @classmethod
    def stop(cls):
        rv = False

        if cls.started():
            try:
                subprocess.check_output(["systemctl",
                                         "--user",
                                         "stop",
                                         cls.SERVICE_NAME])
                rv = not cls.started()
            except subprocess.CalledProcessError as e:
                print("Error stopping service: %s" % e)
                rv = False

        return rv


class Launchd(Daemonizer):
    PLIST_FILE_PATH = Path("~/Library/LaunchAgents/com.two1.walletd.plist").expanduser()
    AGENT_LABEL = "com.two1.walletd"

    @staticmethod
    def indent(elem, level=0):
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
        return cls.PLIST_FILE_PATH.exists()

    @classmethod
    def install(cls, data_provider_options):
        dpo = data_provider_options
        rv = False

        if cls.installed():
            rv = True
        else:
            # Figure out data provider stuff
            env_vars = {}
            if dpo['provider'] == 'chain':
                env_vars["CHAIN_API_KEY_ID"] = dpo['api_key_id']
                env_vars["CHAIN_API_KEY_SECRET"] = dpo['api_key_secret']

            try:
                cls._create_plist_file(env_vars)
                rv = cls.installed()
            except WalletError as e:
                print("Couldn't install launchd agent: %s" % e)
                rv = False

        return rv

    @classmethod
    def uninstall(cls):
        if cls.PLIST_FILE_PATH.exists():
            cls.PLIST_FILE_PATH.unlink()

        return not cls.PLIST_FILE_PATH.exists()

    @classmethod
    def enabled(cls):
        return cls.installed()

    @classmethod
    def enable(cls):
        return cls.installed()

    @classmethod
    def disable(cls):
        return cls.uninstall()

    @classmethod
    def started(cls):
        # Need to do launchctl list com.two1.walletd and
        # analyze output
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
                print("Couldn't enable daemon using launchctl: %s" % e)
                rv = False

        return rv

    @classmethod
    def stop(cls):
        rv = True
        if cls.started():
            try:
                subprocess.check_output(['launchctl',
                                         'unload',
                                         '-w',
                                         cls.PLIST_FILE_PATH],
                                        stderr=subprocess.STDOUT)
            except subprocess.CalledProcessError as e:
                print("Couldn't disable daemon using launctl: %s" % e)
                rv = False

        return rv
