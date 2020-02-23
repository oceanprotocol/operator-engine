#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import json

import kubernetes
import yaml
import kopf
import psycopg2
import os

from constants import OperatorConfig, VolumeConfig, ExternalURLs


def create_pvc(body, logger, resources):
    create_pvc_input(body,logger,resources['inputVolumesize'])
    create_pvc_output(body,logger,resources['outputVolumesize'])
    create_pvc_adminlogs(body,logger,resources['adminlogsVolumesize'])

def create_pvc_output(body, logger,size):
    storage_class_name = VolumeConfig.STORAGE_CLASS
    with open("templates/volume-template.yaml", 'r') as stream:
        try:
            volume = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    volume['metadata']['name'] = body['metadata']['name']+"-output"
    volume['metadata']['namespace'] = body['metadata']['namespace']
    volume['spec']['resources']['requests']['storage'] = size
    volume['spec']['storageClassName'] = storage_class_name
    kopf.adopt(volume, owner=body)

    api = kubernetes.client.CoreV1Api()
    obj = api.create_namespaced_persistent_volume_claim(body['metadata']['namespace'], volume)
    logger.info(f"{obj.kind} {obj.metadata.name} created")

def create_pvc_input(body, logger,size):
    storage_class_name = VolumeConfig.STORAGE_CLASS
    with open("templates/volume-template.yaml", 'r') as stream:
        try:
            volume = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    volume['metadata']['name'] = body['metadata']['name']+"-input"
    volume['metadata']['namespace'] = body['metadata']['namespace']
    volume['spec']['resources']['requests']['storage'] = size
    volume['spec']['storageClassName'] = storage_class_name
    kopf.adopt(volume, owner=body)

    api = kubernetes.client.CoreV1Api()
    obj = api.create_namespaced_persistent_volume_claim(body['metadata']['namespace'], volume)
    logger.info(f"{obj.kind} {obj.metadata.name} created")

def create_pvc_adminlogs(body, logger,size):
    storage_class_name = VolumeConfig.STORAGE_CLASS
    with open("templates/volume-template.yaml", 'r') as stream:
        try:
            volume = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    volume['metadata']['name'] = body['metadata']['name']+"-adminlogs"
    volume['metadata']['namespace'] = body['metadata']['namespace']
    volume['spec']['resources']['requests']['storage'] = size
    volume['spec']['storageClassName'] = storage_class_name
    kopf.adopt(volume, owner=body)

    api = kubernetes.client.CoreV1Api()
    obj = api.create_namespaced_persistent_volume_claim(body['metadata']['namespace'], volume)
    logger.info(f"{obj.kind} {obj.metadata.name} created")


def create_configmap_workflow(body, logger):
    with open("templates/configmap-template.yaml", 'r') as stream:
        try:
            configmap = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    configmap['metadata']['name'] = body['metadata']['name']
    configmap['metadata']['namespace'] = body['metadata']['namespace']
    data_to_dump = body['spec']['metadata']
    configmap['data']['workflow.yaml'] = yaml.dump(data_to_dump)
    configmap['data']['workflow.json'] = json.dumps(data_to_dump)
    kopf.adopt(configmap, owner=body)

    api = kubernetes.client.CoreV1Api()
    obj = api.create_namespaced_config_map(body['metadata']['namespace'], configmap)
    logger.info(f"{obj.kind} {obj.metadata.name} created")

def stop_specific_job(namespace,jobname,logger):
    logger.info(f"Trying to stop {jobname} in {namespace}")
    batch_client = kubernetes.client.BatchV1Api()
    grace_period_seconds = 0 # int | The duration in seconds before the object should be deleted. Value must be non-negative integer. The value zero indicates delete immediately. If this value is nil, the default grace period for the specified type will be used. Defaults to a per object value if not specified. zero means delete immediately. (optional)
    propagation_policy = 'Foreground' # str | Whether and how garbage collection will be performed. Either this field or OrphanDependents may be set, but not both. The default policy is decided by the existing finalizer set in the metadata.finalizers and the resource-specific default policy. Acceptable values are: 'Orphan' - orphan the dependents; 'Background' - allow the garbage collector to delete the dependents in the background; 'Foreground' - a cascading policy that deletes all dependents in the foreground. (optional)
    try:
        api_response = batch_client.delete_namespaced_job(jobname, namespace,grace_period_seconds=grace_period_seconds, propagation_policy=propagation_policy)
        logger.info(f"Got {api_response}")
    except ApiException as e:
        logger.error(f'Exception when calling CustomObjectsApi->delete_namespaced_custom_object: {e}')




def create_configure_job(body, logger):
    logger.info(f"create_configure_job started")
    init_script = OperatorConfig.POD_CONFIGURATION_INIT_SCRIPT

    with open("templates/job-template-pgsql.yaml", 'r') as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job['metadata']['labels']['app'] = body['metadata']['name']
    job['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['metadata']['labels']['component'] = 'configure'
    job['metadata']['name'] = f"{body['metadata']['name']}-configure-job"
    job['metadata']['namespace'] = body['metadata']['namespace']

    job['spec']['template']['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['spec']['template']['metadata']['labels']['component'] = 'configure'

    job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', init_script]
    job['spec']['template']['spec']['containers'][0]['image'] = OperatorConfig.POD_CONFIGURATION_CONTAINER

    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'INPUTS',
                                                                    'value': OperatorConfig.INPUTS_FOLDER})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'TRANSFORMATIONS',
                                                                    'value': OperatorConfig.TRANSFORMATIONS_FOLDER})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'VOLUME',
                                                                    'value': '/data'})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'WORKFLOW',
                                                                    'value': OperatorConfig.WORKFLOW})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'WORKFLOWID',
                                                                    'value': body['metadata']['name']})

    # Volumes
    job['spec']['template']['spec']['volumes'] = []
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []
    # Input volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'input', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-input"}})
    volume_mount = {'mountPath': '/data/input', 'name': 'input', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    # Output volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'output', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-output"}})
    volume_mount = {'mountPath': '/data/', 'name': 'output', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    # Admin logs volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'adminlogs', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-adminlogs"}})
    volume_mount = {'mountPath': '/data/adminlogs', 'name': 'adminlogs', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    # Workflow config volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'workflow', 'configMap': {'defaultMode': 420, 'name': body['metadata']['name']}})
    volume_mount = {'mountPath': '/workflow.yaml', 'name': 'workflow', 'subPath': 'workflow.yaml'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    volume_mount = {'mountPath': '/workflow.json', 'name': 'workflow', 'subPath': 'workflow.json'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    logger.info(f"Job: {job}")

    kopf.adopt(job, owner=body)

    batch_client = kubernetes.client.BatchV1Api()
    obj = batch_client.create_namespaced_job(body['metadata']['namespace'], job)
    logger.info(f"{obj.kind} {obj.metadata.name} created")


def create_algorithm_job(body, logger, resources):
    metadata = body['spec']['metadata']
    logger.info(f"create_algorithm_job:{metadata}")
    # attributes = metadata['service'][0]['attributes']
    with open("templates/job-template.yaml", 'r') as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job['metadata']['labels']['app'] = body['metadata']['name']
    job['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['metadata']['labels']['component'] = 'algorithm'

    job['metadata']['name'] = f"{body['metadata']['name']}-algorithm-job"
    job['metadata']['namespace'] = body['metadata']['namespace']

    job['spec']['template']['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['spec']['template']['metadata']['labels']['component'] = 'algorithm'

    #job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', OperatorConfig.POD_ALGORITHM_INIT_SCRIPT]
    command=OperatorConfig.POD_ALGORITHM_INIT_SCRIPT
    fullcommand=command.replace("CMDLINE",metadata['stages'][0]['algorithm']['container']['entrypoint'].replace('$ALGO', OperatorConfig.TRANSFORMATIONS_FOLDER+"/algorithm"))
    job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', fullcommand]
    #job['spec']['template']['spec']['containers'][0]['command'] = metadata['stages'][0]['algorithm']['container']['entrypoint'].replace('$ALGO', OperatorConfig.TRANSFORMATIONS_FOLDER+"/algorithm")
    job['spec']['template']['spec']['containers'][0]['image'] = \
        f"{metadata['stages'][0]['algorithm']['container']['image']}" \
            f":{metadata['stages'][0]['algorithm']['container']['tag']}"

    # Env
    #did_input_0 = [e for e in metadata['stages'][0]['input'] if e['index'] == 0][0]
    #did_input_1 = [e for e in metadata['stages'][0]['input'] if e['index'] == 1][0]
    did_transformation = metadata['stages'][0]['algorithm']

    #env_did0 = f"datafile.{did_input_0['id'].replace('did:op:', '')}.0"
    #env_did1 = f"datafile.{did_input_1['id'].replace('did:op:', '')}.0"
    env_transformation = f"datafile.{did_transformation['id'].replace('did:op:', '')}.0"
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'VOLUME',
                                                                    'value': '/data'})
    #job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'DID_INPUT1',
    #                                                                'value': env_did0})
    #job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'DID_INPUT2',
    #                                                                'value': env_did1})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'TRANSFORMATION_DID',
                                                                    'value': env_transformation})

    # Resources  (CPU & Memory)
    job['spec']['template']['spec']['containers'][0]['resources'] = dict()
    job['spec']['template']['spec']['containers'][0]['resources']['requests'] = dict()
    job['spec']['template']['spec']['containers'][0]['resources']['requests']['memory'] = resources['requests_memory']
    job['spec']['template']['spec']['containers'][0]['resources']['requests']['cpu'] = resources['requests_cpu']
    job['spec']['template']['spec']['containers'][0]['resources']['limits'] = dict()
    job['spec']['template']['spec']['containers'][0]['resources']['limits']['memory'] = resources['limits_memory']
    job['spec']['template']['spec']['containers'][0]['resources']['limits']['cpu'] = resources['limits_cpu']
    
    # Volumes
    job['spec']['template']['spec']['volumes'] = []
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []

    # Output volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'output', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-output"}})
    volume_mount = {'mountPath': '/data/', 'name': 'output', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    # Input volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'input', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-input"}})
    volume_mount = {'mountPath': '/data/input', 'name': 'input', 'readOnly': True}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    # Admin logs volume -  Do not mount it here
    
    # Workflow config volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'workflow', 'configMap': {'defaultMode': 420, 'name': body['metadata']['name']}})
    volume_mount = {'mountPath': '/workflow.yaml', 'name': 'workflow', 'subPath': 'workflow.yaml'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    logger.info(f"in create_algorithm_job starting Job: {job}")

    kopf.adopt(job, owner=body)

    batch_client = kubernetes.client.BatchV1Api()
    obj = batch_client.create_namespaced_job(body['metadata']['namespace'], job)
    logger.info(f"{obj.kind} {obj.metadata.name} created")


def create_publish_job(body, logger):
    init_script = OperatorConfig.POD_PUBLISH_INIT_SCRIPT

    with open("templates/job-template-pgsql.yaml", 'r') as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job['metadata']['labels']['app'] = body['metadata']['name']
    job['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['metadata']['labels']['component'] = 'publish'

    job['metadata']['name'] = f"{body['metadata']['name']}-publish-job"
    job['metadata']['namespace'] = body['metadata']['namespace']

    job['spec']['template']['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['spec']['template']['metadata']['labels']['component'] = 'publish'

    job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', init_script]
    job['spec']['template']['spec']['containers'][0]['image'] = OperatorConfig.POD_PUBLISH_CONTAINER

    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'CREDENTIALS',
                                                                    'value': OperatorConfig.ACCOUNT_JSON})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'PASSWORD',
                                                                    'value': OperatorConfig.ACCOUNT_PASSWORD})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'INPUTS',
                                                                    'value': OperatorConfig.INPUTS_FOLDER})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'TRANSFORMATIONS',
                                                                    'value': OperatorConfig.TRANSFORMATIONS_FOLDER})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'VOLUME',
                                                                    'value': '/data'})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'WORKFLOW',
                                                                    'value': OperatorConfig.WORKFLOW})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_ACCESS_KEY_ID',
                                                                    'value': OperatorConfig.AWS_ACCESS_KEY_ID})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_SECRET_ACCESS_KEY',
                                                                    'value': OperatorConfig.AWS_SECRET_ACCESS_KEY})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_REGION',
                                                                    'value': OperatorConfig.AWS_REGION})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_BUCKET_OUTPUT',
                                                                    'value': OperatorConfig.AWS_BUCKET_OUTPUT})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_BUCKET_ADMINLOGS',
                                                                    'value': OperatorConfig.AWS_BUCKET_ADMINLOGS})                                                                                                                                    
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'WORKFLOWID',
                                                                    'value': body['metadata']['name']})
    # Volumes
    job['spec']['template']['spec']['volumes'] = []
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []

    # Output volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'output', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-output"}})
    volume_mount = {'mountPath': '/data/', 'name': 'output', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    # Input volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'input', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-input"}})
    volume_mount = {'mountPath': '/data/input', 'name': 'input', 'readOnly': True}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    # Admin logs volume 
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'adminlogs', 'persistentVolumeClaim': {'claimName': body['metadata']['name']+"-adminlogs"}})
    volume_mount = {'mountPath': '/data/adminlogs', 'name': 'adminlogs', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    

    # Workflow config volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'workflow', 'configMap': {'defaultMode': 420, 'name': body['metadata']['name']}})
    volume_mount = {'mountPath': '/workflow.yaml', 'name': 'workflow', 'subPath': 'workflow.yaml'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    volume_mount = {'mountPath': '/workflow.json', 'name': 'workflow', 'subPath': 'workflow.json'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    kopf.adopt(job, owner=body)

    batch_client = kubernetes.client.BatchV1Api()
    obj = batch_client.create_namespaced_job(body['metadata']['namespace'], job)
    logger.info(f"{obj.kind} {obj.metadata.name} created")


def create_job_from_computejob(computejob_body, logger):
    logger.info("####################create_job_from_computejob###################")
    namespace = computejob_body['metadata']['namespace']
    jobtype = computejob_body['spec']['type']
    # We need to get the workflow body
    custom_object_client = kubernetes.client.CustomObjectsApi()
    workflow_body = custom_object_client.get_namespaced_custom_object(group='oceanprotocol.com', version='v1alpha',
                                                                      namespace=namespace, plural='computejobs',
                                                                      name=computejob_body['spec']['workflow'])
    with open("templates/job-template.yaml", 'r') as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job['metadata']['labels']['app'] = workflow_body['metadata']['name']
    job['metadata']['labels']['workflow'] = workflow_body['metadata']['labels']['workflow']
    job['metadata']['labels']['component'] = 'configure'
    job['metadata']['name'] = f"{workflow_body['metadata']['name']}-{jobtype}-job"
    job['metadata']['namespace'] = workflow_body['metadata']['namespace']

    job['spec']['template']['metadata']['labels']['workflow'] = workflow_body['metadata']['labels']['workflow']
    job['spec']['template']['metadata']['labels']['component'] = 'configure'

    # Volumes
    job['spec']['template']['spec']['volumes'] = []

    # Data volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'download', 'persistentVolumeClaim': {'claimName': workflow_body['metadata']['name']}})
    volume_mount = {'mountPath': '/data', 'name': 'download', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    # Workflow config volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'workflow', 'configMap': {'defaultMode': 420, 'name': workflow_body['metadata']['name']}})
    volume_mount = {'mountPath': '/workflow.yaml', 'name': 'workflow', 'subPath': 'workflow.yaml'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)
    volume_mount = {'mountPath': '/workflow.json', 'name': 'workflow', 'subPath': 'workflow.json'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    job['spec']['template']['metadata']['labels']['component'] = jobtype

    envs = []

    if jobtype == 'configure':
        init_script = OperatorConfig.POD_CONFIGURATION_INIT_SCRIPT
        image = OperatorConfig.POD_CONFIGURATION_CONTAINER

        envs.append({'name': 'CREDENTIALS', 'value': OperatorConfig.ACCOUNT_JSON})
        envs.append({'name': 'PASSWORD', 'value': OperatorConfig.ACCOUNT_PASSWORD})
        envs.append({'name': 'INPUTS', 'value': OperatorConfig.INPUTS_FOLDER})
        envs.append({'name': 'TRANSFORMATIONS', 'value': OperatorConfig.TRANSFORMATIONS_FOLDER})
        envs.append({'name': 'VOLUME', 'value': '/data'})
        envs.append({'name': 'NODE', 'value': ExternalURLs.KEEPER_URL})
        envs.append({'name': 'WORKFLOW', 'value': OperatorConfig.WORKFLOW})
        envs.append({'name': 'BRIZO_ADDRESS', 'value': ExternalURLs.BRIZO_ADDRESS})
        envs.append({'name': 'BRIZO_URL', 'value': ExternalURLs.BRIZO_URL})
        envs.append({'name': 'AQUARIUS_URL', 'value': ExternalURLs.AQUARIUS_URL})
        envs.append({'name': 'SECRET_STORE_URL', 'value': ExternalURLs.SECRET_STORE_URL})


    elif jobtype == 'algorithm':
        init_script = OperatorConfig.POD_ALGORITHM_INIT_SCRIPT
        attributes = workflow_body['spec']['metadata']['service'][0]['attributes']
        image = \
            f"{attributes['workflow']['stages'][0]['requirements']['container']['image']}" \
            f":{attributes['workflow']['stages'][0]['requirements']['container']['tag']}"

        # Env
        did_input_0 = [e for e in attributes['workflow']['stages'][0]['input'] if e['index'] == 0][0]
        did_input_1 = [e for e in attributes['workflow']['stages'][0]['input'] if e['index'] == 1][0]
        did_transformation = attributes['workflow']['stages'][0]['transformation']

        env_did0 = f"datafile.{did_input_0['id'].replace('did:op:', '')}.0"
        env_did1 = f"datafile.{did_input_1['id'].replace('did:op:', '')}.0"
        env_transformation = f"datafile.{did_transformation['id'].replace('did:op:', '')}.0"
        envs.append({'name': 'VOLUME', 'value': '/data'})
        envs.append({'name': 'DID_INPUT1', 'value': env_did0})
        envs.append({'name': 'DID_INPUT2', 'value': env_did1})
        envs.append({'name': 'TRANSFORMATION_DID', 'value': env_transformation})

    elif jobtype == 'publish':
        init_script = OperatorConfig.POD_PUBLISH_INIT_SCRIPT
        image = OperatorConfig.POD_PUBLISH_CONTAINER

        envs.append({'name': 'CREDENTIALS', 'value': OperatorConfig.ACCOUNT_JSON})
        envs.append({'name': 'PASSWORD', 'value': OperatorConfig.ACCOUNT_PASSWORD})
        envs.append({'name': 'INPUTS', 'value': OperatorConfig.INPUTS_FOLDER})
        envs.append({'name': 'TRANSFORMATIONS', 'value': OperatorConfig.TRANSFORMATIONS_FOLDER})
        envs.append({'name': 'VOLUME', 'value': '/data'})
        envs.append({'name': 'NODE', 'value': ExternalURLs.KEEPER_URL})
        envs.append({'name': 'WORKFLOW', 'value': OperatorConfig.WORKFLOW})
        envs.append({'name': 'AWS_ACCESS_KEY_ID', 'value': OperatorConfig.AWS_ACCESS_KEY_ID})
        envs.append({'name': 'AWS_SECRET_ACCESS_KEY', 'value': OperatorConfig.AWS_SECRET_ACCESS_KEY})
        envs.append({'name': 'AQUARIUS_URL', 'value': ExternalURLs.AQUARIUS_URL})
        envs.append({'name': 'BRIZO_URL', 'value': ExternalURLs.BRIZO_URL})
        envs.append({'name': 'SECRET_STORE_URL', 'value': ExternalURLs.SECRET_STORE_URL})

    else:
        logger.error(f'ComputeJob type {jobtype} not recognized')
        return -1

    job['spec']['template']['spec']['containers'][0]['env'] = envs
    job['spec']['template']['spec']['containers'][0]['image'] = image
    job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', init_script]

    # Run job
    kopf.adopt(job, owner=computejob_body)

    batch_client = kubernetes.client.BatchV1Api()
    obj = batch_client.create_namespaced_job(namespace, job)
    logger.info(f"{obj.kind} {obj.metadata.name} created")




def update_sql_job_datefinished(jobId,logger):
    logger.error(f"Start update_sql_job_datefinished for {jobId}")
    connection = getpgconn()
    try:
        cursor = connection.cursor()
        postgres_update_query = """ UPDATE jobs SET dateFinished=NOW() WHERE workflowId=%s"""
        record_to_update = (jobId,)
        logger.info(f'Got select_query: {postgres_update_query}')
        logger.info(f'Got params: {record_to_update}')
        cursor.execute(postgres_update_query, record_to_update)
        connection.commit()
    except (Exception, psycopg2.Error) as error :
            logger.error("Error in  update_sql_job_datefinished PostgreSQL:"+str(error))
    finally:
            #closing database connection.
            if(connection):
                cursor.close()
                connection.close()


def update_sql_job_istimeout(jobId,logger):
    logger.error(f"Start update_sql_job_istimeout for {jobId}")
    connection = getpgconn()
    try:
        cursor = connection.cursor()
        postgres_update_query = """ UPDATE jobs SET stopreq=2 WHERE workflowId=%s"""
        record_to_update = (jobId,)
        logger.info(f'Got select_query: {postgres_update_query}')
        logger.info(f'Got params: {record_to_update}')
        cursor.execute(postgres_update_query, record_to_update)
        connection.commit()
    except (Exception, psycopg2.Error) as error :
            logger.error("Error in  update_sql_job_istimeout PostgreSQL:"+str(error))
    finally:
            #closing database connection.
            if(connection):
                cursor.close()
                connection.close()


def update_sql_job_status(jobId,status,logger):
    logger.error(f"Start update_sql_job_status for {jobId} : {status}")
    connection = getpgconn()
    try:
        switcher = {
            10: "Job started",
            20: "Configuring volumes",
            40: "Running algorithm ",
            50: "Filtering results",
            60: "Publishing results",
            70: "Job finished"
        }
        statusText=switcher.get(status, "Unknown status" )
        cursor = connection.cursor()
        postgres_update_query = """ UPDATE jobs SET status=%s,statusText=%s WHERE workflowId=%s"""
        record_to_update = (status,statusText,jobId)
        logger.info(f'Got select_query: {postgres_update_query}')
        logger.info(f'Got params: {record_to_update}')
        cursor.execute(postgres_update_query, record_to_update)
        connection.commit()
    except (Exception, psycopg2.Error) as error :
            logger.error("Error in update_sql_job_status PostgreSQL:"+str(error))
    finally:
            #closing database connection.
            if(connection):
                cursor.close()
                connection.close()



def get_sql_job_status(jobId,logger):
  logger.error(f"Start get_sql_job_status for {jobId}")
  connection = getpgconn()
  try:
      cursor = connection.cursor()
      params=dict()
      select_query="SELECT status FROM jobs WHERE workflowId=%(jobId)s LIMIT 1"
      params['jobId']=jobId
      logger.info(f'Got select_query: {select_query}')
      logger.info(f'Got params: {params}')
      cursor.execute(select_query, params)
      returnstatus=-1
      while True:
        row = cursor.fetchone()
        if row == None:
            break
        returnstatus=row[0]
  except (Exception, psycopg2.Error) as error :
        logger.error(f'Got PG error in get_sql_job_status: {error}')
  finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
  logger.error(f'get_sql_job_status goes back with  {returnstatus}')
  return returnstatus

def check_sql_stop_requested(jobId,logger):
  connection = getpgconn()
  returnstatus=False
  try:
      cursor = connection.cursor()
      params=dict()
      select_query="SELECT stopreq FROM jobs WHERE workflowId=%(jobId)s LIMIT 1"
      params['jobId']=jobId
      cursor.execute(select_query, params)
      while True:
        row = cursor.fetchone()
        if row == None:
            break
        if row[0]==1:
            returnstatus=True
  except (Exception, psycopg2.Error) as error :
        logger.error(f'Got PG error in check_sql_stop_requested: {error}')
  finally:
    #closing database connection.
        if(connection):
            cursor.close()
            connection.close()
  return returnstatus

def getpgconn():
    try:
        connection = psycopg2.connect(user = os.getenv("POSTGRES_USER"),
                                  password = os.getenv("POSTGRES_PASSWORD"),
                                  host = os.getenv("POSTGRES_HOST"),
                                  port = os.getenv("POSTGRES_PORT"),
                                  database = os.getenv("POSTGRES_DB"))
        connection.set_client_encoding('LATIN9')
        return connection
    except (Exception, psycopg2.Error) as error :
        logging.error(f'New PG connect error: {error}')
        return None