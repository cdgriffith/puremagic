#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup
import os
import re


root = os.path.abspath(os.path.dirname(__file__))

with open(os.path.join(root, "puremagic", "main.py"), "r") as reuse_file:
    reuse_content = reuse_file.read()

attrs = dict(re.findall(r"__([a-z]+)__ *= *['\"](.+)['\"]", reuse_content))

with open("README.rst", "r") as readme_file:
    long_description = readme_file.read()

setup(
    name="puremagic",
    version=attrs["version"],
    url="https://github.com/cdgriffith/puremagic",
    license="MIT",
    author=attrs["author"],
    author_email="chris@cdgriffith.com",
    description="Pure python implementation of magic file detection",
    long_description=long_description,
    package_data={"puremagic": ["*.json"]},
    packages=["puremagic"],
    include_package_data=True,
    platforms="any",
    classifiers=[
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: PyPy",
        "Development Status :: 5 - Production/Stable",
        "Natural Language :: English",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Utilities",
    ],
)
