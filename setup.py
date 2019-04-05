#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
Even for a larger incident response team handling all of the repetitive tasks
related to malware infections is a tedious task. Our malware analysts have
spent a lot of time chasing digital forensics from potentially infected macOS
systems, leveraging open source tools, like OSXCollector. Early on, we have
automated some part of the analysis process, augmenting the initial set of
digital forensics collected from the machines with the information gathered
from the threat intelligence APIs. They helped us with additional information
on potentially suspicious domains, URLs and file hashes. But our approach to
the analysis still required a certain degree of configuration and manual
maintenance that was consuming lots of attention from malware responders.

Enter automation: turning all of your repetitive tasks in a scripted way that
will help you deal faster with the incident discovery, forensic collection and
analysis, with fewer possibilities to make a mistake. We went ahead and turned
OSXCollector toolkit into AMIRA: Automated Malware Incident Response and
Analysis service. AMIRA turns the forensic information gathered by OSXCollector
into actionable response plan, suggesting the infection source as well as
suspicious files and domains requiring a closer look. Furthermore, we
integrated AMIRA with our incident response platform, making sure that as
little interaction as necessary is required from the analyst to follow the
investigation. Thanks to that, the incident response team members can focus on
what they excel at: finding unusual patterns and the novel ways that malware
was trying to sneak into the corporate infrastructure.
"""
from __future__ import absolute_import

from setuptools import find_packages
from setuptools import setup

from amira import __version__


with open('README.md', 'r') as fh:
    long_description = fh.read()

setup(
    name='amira',
    version=__version__,
    description='Automated Malware Incident Response and Analysis',
    long_description=long_description,
    long_description_content_type='text/markdown',
    author='Yelp Security',
    author_email='opensource@yelp.com',
    license='The MIT License (MIT)',
    url='https://github.com/Yelp/amira',
    setup_requires='setuptools',
    packages=find_packages(exclude=['tests']),
    provides=['amira'],
    install_requires=[
        'boto',
        'osxcollector_output_filters>=1.1.0',
        'simplejson',
    ],
)
