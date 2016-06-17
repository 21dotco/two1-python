""" Installer for 21 sell service manager.
"""
# standard python imports
import os
import sys
import subprocess
from abc import ABCMeta
from abc import abstractmethod


class Two1SellInstaller:
    """ OS-specific installer handler.
    """

    SERVICE_DIR = os.path.expanduser("~/.two1/services")
    DB_DIR = os.path.join(SERVICE_DIR, 'db_dir')
    DOCKER_TOOLS = ["Virtualbox", "Docker Machine", "Docker Compose", "Docker"]

    def __init__(self, system, distro):
        """ Init installer handler.
        """

        if system == "Darwin":
            # mac os x
            self.installer = InstallerMac()
        elif system == "Linux" and (
                'debian-8.' in distro.lower() or
                'ubuntu-14.04' in distro.lower() or
                'ubuntu-16.04' in distro.lower() or
                'centos' in distro.lower()):
            # ubuntu/debian aws
            self.DOCKER_TOOLS.remove('Virtualbox')
            self.DOCKER_TOOLS.remove('Docker Machine')
            self.installer = InstallerDebian()
        else:
            sys.exit()

    def install_zerotier(self):
        """ Install ZeroTier One service for virtual networking.
        """
        zt = self.installer.install_zerotier()
        if zt == 0:
            return True
        else:
            return False

    def install_docker_tools(self):
        """ Install Docker tools for vm and container management.
        """
        dt = self.installer.install_docker_tools()
        if dt == 0:
            return True
        else:
            return False

    def check_dependencies(self):
        """ Check if system dependencies installed.
        """
        return self.installer.check_dependencies()


class InstallerBase:
    """ Abstract base Installer.

    Each OS installer must implement this base class.

    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def program_installed(self, pname):
        return

    @abstractmethod
    def install_zerotier(self):
        """ Install Zerotier for network virtualization.
        """
        return

    @abstractmethod
    def install_docker_tools(self):
        """ Install docker, docker-machine, docker-compose.
        """
        return

    @abstractmethod
    def check_dependencies(self):
        """ Checks if all dependencies are installed
        """
        return


class InstallerMac(InstallerBase):
    """ Mac OS X Installer.
    """
    VERSION_OS = subprocess.check_output(["uname", "-s"]).decode()
    VERSION_HW = subprocess.check_output(["uname", "-m"]).decode()

    # zerotier
    ZEROTIER_PKG_URL = "https://download.zerotier.com/dist/"
    ZEROTIER_PKG = "ZeroTier One.pkg"

    # docker toolbox
    DOCKER_TOOLBOX_URL = "https://github.com/docker/toolbox/releases/download/v1.11.0/DockerToolbox-1.11.0.pkg"
    DOCKER_TOOLBOX_PKG = DOCKER_TOOLBOX_URL.split("/")[-1]

    # virtualbox
    VBOX_BINARY_URL = "http://download.virtualbox.org/virtualbox/5.0.16/VirtualBox-5.0.16-105871-OSX.dmg"
    VBOX_BINARY = VBOX_BINARY_URL.split("/")[-1]

    def __init__(self):
        """ Init Mac Installer.
        """
        self._copy_services()
        self._make_tmp()

    def _copy_services(self):
        try:
            if "services" not in os.listdir(os.path.expanduser("~/.two1")):
                os.makedirs(Two1SellInstaller.DB_DIR, exist_ok=True)

            subprocess.check_output(["cp", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                                        "util", "schema.sql"),
                                     Two1SellInstaller.DB_DIR])
        except Exception:
            raise

    def _make_tmp(self):
        try:
            if "tmp" not in os.listdir(os.path.expanduser("~/.two1")):
                subprocess.check_output(["mkdir", "-p", os.path.expanduser("~/.two1/tmp/")])
        except Exception as e:
            print(e)

    def check_dependencies(self):
        """ Check for 21 sell dependencies.
        """
        installed = []
        packages = ["Virtualbox"]
        try:
            subprocess.check_output(["vboxmanage", "--version"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        packages.append("Docker Machine")
        try:
            subprocess.check_output(["docker-machine", "version"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        packages.append("Docker Compose")
        try:
            subprocess.check_output(["docker-compose", "version"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        packages.append("Docker")
        try:
            subprocess.check_output(["docker", "--version"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        packages.append("Zerotier")
        try:
            subprocess.check_output(["zerotier-cli", "-v"])
        except:
            installed.append(False)
        else:
            installed.append(True)
        return list(zip(packages, installed))

    def _cleanup(self):
        """ Clean up installation directory.
        """
        try:
            subprocess.check_output(["rm", "-rf", os.path.expanduser("~/.two1/tmp/")],
                                    stderr=subprocess.DEVNULL)
        except Exception as e:
            print(e)

    def program_installed(self, pname):
        """ Check if program exists.

        Args:
            pname: Program name to check
        """
        try:
            subprocess.check_output(["hash", pname], stderr=subprocess.DEVNULL)
        except:
            return False
        else:
            return True

    def install_zerotier(self):
        """ Install Zerotier virual network service.

        Sources:
            https://www.zerotier.com/product-one.shtml
        """
        if not self.program_installed("zerotier-cli"):
            self._make_tmp()
            try:
                subprocess.check_output(["curl", InstallerMac.ZEROTIER_PKG_URL +
                                        InstallerMac.ZEROTIER_PKG.replace(" ", "%20"),
                                        "-o",
                                         os.path.expanduser("~/.two1/tmp/") +
                                         InstallerMac.ZEROTIER_PKG.replace(" ", "-")],
                                        stderr=subprocess.DEVNULL)
                subprocess.check_output(["sudo", "installer", "-pkg",
                                        os.path.expanduser("~/.two1/tmp/") +
                                        InstallerMac.ZEROTIER_PKG.replace(" ", "-"),
                                        "-target", "/"],
                                        stderr=subprocess.DEVNULL)
                exit_code = 0
            except Exception as e:
                print(e)
                exit_code = 1
            self._cleanup()
        else:
            exit_code = 0
        return exit_code

    def install_virtual_box(self):
        """ Install virtual box on Mac OS X.
        """
        if not self.program_installed("vboxmanage"):
            self._make_tmp()
            try:
                subprocess.check_output(["curl", "-L", InstallerMac.VBOX_BINARY_URL, "-o",
                                         os.path.expanduser("~/.two1/tmp/") + InstallerMac.VBOX_BINARY])
                subprocess.check_output(["hdiutil", "mount", InstallerMac.VBOX_BINARY])
                subprocess.check_output(["sudo", "installer", "-pkg", "/Volumes/VirtualBox/VirtualBox.pkg",
                                         "-target", "/"])
                subprocess.check_output(["hdiutil", "unmount", "/Volumes/VirtualBox/"])
                subprocess.check_output(["rm", InstallerMac.VBOX_BINARY])
            except Exception as e:
                print(e)

    def install_docker_tools(self):
        """ Install Docker Toolbox on Mac OS X.

            This installs all necessary dependencies for the `21 sell` stack.
        """
        docker = self.program_installed("docker")
        docker_compose = self.program_installed("docker-compose")
        docker_machine = self.program_installed("docker-machine")
        virtualbox = self.program_installed("vboxmanage")
        all_installed = docker and docker_compose and docker_machine and virtualbox
        if not all_installed:
            try:
                self._make_tmp()
                subprocess.check_output(["curl", "-L", InstallerMac.DOCKER_TOOLBOX_URL, "-o",
                                        os.path.expanduser("~/.two1/tmp/") +
                                        InstallerMac.DOCKER_TOOLBOX_PKG],
                                        stderr=subprocess.DEVNULL)
                subprocess.check_output(["sudo", "installer", "-pkg",
                                        os.path.expanduser("~/.two1/tmp/") +
                                        InstallerMac.DOCKER_TOOLBOX_PKG,
                                        "-target", "/"],
                                        stderr=subprocess.DEVNULL)
                exit_code = 0
            except:
                exit_code = 1
            self._cleanup()
        else:
            exit_code = 0
        return exit_code


class InstallerDebian(InstallerBase):
    """ Debian/Ubuntu Installer.
    """

    # zerotier
    ZEROTIER_PKG_URL = "https://download.zerotier.com/dist/"
    ZEROTIER_PKG = "zerotier-one_1.1.4_amd64.deb"

    def __init__(self):
        """ Init Debian/Ubuntu Installer. """
        self._copy_services()

    def program_installed(self, pname):
        """ Check if program exists.

        Args:
            pname: Program name to check
        """
        try:
            subprocess.check_output(["hash", pname], stderr=subprocess.DEVNULL)
        except:
            return False
        else:
            return True

    def _copy_services(self):
        """ Copy services to .two1 directory.
        """
        try:
            if "services" not in os.listdir(os.path.expanduser("~/.two1")):
                subprocess.check_output(["mkdir", "-p", os.path.expanduser("~/.two1/services/")])
                subprocess.check_output(["mkdir", "-p", Two1SellInstaller.DB_DIR])
            subprocess.check_output(
                ["cp", os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                    "util", "schema.sql"),
                 Two1SellInstaller.DB_DIR])
        except Exception:
            raise

    def check_dependencies(self):
        """ Check for 21 sell dependencies.
        """
        installed = []
        packages = ["Docker Compose"]
        try:
            subprocess.check_output(["docker-compose", "version"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        packages.append("Docker")
        try:
            subprocess.check_output(["docker", "--version"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        packages.append("Zerotier")
        try:
            subprocess.check_output(["zerotier-cli", "-v"])
        except:
            installed.append(False)
        else:
            installed.append(True)

        return list(zip(packages, installed))

    def already_in_group(self):
        """ Check if user in Docker unix group.

        Returns: (bool) True:  if user does not need to log in again.
                 (bool) False: otherwise.
        """
        return 'docker' in subprocess.check_output(['groups'],
                                                   universal_newlines=True,
                                                   stderr=subprocess.DEVNULL)

    def install_zerotier(self):
        """ Install ZeroTier One virtual network service.

        Sources:
            https://www.zerotier.com/product-one.shtml
        """
        zt_in = "URL='{}{}'; FILE=`mktemp`; wget \"$URL\" -qO $FILE && sudo dpkg -i $FILE; rm $FILE"
        if not self.program_installed("zerotier-cli"):
            try:
                subprocess.check_output(zt_in.format(
                    self.ZEROTIER_PKG_URL, self.ZEROTIER_PKG), shell=True, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                return e.returncode
        return 0

    def install_docker_tools(self):
        """ Install Docker Compose and Docker Enginer on AWS Linux.
        """
        docker = self.program_installed("docker")
        docker_compose = self.program_installed("docker-compose")
        if not docker:
            try:
                subprocess.check_output("curl -fsSL https://get.docker.com/ | sh", shell=True,
                                        stderr=subprocess.DEVNULL)
                subprocess.check_output("sudo usermod -aG docker `whoami`",
                                        shell=True,
                                        stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                return e.returncode

        if not docker_compose:
            try:
                subprocess.check_output(
                    "URL=https://github.com/docker/compose/releases/download/1.7.0/docker-compose"
                    "-`uname -s`-`uname -m`; FILE=`mktemp tmp.XXXXX`; wget \"$URL\" -qO $FILE && "
                    "sudo mv $FILE /usr/local/bin/docker-compose && "
                    "chmod +x /usr/local/bin/docker-compose",
                    shell=True, stderr=subprocess.DEVNULL)
            except subprocess.CalledProcessError as e:
                return e.returncode

        return 0
