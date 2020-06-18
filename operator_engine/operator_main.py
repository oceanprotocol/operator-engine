#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import asyncio
import threading
import logging
import time

import kopf
from k8s_utils import wait_finish_job
from resources import (
    get_sql_job_status,
    update_sql_job_status,
    create_pvc,
    create_configure_job,
    create_algorithm_job,
    update_sql_job_istimeout,
    check_sql_stop_requested,
    update_sql_job_datefinished,
    stop_specific_job,
    create_filter_job,
    create_publish_job,
)

from resources import create_configmap_workflow

logger = logging.getLogger("ocean-operator")
logger.setLevel(logging.DEBUG)

CUSTOM_JOBS_LOG_NOTICE_RATE = 10.0  # in seconds

# Configuring kopf workers
# Let's set how many workers can be running simultaneously on per-object event queue
kopf.WorkersConfig.synchronous_tasks_threadpool_limit = 20


@kopf.on.create("oceanprotocol.com", "v1alpha", "workflows")
def create_workflow(**kwargs):
    body = kwargs["body"]
    logging.info(f"Body:{body}")

    # some names that are repeatedly used throughout this function
    body_meta = body["metadata"]
    namespace = body["metadata"]["namespace"]
    job_name = body_meta["name"]
    spec_meta = body["spec"]["metadata"]  # potential key error
    stages = spec_meta["stages"]

    # check if we already have a jobid
    sqlstatus = get_sql_job_status(job_name, logging)
    logging.info(f"Got status:{sqlstatus}")
    if sqlstatus > 10:
        logging.error(f"Creating workflow failed, already in db!!!")
        return {"message": "Creating workflow failed, already in db"}

    logging.info("Start pod template")

    # Pod  template
    # kopf.info(body, reason='workflow with type {}'.format(attributes['main']['type']))
    for stage in stages:
        logger.info(f"Stage {stage['index']}:")
        logger.info(
            f"Running container {stage['algorithm']['container']['image']}"
            f":{stage['algorithm']['container']['tag']}"
        )

    update_sql_job_status(job_name, 20, logger)

    # Configmap for workflow
    logging.info("Start config map")
    create_configmap_workflow(body, logger)

    # Volume
    logging.info("Start volume creation")
    create_pvc(body, logger, stages[0]["compute"]["resources"])

    # Configure pod
    logging.info("Start conf pod")
    create_configure_job(body, logger)

    # Wait configure pod to finish
    while not wait_finish_job(namespace, f"{job_name}-configure-job"):
        logger.info("Waiting for configure pod to finish")
        time.sleep(CUSTOM_JOBS_LOG_NOTICE_RATE)

    sqlstatus = get_sql_job_status(job_name, logger)
    if sqlstatus > 30:
        return {"message": "Configure failed, job stopped"}

    # Algorithm job
    update_sql_job_status(job_name, 40, logger)
    create_algorithm_job(body, logger, stages[0]["compute"]["resources"])
    start_time = int(time.time())
    # Wait configure pod to finish
    while not wait_finish_job(namespace, f"{job_name}-algorithm-job"):
        duration = int(time.time()) - start_time
        should_stop = False
        logger.info(
            f"Waiting for algorithm pod to finish. Running for {duration} so far"
        )

        # Check if algo is taking too long
        if "maxtime" in stages[0]["compute"]:
            if isinstance(stages[0]["compute"]["maxtime"], int):
                if duration > stages[0]["compute"]["maxtime"]:
                    logger.info("Algo is taking too long. Killing IT!")
                    should_stop = True
                    update_sql_job_istimeout(job_name, logger)

        # Check if stop was requested
        if check_sql_stop_requested(job_name, logger) is True:
            logger.info("Algo received a stop request. Killing IT!")
            should_stop = True

        # Stop it if needed
        if should_stop is True:
            stop_specific_job(
                namespace, f"{job_name}-algorithm-job", logger,
            )
            break
        time.sleep(CUSTOM_JOBS_LOG_NOTICE_RATE)
    update_sql_job_datefinished(job_name, logger)

    # Filter Job
    update_sql_job_status(job_name, 50, logger)
    create_filter_job(body, logger)
    while not wait_finish_job(namespace, f"{job_name}-filter-job"):
        logger.info("Waiting for filter pod to finish")
        time.sleep(CUSTOM_JOBS_LOG_NOTICE_RATE)
    update_sql_job_datefinished(job_name, logger)

    # Publish job
    update_sql_job_status(job_name, 60, logger)
    create_publish_job(body, logger)
    while not wait_finish_job(namespace, f"{job_name}-publish-job"):
        logger.info("Waiting for publish pod to finish")
        time.sleep(CUSTOM_JOBS_LOG_NOTICE_RATE)

    update_sql_job_status(job_name, 70, logger)
    return {"message": "Creating workflow finished"}


@kopf.on.update("oceanprotocol.com", "v1alpha", "workflows")
def update_workflow(body, spec, old, new, diff, logger, **_):
    logger.warning(f"Updated {body['metadata']['name']} with diff {diff}")
    return {"message": "Updating workflow finished"}


@kopf.on.delete("oceanprotocol.com", "v1alpha", "workflows")
def delete_workflow(body, logger, **_):
    logger.warning(f"Deleted {body['metadata']['name']}")
    return {"message": "Deleted workflow finished"}


# @kopf.on.create('oceanprotocol.com', 'v1alpha', 'computejob')
# def create_compute_job(body, logger, **_):
#     logging.info(f'Creating computejob for {body["spec"]["type"]} of workflow {body["spec"]["workflow"]}')
#     create
