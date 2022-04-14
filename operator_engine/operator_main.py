#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import asyncio
import logging
import time
import json
import kubernetes
import kopf
from log import setup_logging
from resources import *
from threading import Thread, Lock

# from resources import create_configmap_workflow, notify_start, notify_stop, enforce_compute_resources

setup_logging()
logger = logging.getLogger("ocean-operator")

kubernetes.config.load_incluster_config()
current_namespace = open(
    "/var/run/secrets/kubernetes.io/serviceaccount/namespace"
).read()
current_jobs = 0


def update_counter(lock, by):
    global current_jobs
    with lock:
        local_counter = current_jobs
        local_counter += by
        current_jobs = local_counter


def handle_new_job(jobId, logger, lock):
    sql_body = get_sql_job_workflow(jobId, logger)
    if sql_body is None:
        logger.error(f"Sql workflow is empty for {jobId}")
        update_counter(lock, -1)
        return
    body = json.loads(sql_body)
    if not isinstance(body, dict):
        logger.error(f"Error loading dict workflow for {jobId}")
        update_counter(lock, -1)
        return
    sqlstatus = get_sql_job_status(body["metadata"]["name"], logger)
    if sqlstatus > 10:
        logger.error(f"Creating workflow failed, already in db!!!")
        update_counter(lock, -1)
        return {"message": "Creating workflow failed, already in db"}
    api = kubernetes.client.BatchV1Api()
    # make sure we overwrite any resources needed
    body["metadata"]["namespace"] = current_namespace
    body = enforce_compute_resources(body)
    # check if we already have a jobid
    logger.debug(f"Body: {body}")

    notify_start(body, logger)
    update_sql_job_status(body["metadata"]["name"], 20, logger)
    # Configmap for workflow
    logger.info(f"Job: {jobId} Creating config map")
    create_configmap_workflow(body, logger)

    # Volume
    logger.info(f"Job: {jobId} Creating volumes")
    create_all_pvc(
        body, logger, body["spec"]["metadata"]["stages"][0]["compute"]["resources"]
    )

    # Configure pod
    logger.info(f"Job: {jobId} Start conf pod")
    create_configure_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(
        current_namespace, f"{body['metadata']['name']}-configure-job", logger
    ):
        logger.debug(f"Job: {jobId} Waiting for configure pod to finish")
        time.sleep(5.0)
        # we should check for a timeout
    # Terminate configure job
    if OperatorConfig.DEBUG_NO_CLEANUP is None:
        try:
            name = body["metadata"]["name"] + "-configure-job"
            logger.info(f"Removing job {name}")
            api.delete_namespaced_job(
                namespace=current_namespace,
                name=name,
                propagation_policy="Foreground",
                grace_period_seconds=1,
            )
        except ApiException as e:
            logger.warning(f"Failed to remove configure job\n")
    sqlstatus = get_sql_job_status(body["metadata"]["name"], logger)
    # Run the algo if status == 30, else configure failed..
    if sqlstatus == 30:
        # Algorithm job
        update_sql_job_status(body["metadata"]["name"], 40, logger)
        create_algorithm_job(
            body, logger, body["spec"]["metadata"]["stages"][0]["compute"]["resources"]
        )
        starttime = int(time.time())
        # Wait configure pod to finish
        while not wait_finish_job(
            current_namespace, f"{body['metadata']['name']}-algorithm-job", logger
        ):
            duration = int(time.time()) - starttime
            shouldstop = False
            logger.debug(
                f"Job: {jobId} Waiting for algorithm pod to finish, {duration} seconds of running so far"
            )
            # Check if algo is taking too long
            if "maxtime" in body["spec"]["metadata"]["stages"][0]["compute"]:
                if isinstance(
                    body["spec"]["metadata"]["stages"][0]["compute"]["maxtime"], int
                ):
                    if (
                        duration
                        > body["spec"]["metadata"]["stages"][0]["compute"]["maxtime"]
                    ):
                        logger.info("Algo is taking too long. Kill IT!")
                        shouldstop = True
                        update_sql_job_istimeout(body["metadata"]["name"], logger)
            # Check if stop was requested
            if check_sql_stop_requested(body["metadata"]["name"], logger) is True:
                logger.info(f"Job: {jobId} Algo has a stop request. Kill IT!")
                shouldstop = True
            # Stop it if needed
            if shouldstop is True:
                stop_specific_job(
                    current_namespace,
                    body["metadata"]["name"] + "-algorithm-job",
                    logger,
                )
                break
            time.sleep(5.0)
    else:
        logger.info(f"Job: {jobId} Configure failed, algo was skipped")
    # Terminate algorithm job
    if OperatorConfig.DEBUG_NO_CLEANUP is None:
        try:
            name = body["metadata"]["name"] + "-algorithm-job"
            logger.info(f"Removing job {name}")
            api.delete_namespaced_job(
                namespace=current_namespace,
                name=name,
                propagation_policy="Foreground",
                grace_period_seconds=1,
            )
        except ApiException as e:
            logger.warning(f"Failed to remove algorithm job\n")

    # Filtering pod
    if OperatorConfig.FILTERING_CONTAINER:
        update_sql_job_status(body["metadata"]["name"], 50, logger)
        create_filter_job(
            body, logger, body["spec"]["metadata"]["stages"][0]["compute"]["resources"]
        )
        while not wait_finish_job(
            current_namespace, f"{body['metadata']['name']}-filter-job", logger
        ):
            logger.debug(f"Job: {jobId} Waiting for filtering pod to finish")
            time.sleep(5.0)
        if OperatorConfig.DEBUG_NO_CLEANUP is None:
            try:
                name = body["metadata"]["name"] + "-filter-job"
                logger.info(f"Removing job {name}")
                api.delete_namespaced_job(
                    namespace=current_namespace,
                    name=name,
                    propagation_policy="Foreground",
                    grace_period_seconds=1,
                )
            except ApiException as e:
                logger.warning(f"Failed to remove filter job\n")
    # Publish job
    # Update status only if algo was runned
    if sqlstatus == 30:
        update_sql_job_status(body["metadata"]["name"], 60, logger)
    create_publish_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(
        current_namespace, f"{body['metadata']['name']}-publish-job", logger
    ):
        logger.debug(f"Job: {jobId} Waiting for publish pod to finish")
        time.sleep(5.0)
        # we should check for a timeout
    # Terminate publish job
    if OperatorConfig.DEBUG_NO_CLEANUP is None:
        try:
            name = body["metadata"]["name"] + "-publish-job"
            logger.info(f"Removing job {name}")
            api.delete_namespaced_job(
                namespace=current_namespace,
                name=name,
                propagation_policy="Foreground",
                grace_period_seconds=1,
            )
        except ApiException as e:
            logger.warning(f"Failed to remove algorithm job\n")

    if sqlstatus == 30:
        update_sql_job_status(body["metadata"]["name"], 70, logger)
    update_sql_job_datefinished(body["metadata"]["name"], logger)
    logger.info(f"Job: {jobId} Finished")
    cleanup_job(current_namespace, jobId, logger)
    notify_stop(body, logger)
    update_counter(lock, -1)
    return {"message": "Creating workflow finished"}


def run_events_monitor():
    logger.info(f"Monitor thread started, using namespace {current_namespace}")
    account = Account.from_key(OperatorConfig.OPERATOR_PRIVATE_KEY)
    lock = Lock()
    while True:
        # we keep it here because current_jobs is changing
        announce = {
            "id": current_namespace,
            "cpuNumber": OperatorConfig.ENVIROMENT_nCPU,
            "cpuType": OperatorConfig.ENVIROMENT_cpuType,
            "gpuNumber": OperatorConfig.ENVIROMENT_nGPU,
            "gpuType": OperatorConfig.ENVIROMENT_gpuType,
            "ramGB": OperatorConfig.ENVIROMENT_ramGB,
            "diskGB": OperatorConfig.ENVIROMENT_diskGB,
            "priceMin": OperatorConfig.ENVIROMENT_priceMinute,
            "desc": OperatorConfig.ENVIROMENT_description,
            "currentJobs": current_jobs,
            "maxJobs": OperatorConfig.ENVIROMENT_maxJobs,
            "consumerAddress": account.address,
            "storageExpiry": OperatorConfig.ENVIROMENT_storageExpiry,
            "maxJobDuration": OperatorConfig.ENVIROMENT_maxJobDuration,
        }
        max_jobs_to_take = OperatorConfig.ENVIROMENT_maxJobs - current_jobs
        jobs = announce_and_get_sql_pending_jobs(logger, announce, max_jobs_to_take)
        for job in jobs:
            logger.info(f"Starting handler for job {job}")
            update_counter(lock, 1)
            thread = Thread(
                target=handle_new_job,
                args=(
                    job,
                    logger,
                    lock,
                ),
            )
            thread.start()
        time.sleep(5)
    logger.info("Closing monitor thread. Bye.")


if __name__ == "__main__":
    if OperatorConfig.OPERATOR_PRIVATE_KEY is None:
        logger.info(f"Missing OPERATOR_PRIVATE_KEY, operator-engine cannot start!")
        exit(1)
    run_events_monitor()
