# -*- coding: utf-8 -*-
from setuptools import setup

PACKAGE = 'irclogs'
VERSION = '0.2'

setup(
    name=PACKAGE,
    version=VERSION,
    packages=['irclogs'],
    package_data={
        'irclogs' : ['templates/*.cs', 'htdocs/*.css']
    },
    entry_points = {
        'trac.plugins': ['irclogs = irclogs']
    },
    install_requires = ['pyndexter>=0.2'],
)
