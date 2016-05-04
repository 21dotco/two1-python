# standard python imports
import os
import platform
from collections import namedtuple

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
                                       help_message="The `21 sell` service manager "
                                       "is not yet supported on the Bitcoin Computer. "
                                       "Please visit %s to get started hosting "
                                       "machine-payable servers on your Bitcoin "
                                       "Computer." % PING21_LEARN_URL,
                                       label="21bc")
        elif 'boot2docker' in detected_distro.lower():
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=False,
                                       help_message="The `21 sell` service manager is not "
                                       "yet supported within another boot2docker VM.",
                                       label="boot2docker")
        elif os.path.isfile('/sys/hypervisor/uuid') and (
                'debian-8.' in detected_distro.lower() or
                'ubuntu-14.04' in detected_distro.lower()):
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=True,
                                       help_message="",
                                       label="aws_ubuntu")
        elif 'debian' in detected_distro.lower() or 'ubuntu' in detected_distro.lower():
            return PlatformDescription(detected_os=detected_os,
                                       detected_distro=detected_distro,
                                       is_supported=False,
                                       help_message="The `21 sell` service manager is not "
                                       "yet available on this system.",
                                       label="")
    return PlatformDescription(detected_os=detected_os,
                               detected_distro=detected_distro,
                               is_supported=False,
                               help_message="",
                               label="The `21 sell` service manager is not yet "
                               "available on this system.")
