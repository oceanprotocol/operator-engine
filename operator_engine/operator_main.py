#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import asyncio
import threading
import logging
import time

import kopf
from k8s_utils import *
from resources import *

from resources import create_configmap_workflow

logger = logging.getLogger('ocean-operator')
logger.setLevel(logging.DEBUG)

# Configuring kopf workers
# Let's set how many workers can be running simultaneously on per-object event queue
kopf.WorkersConfig.synchronous_tasks_threadpool_limit = 20


@kopf.on.create('oceanprotocol.com', 'v1alpha', 'workflows')
def create_workflow(**kwargs):
    body = kwargs['body']
    logging.info(f"Body:{body}")
    # attributes = body['spec']['metadata']['service'][0]['attributes']
 #   logging.info(f"Creating computejob for {body['spec']['type']} of workflow {body['spec']['workflow']}")
    # Make sure type did is provided
   # if not attributes:
   #     raise kopf.HandlerFatalError(f"Workflow error. Got {attributes}.")
    logging.info("Start pod template")
    # Pod template
    #kopf.info(body, reason='workflow with type {}'.format(attributes['main']['type']))
    for stage in body['spec']['metadata']['stages']:
        logger.info(f"Stage {stage['index']}:")
        logger.info(
            f"Running container {stage['algorithm']['container']['image']}"
            f":{stage['algorithm']['container']['tag']}")
    
    # Configmap for workflow
    logging.info("Start config map")
    create_configmap_workflow(body, logger)

    # Volume
    logging.info("Start volume creation")
    create_pvc(body, logger)

    # Configure pod
    logging.info("Start conf pod")
    create_configure_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-configure-job"):
        logger.info("Waiting configure pod to finish")
        time.sleep(10.0)

    # Algorithm job
    create_algorithm_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-algorithm-job"):
        logger.info("Waiting algorithm pod to finish")
        time.sleep(10.0)

    # Publish job
    create_publish_job(body, logger)
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-publish-job"):
        logger.info("Waiting publish pod to finish")
        time.sleep(10.0)

    return {'message': "Creating workflow finished"}


@kopf.on.update('oceanprotocol.com', 'v1alpha', 'workflows')
def update_workflow(body, spec, old, new, diff, logger, **_):
    logger.warning(f"Updated {body['metadata']['name']} with diff {diff}")
    return {'message': "Updating workflow finished"}


@kopf.on.delete('oceanprotocol.com', 'v1alpha', 'workflows')
def delete_workflow(body, logger, **_):
    logger.warning(f"Deleted {body['metadata']['name']}")
    return {'message': "Deleted workflow finished"}


# @kopf.on.create('oceanprotocol.com', 'v1alpha', 'computejob')
# def create_compute_job(body, logger, **_):
#     logging.info(f'Creating computejob for {body["spec"]["type"]} of workflow {body["spec"]["workflow"]}')
#     create
