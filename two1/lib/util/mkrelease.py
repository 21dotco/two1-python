import os
import re
import subprocess


def create_version_file(version):
    """Print version to two1/version.py.

    Args:
        version (string): string representing current repo version.
    """
    version_file = 'VERSION = "{}"'.format(version)
    repo_dir = os.path.join(os.getcwd(), 'two1')
    f = open(repo_dir + '/version.py', 'w')
    f.write(version_file)
    f.close()


def create_sdist():
    """Run setup.py to create a gzip'ed tar file of the current version."""
    subprocess.check_call('python3 setup.py sdist --formats=gztar', shell=True)
    print('Two1 sdist created.')


def get_version_from_git():
    """Create a version using a string from `git describe`.

    Returns:
        (string): stringified version number.
        Format: [MAJOR].[MINOR].[PATCH]-[GIT_NUM]-[GIT_SHA]
        Example: 0.2.1-2-g1234SHA
    """
    git_version = subprocess.Popen(
        'git describe --always --tags --dirty',
        stdout=subprocess.PIPE, stderr=subprocess.PIPE,
        shell=True, universal_newlines=True)
    version = git_version.communicate()[0].strip()
    return version


def main():
    """Script to make and package a new release."""
    # Get current git version relative to the most recent tag
    version = get_version_from_git()

    # Print to verison.py file
    create_version_file(version)

    # Create new dist
    create_sdist()


if __name__ == '__main__':
    main()
