#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import asyncio
import threading
import logging
import time
import json
import kubernetes
import kopf
from resources import *


from resources import create_configmap_workflow, notify_start, notify_stop

logger = logging.getLogger('ocean-operator')
#logger.setLevel(OperatorConfig.LOG_LEVEL)
logger.setLevel(logging.DEBUG)
kubernetes.config.load_incluster_config()
#current_namespace = open("/var/run/secrets/kubernetes.io/serviceaccount/namespace").read()
#start the sql thread


def handle_new_job(jobId,logger):
    sql_body=get_sql_job_workflow(jobId,logger)
    if sql_body is None:
        logging.error(f'Sql workflow is empty for {jobId}')
        return
    body = json.loads(sql_body)
    if not isinstance(body,dict):
        logging.error(f'Error loading dict workflow for {jobId}')
        return
    
    #check if we already have a jobid
    sqlstatus=get_sql_job_status(body['metadata']['name'],logging)
    if sqlstatus>10:
        logging.error(f"Creating workflow failed, already in db!!!")
        return {'message': "Creating workflow failed, already in db"}
    
    notify_start(body, logger)
    update_sql_job_status(body['metadata']['name'],20,logger)
    # Configmap for workflow
    logging.debug(f"Job: {jobId} Creating config map")
    create_configmap_workflow(body, logger)

    # Volume
    logging.debug(f"Job: {jobId} Creating volumes")
    create_all_pvc(body, logger, body['spec']['metadata']['stages'][0]['compute']['resources'])
    

    # Configure pod
    logging.error(f"Job: {jobId} Start conf pod")
    create_configure_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-configure-job",logger):
        logging.error(f"Job: {jobId} Waiting for configure pod to finish")
        time.sleep(5.0)
        #we should check for a timeout
    
    sqlstatus=get_sql_job_status(body['metadata']['name'],logger)
    # Run the algo if status == 30, else configure failed..
    if sqlstatus==30:
        # Algorithm job
        update_sql_job_status(body['metadata']['name'],40,logger)
        create_algorithm_job(body, logger, body['spec']['metadata']['stages'][0]['compute']['resources'])
        starttime=int(time.time())
        # Wait configure pod to finish
        while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-algorithm-job",logger):
            duration=int(time.time())-starttime
            shouldstop=False
            logging.debug(f"Job: {jobId} Waiting for algorithm pod to finish, {duration} seconds of running so far")
            #Check if algo is taking too long
            if 'maxtime' in body['spec']['metadata']['stages'][0]['compute']:
                if isinstance(body['spec']['metadata']['stages'][0]['compute']['maxtime'], int):
                    if duration>body['spec']['metadata']['stages'][0]['compute']['maxtime']:
                        logging.info("Algo is taking too long. Kill IT!")
                        shouldstop=True
                        update_sql_job_istimeout(body['metadata']['name'],logger)
            #Check if stop was requested
            if check_sql_stop_requested(body['metadata']['name'],logger) is True:
                logging.info(f"Job: {jobId} Algo has a stop request. Kill IT!")
                shouldstop=True
            #Stop it if needed
            if shouldstop is True:
                stop_specific_job(body['metadata']['namespace'],body['metadata']['name']+"-algorithm-job",logger)
                break
            time.sleep(5.0)
    else:
        logging.info(f"Job: {jobId} Configure failed, algo was skipped")
    
    # Publish job
    # Update status only if algo was runned
    if sqlstatus==30:
        update_sql_job_status(body['metadata']['name'],60,logger)
    create_publish_job(body, logger)
    # Wait configure pod to finish
    while not wait_finish_job(body['metadata']['namespace'], f"{body['metadata']['name']}-publish-job",logger):
        logging.error(f"Job: {jobId} Waiting for publish pod to finish")
        time.sleep(5.0)
        #we should check for a timeout


    if sqlstatus==30:
        update_sql_job_status(body['metadata']['name'],70,logger)
    update_sql_job_datefinished(body['metadata']['name'],logger)
    logging.info(f"Job: {jobId} Finished")
    cleanup_job(body['metadata']['namespace'], jobId, logger)
    notify_stop(body, logger)
    return {'message': "Creating workflow finished"}

def run_events_monitor():
    logger.info("Monitor thread started")
    while True:
        jobs=get_sql_pending_jobs(logger)
        for job in jobs:
            logger.info(f"Starting handler for job {job}")
            thread=threading.Thread(target=handle_new_job, args=(job,logger,))
            thread.start()
        time.sleep(5)
    logger.info("Closing monitor thread. Bye.")

if __name__ == '__main__':
    run_events_monitor()




