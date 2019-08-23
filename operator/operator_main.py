#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import asyncio

from k8s_utils import *
from resources import *


@kopf.on.create('oceanprotocol.com', 'v1alpha', 'workflows')
async def create_workflow(body, logger, **_):
    metadata = body['spec']['metadata']['service'][0]['metadata']

    # Make sure type did is provided
    if not metadata:
        raise kopf.HandlerFatalError(f"Workflow error. Got {metadata}.")

    # Pod template
    kopf.info(body, reason='workflow with type {}'.format(metadata['base']['type']))
    for stage in metadata['workflow']['stages']:
        logger.info(f"Stage {stage['index']} with stageType {stage['stageType']}")
        logger.info(
            f"Running container {stage['requirements']['container']['image']}"
            f":{stage['requirements']['container']['tag']}")

    # Configmap for workflow
    create_configmap_workflow(body, logger)

    # Volume
    create_pvc(body, logger)

    # Job 1
    create_first_job(body, logger)

    # Wait Job1 to finish
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-job-1"):
        logger.info("Waiting job1 to finish")
        await asyncio.sleep(10.0)

    # Job 2
    create_second_job(body, logger)

    return {'message': "Creating workflow finished"}


@kopf.on.update('oceanprotocol.com', 'v1alpha', 'workflows')
def update_workflow(body, spec, old, new, diff, logger, **_):
    logger.warning(f"Updated {body['metadata']['name']} with diff {diff}")
    return {'message': "Updating workflow finished"}


@kopf.on.delete('oceanprotocol.com', 'v1alpha', 'workflows')
def delete_workflow(body, logger, **_):
    logger.warning(f"Deleted {body['metadata']['name']}")
    return {'message': "Deleted workflow finished"}
