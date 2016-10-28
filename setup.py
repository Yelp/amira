#!/usr/bin/python
# -*- coding: utf-8 -*-
from __future__ import absolute_import

from setuptools import find_packages
from setuptools import setup

from amira import __version__

setup(
    name="amira",
    version=__version__,
    description="Automated Malware Incident Response and Analysis.",
    author="Yelp Security",
    author_email="opensource@yelp.com",
    setup_requires="setuptools",
    packages=find_packages(exclude=["tests"]),
    provides=["amira"],
    install_requires=[
        "boto",
        "osxcollector_output_filters",
        "simplejson",
    ],
)
