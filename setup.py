# -*- Mode: Python -*-
"""two1

This tool uses the official PyPa packaging and click recommendations:
https://github.com/pypa/sampleproject
https://packaging.python.org/en/latest/distributing.html
http://click.pocoo.org/4/setuptools/
"""
from setuptools import setup
from setuptools import find_packages
from codecs import open
from os import path
import os


here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

install_requires = [
                    'arrow',
                    'base58',
                    'pytest',
                    'requests',
                    'responses',
                    'simplejson',
                    'sha256',
                    'path.py',
                    'click==4.1',
                    'mnemonic',
                    'protobuf==3.0.0a3',
                    'pyaes',
                    'tabulate',
                    'jsonrpcclient',
                    'jsonrpcserver>=3.0.0',
                    ]

version = __import__('two1').__version__

setup(
    name='two1',
    version=version,
    description='Buy and sell anything on the internet with Bitcoin.',
    long_description=long_description,
    url='https://github.com/21dotco/two1',
    author='21',
    author_email='21@21.co',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Topic :: Internet',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='bitcoin blockchain client server',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['two1', 'two1.lib', 'two1.commands', 'two1.lib.bitcoin',
              'two1.lib.mining', 'two1.lib.server', 'two1.lib.wallet',
              'two1.lib.crypto', 'two1.lib.bitserv',
              'two1.lib.bitserv.django', 'two1.lib.bitserv.flask',
              'two1.lib.blockchain', 'two1.lib.bitcurl', 'two1.lib.util',
              'two1.examples.server',
              'two1.examples.bitcoin_auth', 'two1.examples.server.misc',
              'two1.examples.server.scipy_aas'],

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
        'two1': ['two1-config.json'],
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
            'wallet=two1.lib.wallet.cli:main',
            '21=two1.cli:main',
            'twentyone=two1.cli:main',
            'walletd=two1.lib.wallet.daemon:main'
        ],
    },
)
