#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import os
import re

# Fix for issues with nosetests, experienced on win7
import multiprocessing

root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(root, "puremagic", "main.py"), "r") as reuse_file:
    reuse_content = reuse_file.read()

attrs = dict(re.findall(r"__([a-z]+)__ *= *['\"](.+)['\"]", reuse_content))

with open("README.rst", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name='puremagic',
    version=attrs['version'],
    url='https://github.com/cdgriffith/puremagic',
    license='MIT',
    author=attrs['author'],
    tests_require=["nose >= 1.3", "coverage >= 3.6", "argparse"],
    install_requires=["argparse"],
    author_email='chris@cdgriffith.com',
    description='Pure python implementation of magic file detection',
    long_description=long_description,
    package_data={'puremagic': ['*.json']},
    packages=['puremagic'],
    include_package_data=True,
    platforms='any',
    test_suite='nose.collector',
    classifiers=[
        'Programming Language :: Python',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: Implementation :: PyPy',
        'Development Status :: 4 - Beta',
        'Natural Language :: English',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Topic :: Utilities'
        ],
    extras_require={
        'testing': ["nose >= 1.3", "coverage >= 3.6", "argparse"],
        }
)
