# standard python imports
import os
import platform
from collections import namedtuple

SUPPORTED_SYSTEMS = """`21 sell` is currently only available on
Mac OS X and Amazon Web Services (Supported Distributions: Ubuntu 14.04/16.04, CentOS 7 and Fedora 24)."""
PING21_LEARN_URL = "https://21.co/learn/ping21-earn-bitcoin-by-monitoring-uptime-and-latency"
PlatformDescription = namedtuple('PlatformDescription', ['detected_os',
                                                         'detected_distro',
                                                         'is_supported',
                                                         'help_message',
                                                         'label'])


def get_platform():
    """ Get system platform metadata.
    """
    detected_os = platform.system()
    detected_distro = platform.platform()

    if detected_os == "Darwin":
        return PlatformDescription(detected_os=detected_os,
                                   detected_distro=detected_distro,
                                   is_supported=True,
                                   help_message="",
                                   label="")
    elif detected_os == "Linux":
        if os.path.isfile('/proc/device-tree/hat/uuid'):
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=False,
                                       help_message="%s "
                                       "Please visit %s to get started hosting "
                                       "machine-payable servers on your Bitcoin "
                                       "Computer." % (SUPPORTED_SYSTEMS, PING21_LEARN_URL),
                                       label="21bc")
        elif 'boot2docker' in detected_distro.lower():
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=False,
                                       help_message="The `21 sell` service manager is not "
                                       "yet supported within another boot2docker VM.",
                                       label="boot2docker")
        elif (os.path.isfile('/sys/hypervisor/uuid') or os.path.isdir('/var/lib/digitalocean')) and (
                'debian-8.' in detected_distro.lower() or
                'ubuntu-14.04' in detected_distro.lower() or
                'ubuntu-16.04' in detected_distro.lower()):
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=True,
                                       help_message="",
                                       label="debian")
        elif os.path.isfile('/sys/hypervisor/uuid') and (
                'centos-7' in detected_distro.lower()):
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=True,
                                       help_message="",
                                       label="centos")
        elif os.path.isfile('/sys/hypervisor/uuid') and (
                'fedora-24' in detected_distro.lower()):
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=True,
                                       help_message="",
                                       label="fedora")
    return PlatformDescription(detected_os=detected_os,
                               detected_distro=detected_distro,
                               is_supported=False,
                               help_message=SUPPORTED_SYSTEMS,
                               label="")
