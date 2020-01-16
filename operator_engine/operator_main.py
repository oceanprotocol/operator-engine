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
    #check if we already have a jobid
    sqlstatus=get_sql_job_status(body['metadata']['name'],logging)
    if sqlstatus>10:
        return {'message': "Creating workflow failed, already in db"}
    
    
    logging.info("Start pod template")
    # Pod  template
    #kopf.info(body, reason='workflow with type {}'.format(attributes['main']['type']))
    for stage in body['spec']['metadata']['stages']:
        logger.info(f"Stage {stage['index']}:")
        logger.info(
            f"Running container {stage['algorithm']['container']['image']}"
            f":{stage['algorithm']['container']['tag']}")
    
    
    update_sql_job_status(body['metadata']['name'],20,logger)
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
    
    sqlstatus=get_sql_job_status(body['metadata']['name'],logger)
    if sqlstatus>30:
        return {'message': "Configure failed, job stopped"}
    
    # Algorithm job
    update_sql_job_status(body['metadata']['name'],40,logger)
    create_algorithm_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-algorithm-job"):
        logger.info("Waiting algorithm pod to finish")
        time.sleep(10.0)
    update_sql_job_datefinished(body['metadata']['name'],logger)
    
    
    # Publish job
    update_sql_job_status(body['metadata']['name'],60,logger)
    create_publish_job(body, logger)
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-publish-job"):
        logger.info("Waiting publish pod to finish")
        time.sleep(10.0)

    update_sql_job_status(body['metadata']['name'],70,logger)
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
