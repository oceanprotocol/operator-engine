#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
from os import getenv


class OperatorConfig:
    NETWORK = getenv('NETWORK', 'pacific')
    ACCOUNT_JSON = getenv('ACCOUNT_JSON')
    ACCOUNT_PASSWORD = getenv('ACCOUNT_PASSWORD')
    INPUTS_FOLDER = getenv('INPUTS_FOLDER', '/data/inputs')
    TRANSFORMATIONS_FOLDER = getenv('TRANSFORMATIONS_FOLDER', '/data/transformations')
    POD_CONFIGURATION_CONTAINER = getenv('POD_CONFIGURATION_CONTAINER', 'pedrogp/ocean-pod-configuration:latest')
    WORKFLOW = getenv('WORKFLOW', '/workflow.json')
    POD_CONFIGURATION_INIT_SCRIPT = """#!/usr/bin/env bash -e

    touch /data/test1
    echo 'The first container was here' > /data/test1 
    sleep 1000
    """


class VolumeConfig:
    VOLUME_SIZE = getenv('VOLUME_SIZE', '2Gi')
    STORAGE_CLASS = getenv('STORAGE_CLASS', 'gp2')


class ExternalURLs:
    BRIZO_URL = getenv('BRIZO_URL', 'https://brizo.commons.oceanprotocol.com')
    AQUARIUS_URL = getenv('AQUARIUS_URL', 'https://aquarius.commons.oceanprotocol.com')
    KEEPER_URL = getenv('KEEPER_URL', 'https://pacific.oceanprotocol.com')
    SECRET_STORE_URL = getenv('SECRET_STORE_URL', 'https://secret-store.oceanprotocol.com')


class Metadata:
    TITLE = 'Operator service'
    DESCRIPTION = 'Infrastructure Kubernetes Operator'

# export BRIZO_URL='https://brizo.nile.dev-ocean.com'
# export AQUARIUS_URL='https://aquarius.nile.dev-ocean.com'
# export KEEPER_URL='https://nile.dev-ocean.com'
# export SECRET_STORE_URL='https://secret-store.nile.dev-ocean.com'
# export ACCOUNT_JSON='{"id":"7a08e6f8-cc89-9793-f82c-5978bfaa2b97","version":3,"crypto":{"cipher":"aes-128-ctr","cipherparams":{"iv":"dc91f4ecd2559cd13246c37e6be94347"},"ciphertext":"8fbdb2f26784844c0e9911b1e88c1fba47c91aaf05b398b8d115a32a7f8899e2","kdf":"pbkdf2","kdfparams":{"c":10240,"dklen":32,"prf":"hmac-sha256","salt":"536e1fdf947d1a2690e33358d7c27b470a4d4712f5d0b50bad7643d86a708c90"},"mac":"f21057ec25b1bd6dc5ba12e4aed5f0f4cc8785bb2dcf14e55306b69eef4c2557"},"address":"376817c638d2a04f475a73af37f7b51a2862d567","name":"","meta":"{}"}'
# export ACCOUNT_PASSWORD='?!#D76e@kJwh8rVY23A$5tGgnD^dP5FC'