#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
from os import getenv


class OperatorConfig:
    NETWORK = getenv('NETWORK', 'pacific')
    ACCOUNT_JSON = getenv('ACCOUNT_JSON')
    ACCOUNT_PASSWORD = getenv('ACCOUNT_PASSWORD')
    INPUTS_FOLDER = getenv('INPUTS_FOLDER', '/data/inputs')
    TRANSFORMATIONS_FOLDER = getenv('TRANSFORMATIONS_FOLDER', '/data/transformations')
    TRANSFORMATIONS_FOLDER = getenv('OUTPUTS_FOLDER', '/data/output')
    WORKFLOW = getenv('WORKFLOW', '/workflow.json')

    # Configuration Job
    POD_CONFIGURATION_CONTAINER = getenv('POD_CONFIGURATION_CONTAINER', 'pedrogp/ocean-pod-configuration:latest')
    POD_CONFIGURATION_INIT_SCRIPT = """#!/usr/bin/env bash -e

    mkdir -p $VOLUME/outputs $VOLUME/logs
    # tail -f /dev/null
    node src/index.js \
      --workflow "$WORKFLOW" \
      --node "$NODE" \
      --credentials "$CREDENTIALS" \
      --password "$PASSWORD" \
      --path "$VOLUME" \
      --verbose 2>&1 | tee $VOLUME/logs/configure.log
    """

    # Algorithm job
    POD_ALGORITHM_INIT_SCRIPT = """#!/usr/bin/env bash -e

    mkdir -p $VOLUME/outputs $VOLUME/logs
    java \
     -jar $VOLUME/transformations/$TRANSFORMATION_DID/wordCount.jar\
     --input1 $VOLUME/inputs/$DID_INPUT1/\
     --input2 $VOLUME/inputs/$DID_INPUT2/\
     --output $VOLUME/outputs/\
     --logs $VOLUME/logs/ 2>&1 | tee $VOLUME/logs/algorithm.log
    """

    # Publish job
    POD_PUBLISH_CONTAINER = getenv('POD_CONFIGURATION_CONTAINER', 'pedrogp/ocean-pod-publishing:latest')
    POD_PUBLISH_INIT_SCRIPT = """#!/usr/bin/env bash -e
    
    mkdir -p $VOLUME/outputs $VOLUME/logs
    node src/index.js \
      --workflow "$WORKFLOW" \
      --node "$NODE" \
      --credentials "$CREDENTIALS" \
      --password "$PASSWORD" \
      --path "$VOLUME" \
      --verbose 2>&1 | tee $VOLUME/logs/publish.log
    """

    AWS_ACCESS_KEY_ID = getenv('AWS_ACCESS_KEY_ID')
    AWS_SECRET_ACCESS_KEY = getenv('AWS_SECRET_ACCESS_KEY')


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
