#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

from setuptools import find_packages, setup

with open("README.md") as readme_file:
    readme = readme_file.read()

with open("CHANGELOG.md") as history_file:
    history = history_file.read()

install_requirements = [
    "kopf",
    "kubernetes",
    "web3",
    "psycopg2",
    "eth_account",
    "coloredlogs",
]

setup_requirements = [
    "pytest-runner",
]

dev_requirements = [
    "bumpversion==0.5.3",
    "pkginfo==1.4.2",
    "twine==1.11.0",
    "flake8",
    "isort",
    "black==22.1.0",
    "pre-commit",
    "licenseheaders",
    "pytest-env",
    # not virtualenv: devs should already have it before pip-installing
    "watchdog==0.8.3",
]

test_requirements = [
    "codacy-coverage",
    "coverage",
    "mccabe",
    "pylint",
    "pytest",
    "pytest-watch",
]

setup(
    author="leucothia",
    author_email="devops@oceanprotocol.com",
    classifiers=[
        "Development Status :: 2 - Pre-Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Natural Language :: English",
        "Programming Language :: Python :: 3.6",
        "Programming Language :: Python :: 3.7",
    ],
    description="🐳 Infrastructure Operator Micro-service",
    extras_require={
        "test": test_requirements,
        "dev": dev_requirements + test_requirements,
    },
    include_package_data=True,
    install_requires=install_requirements,
    keywords="operator-engine",
    license="Apache Software License 2.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    name="operator-engine",
    packages=find_packages(include=["operator-engine"]),
    setup_requires=setup_requirements,
    test_suite="tests",
    tests_require=test_requirements,
    url="https://github.com/oceanprotocol/operator-engine",
    version="0.0.1",
    zip_safe=False,
)
