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

here = path.abspath(path.dirname(__file__))

with open(path.join(here, 'README.rst'), encoding='utf-8') as f:
    long_description = f.read()

install_requires = [
                    'arrow', 
                    'base58',
                    'Cython',
                    'pytest',
                    'requests',
                    'gunicorn',
                    'textblob',
                    'simplejson',
                    'django-filter',
                    'django-rest-swagger',
                    'djangorestframework',
                    'Markdown',
                    'PyYAML',
                    'cssselect',
                    'lxml',
                    'beautifulsoup4',
                    'pycoin',
                    'birdy',
                    'path.py',
                    'click',
                    'keyring',
                    ]

setup(
    name='two1',

    # Versions should comply with PEP440.  For a discussion on single-sourcing
    # the version across setup.py and the project code, see
    # https://packaging.python.org/en/latest/single_source_version.html
    version='0.1',
    description='Buy and sell anything on the internet with Bitcoin.',
    long_description=long_description,
    url='https://github.com/21dotco/two1',
    author='21, Inc',
    author_email='two1@21.co',
    license='MIT',

    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        'Development Status :: 1 - Planning',
        'Intended Audience :: Developers',
        'Topic :: Internet',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3.4',
    ],
    keywords='bitcoin blockchain client server',

    # You can just specify the packages manually here if your project is
    # simple. Or you can use find_packages().
    packages=['two1', 'two1.lib', 'two1.commands', 'two1.bitcoin', 'two1.mining', 'two1.wallet', 
            'two1.crypto','two1.bitcurl', 'two1.djangobitcoin.auth', 'two1.djangobitcoin.misc', 
            'two1.djangobitcoin.scipy', 'two1.djangobitcoin.static_serve'],

    # List run-time dependencies here.  These will be installed by pip when
    # your project is installed. For an analysis of "install_requires" vs pip's
    # requirements files see:
    # https://packaging.python.org/en/latest/requirements.html
    install_requires=install_requires,

    ext_modules=extensions,

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
        ],
    },
)
