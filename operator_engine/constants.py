#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
from os import getenv
import logging

class PGConfig:
    POSTGRES_USER=getenv("POSTGRES_USER")
    POSTGRES_PASSWORD=getenv("POSTGRES_PASSWORD")
    POSTGRES_HOST=getenv("POSTGRES_HOST")
    POSTGRES_PORT=getenv("POSTGRES_PORT")
    POSTGRES_DB=getenv("POSTGRES_DB")

class OperatorConfig:
    NETWORK = getenv('NETWORK', 'pacific')
    ACCOUNT_JSON = getenv('ACCOUNT_JSON')
    ACCOUNT_PASSWORD = getenv('ACCOUNT_PASSWORD')
    INPUTS_FOLDER = getenv('INPUTS_FOLDER', '/data/inputs')
    TRANSFORMATIONS_FOLDER = getenv('TRANSFORMATIONS_FOLDER', '/data/transformations')
    OUTPUT_FOLDER = getenv('OUTPUTS_FOLDER', '/data/outputs')
    WORKFLOW = getenv('WORKFLOW', '/workflow.json')
    envlog = getenv('LOG_LEVEL', 'DEBUG')
    if envlog =='DEBUG':
        LOG_LEVEL=logging.DEBUG
    if envlog =='INFO':
        LOG_LEVEL=logging.INFO
    if envlog =='WARNING':
        LOG_LEVEL=logging.WARNING
    if envlog =='ERROR':
        LOG_LEVEL=logging.ERROR

    # Configuration Job
    POD_CONFIGURATION_CONTAINER = getenv('POD_CONFIGURATION_CONTAINER', 'oceanprotocol/pod-configuration:latest')
    POD_CONFIGURATION_INIT_SCRIPT = """#!/usr/bin/env bash -e

    
    # tail -f /dev/null
    node src/index.js \
      --workflow "$WORKFLOW" \
      --path "$VOLUME" \
      --workflowid "$WORKFLOWID" \
      --verbose 2>&1 | tee $VOLUME/adminlogs/configure.log
    """

    # Algorithm job
    #POD_ALGORITHM_INIT_SCRIPT = """#!/usr/bin/env bash -e
    #
    #   mkdir -p $VOLUME/outputs $VOLUME/logs
    #  java \
    #   -jar $VOLUME/transformations/$TRANSFORMATION_DID/wordCount.jar\
    #   --input1 $VOLUME/inputs/$DID_INPUT1/\
    #   --input2 $VOLUME/inputs/$DID_INPUT2/\
    #   --output $VOLUME/outputs/\
    #   --logs $VOLUME/logs/ 2>&1 | tee $VOLUME/logs/algorithm.log
    #  """
    POD_ALGORITHM_INIT_SCRIPT = """#!/usr/bin/env bash -e
    
    mkdir -p $VOLUME/outputs $VOLUME/logs
    CMDLINE 2>&1 | tee $VOLUME/logs/algorithm.log
    """

    # Publish job
    POD_PUBLISH_CONTAINER = getenv('POD_PUBLISH_CONTAINER', 'oceanprotocol/pod-publishing:latest')
    POD_PUBLISH_INIT_SCRIPT = """#!/usr/bin/env bash -e
    
    
    node src/index.js \
      --workflow "$WORKFLOW" \
      --credentials "$CREDENTIALS" \
      --password "$PASSWORD" \
      --path "$VOLUME" \
      --workflowid "$WORKFLOWID" \
      --verbose 2>&1 | tee $VOLUME/adminlogs/publish.log
    """

    AWS_ACCESS_KEY_ID = getenv('AWS_ACCESS_KEY_ID',None)
    AWS_SECRET_ACCESS_KEY = getenv('AWS_SECRET_ACCESS_KEY',None)
    AWS_REGION = getenv('AWS_REGION',None)
    AWS_BUCKET_OUTPUT = getenv('AWS_BUCKET_OUTPUT',None)
    AWS_BUCKET_ADMINLOGS = getenv('AWS_BUCKET_ADMINLOGS',None)
    IPFS_OUTPUT = getenv('IPFS_OUTPUT',None)
    IPFS_ADMINLOGS = getenv('IPFS_ADMINLOGS',None)
    IPFS_OUTPUT_PREFIX = getenv('IPFS_OUTPUT_PREFIX',None)
    IPFS_ADMINLOGS_PREFIX = getenv('IPFS_ADMINLOGS_PREFIX',None)
    IPFS_EXPIRY_TIME = getenv('IPFS_EXPIRY_TIME', None)
    DEBUG_NO_CLEANUP = getenv('DEBUG_NO_CLEANUP',None)
    NOTIFY_START_URL = getenv('NOTIFY_START_URL',None)
    NOTIFY_STOP_URL = getenv('NOTIFY_STOP_URL',None)
    OPERATOR_PRIVATE_KEY = getenv('OPERATOR_PRIVATE_KEY',None)
    SERVICE_ACCOUNT = getenv('SERVICE_ACCOUNT','db-operator')

class VolumeConfig:
    VOLUME_SIZE = getenv('VOLUME_SIZE', '2Gi')
    STORAGE_CLASS = getenv('STORAGE_CLASS', 'gp2')


class ExternalURLs:
    BRIZO_URL = getenv('BRIZO_URL', 'https://brizo.commons.oceanprotocol.com')
    BRIZO_ADDRESS = getenv('BRIZO_ADDRESS', '0x008C25ED3594E094db4592F4115D5FA74C4f41eA')
    AQUARIUS_URL = getenv('AQUARIUS_URL', 'https://aquarius.commons.oceanprotocol.com')
    KEEPER_URL = getenv('KEEPER_URL', 'https://pacific.oceanprotocol.com')
    SECRET_STORE_URL = getenv('SECRET_STORE_URL', 'https://secret-store.oceanprotocol.com')


class Metadata:
    TITLE = 'Operator service'
    DESCRIPTION = 'Infrastructure Kubernetes Operator'
