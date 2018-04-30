#!/usr/bin/env python

from setuptools import setup, find_packages
setup(
    name="alertsync",
    version="0.1",
    version_format='{tag}.dev{commitcount}+{gitsha}',
    author='CFPB',
    author_email='tech@cfpb.gov',
    maintainer='cfpb',
    maintainer_email='tech@cfpb.gov',
    packages=find_packages(),
    entry_points={
        'console_scripts': [
            'alertsync=alertsync.__main__:main'
        ]
    },
    setup_requires=['setuptools-git-version==1.0.3'],
)
