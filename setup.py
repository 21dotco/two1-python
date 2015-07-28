# -*- Mode: Python -*-

from setuptools import setup, find_packages

try:
    from Cython.Build import cythonize
    extensions = cythonize(['two1/bitcoin/sha256.pyx'])
except:
    from distutils.extension import Extension
    extensions = [Extension("sha256", ["two1/bitcoin/sha256.c"])]

setup (
    name='two1',
    version='0.1.0',
    description='Open-sourced projects by 21, Inc.',
    url='https://github.com/21dotco/two1',
    maintainer='Nigel Drego',
    maintainer_email='nigel@21.co',
    packages=find_packages(),
    install_requires=['cython'],
    ext_modules=extensions
)
