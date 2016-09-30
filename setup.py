# -*- Mode: Python -*-
"""two1

This tool uses the official PyPa packaging and click recommendations:
https://github.com/pypa/sampleproject
https://packaging.python.org/en/latest/distributing.html
http://click.pocoo.org/4/setuptools/
"""
from setuptools import setup


install_requires = [
    'arrow',
    'base58',
    'click==6.6',
    'docker-py==1.8.0',
    'flake8',
    'jsonrpcclient==2.0.1',
    'jsonrpcserver==3.1.1',
    'mnemonic==0.13',
    'path.py',
    'pexpect',
    'protobuf==3.0.0a3',
    'pyaes',
    'pytest',
    'pyyaml',
    'requests',
    'sha256',
    'tabulate',
]

version = __import__('two1').TWO1_VERSION

setup(
    name='two1',
    version=version,
    description='Buy and sell anything on the internet with bitcoin.',
    url='https://21.co',
    author='21',
    author_email='support@21.co',
    license='FreeBSD',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Developers',
        'Topic :: Internet',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='bitcoin blockchain client server',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['two1',
              'two1.mkt',
              'two1.sell',
              'two1.sell.util',
              'two1.sell.exceptions',
              'two1.lib',
              'two1.commands',
              'two1.bitcoin',
              'two1.server',
              'two1.bitserv',
              'two1.wallet',
              'two1.crypto',
              'two1.channels',
              'two1.bitserv.django',
              'two1.bitserv.flask',
              'two1.blockchain',
              'two1.bitrequests',
              'two1.commands.util',
    ],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=install_requires,

    ext_modules=[],

    # List additional groups of dependencies here (e.g. development
    # dependencies). You can install these using the following syntax,
    # for example:
    # $ pip install -e .[dev,test]
    extras_require={
        'dev': ['check-manifest'],
        'test': ['coverage'],
    },

    # If there are data files included in your packages that need to be
    # installed, specify them here.  If using Python 2.6 or less, then these
    # have to be included in MANIFEST.in as well.
    package_data={
        'two1': ['two1-config.json',
                 'sell/util/scripts/ps_zerotier.sh',
                 'sell/util/scripts/zerotier_installer.sh',
                 'sell/blueprints/base/Dockerfile',
                 'sell/blueprints/router/Dockerfile',
                 'sell/blueprints/router/files/nginx.conf',
                 'sell/blueprints/payments/Dockerfile',
                 'sell/blueprints/payments/requirements.txt',
                 'sell/blueprints/payments/login.py',
                 'sell/blueprints/payments/server.py',
                 'sell/blueprints/services/ping/Dockerfile',
                 'sell/blueprints/services/ping/ping21.py',
                 'sell/blueprints/services/ping/requirements.txt',
                 'sell/blueprints/services/ping/server.py',
                 'sell/blueprints/services/ping/manifest.yaml',
                 'sell/blueprints/services/ping/login.py',
                 'sell/util/schema.sql']
    },

    # Although 'package_data' is the preferred approach, in some case you may
    # need to place data files outside of your packages. See:
    # http://docs.python.org/3.4/distutils/setupscript.html#installing-additional-files # noqa
    # In this case, 'data_file' will be installed into '<sys.prefix>/my_data'
    # data_files=[('peers', ['data/default-peers.json'])],

    # To provide executable scripts, use entry points in preference to the
    # "scripts" keyword. Entry points provide cross-platform support and allow
    # pip to create the appropriate form of executable for the target platform.
    # See: http://stackoverflow.com/a/782984/72994
    # http://click.pocoo.org/4/setuptools/
    entry_points={
        'console_scripts': [
            'two1=two1.cli:main',
            'wallet=two1.wallet.cli:main',
            '21=two1.cli:main',
            'twentyone=two1.cli:main',
            'channels=two1.channels.cli:main',
        ],
    },
)
