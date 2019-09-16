#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""The setup script."""
#  Copyright 2018 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0

from setuptools import find_packages, setup

with open('README.md') as readme_file:
    readme = readme_file.read()

with open('CHANGELOG.md') as history_file:
    history = history_file.read()

install_requirements = [
    'aiohttp == 3.5.4',
    'aiojobs == 0.2.2',
    'appnope == 0.1.0',
    'async-timeout == 3.0.1',
    'attrs == 19.1.0',
    'awscli == 1.16.193',
    'backcall == 0.1.0',
    'botocore == 1.12.183',
    'cachetools == 3.1.1',
    'certifi == 2019.6.16',
    'chardet == 3.0.4',
    'Click == 7.0',
    'colorama == 0.3.9',
    'decorator == 4.4.0',
    'docutils == 0.14',
    'google-auth == 1.6.3',
    'idna == 2.8',
    'iso8601 == 0.1.12',
    'jedi == 0.14.0',
    'jmespath == 0.9.4',
    'kopf == 0.19',
    'kubernetes == 9.0.0',
    'multidict == 4.5.2',
    'oauthlib == 3.0.2',
    'parso == 0.5.0',
    'pexpect == 4.7.0',
    'pickleshare == 0.7.5',
    'prompt-toolkit == 2.0.9',
    'ptyprocess == 0.6.0',
    'pyasn1 == 0.4.5',
    'pyasn1-modules == 0.2.5',
    'Pygments == 2.4.2',
    'python-dateutil == 2.8.0',
    'PyYAML == 5.1',
    'requests == 2.22.0',
    'requests-oauthlib == 1.2.0',
    'rsa == 3.4.2',
    's3transfer == 0.2.1',
    'six == 1.12.0',
    'traitlets == 4.3.2',
    'urllib3 == 1.25.3',
    'wcwidth == 0.1.7',
    'websocket-client == 0.56.0',
    'yarl == 1.3.0'
]

setup_requirements = ['pytest-runner==2.11.1', ]

dev_requirements = [
    'bumpversion==0.5.3',
    'pkginfo==1.4.2',
    'twine==1.11.0',
    # not virtualenv: devs should already have it before pip-installing
    'watchdog==0.8.3',
]

test_requirements = [
    'codacy-coverage==1.3.11',
    'coverage==4.5.1',
    'mccabe==0.6.1',
    'pylint==2.2.2',
    'pytest==3.4.2',
    'tox==3.2.1',
]

setup(
    author="leucothia",
    author_email='devops@oceanprotocol.com',
    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Apache Software License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3.6',
        'Programming Language :: Python :: 3.7',
    ],
    description="🐳 Infrastructure Operator Micro-service",
    extras_require={
        'test': test_requirements,
        'dev': dev_requirements + test_requirements,
    },
    include_package_data=True,
    install_requires=install_requirements,
    keywords='operator-engine',
    license="Apache Software License 2.0",
    long_description=readme,
    long_description_content_type="text/markdown",
    name='operator-engine',
    packages=find_packages(include=['operator-engine']),
    setup_requires=setup_requirements,
    test_suite='tests',
    tests_require=test_requirements,
    url='https://github.com/oceanprotocol/operator-engine',
    version='0.0.1',
    zip_safe=False,
)
