#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import json

import kubernetes
import yaml
import kopf

from constants import OperatorConfig, VolumeConfig, ExternalURLs


def create_pvc(body, logger):
    size = VolumeConfig.VOLUME_SIZE
    storage_class_name = VolumeConfig.STORAGE_CLASS
    with open("templates/volume-template.yaml", 'r') as stream:
        try:
            volume = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    volume['metadata']['name'] = body['metadata']['name']
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


def create_configure_job(body, logger):
    init_script = OperatorConfig.POD_CONFIGURATION_INIT_SCRIPT

    with open("templates/job-template.yaml", 'r') as stream:
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
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'NODE',
                                                                    'value': ExternalURLs.KEEPER_URL})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'WORKFLOW',
                                                                    'value': OperatorConfig.WORKFLOW})

    # Volumes
    job['spec']['template']['spec']['volumes'] = []

    # Data volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'download', 'persistentVolumeClaim': {'claimName': body['metadata']['name']}})
    volume_mount = {'mountPath': '/data', 'name': 'download', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []
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


def create_algorithm_job(body, logger):
    metadata = body['spec']['metadata']
    attributes = metadata['service'][0]['attributes']
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

    job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', OperatorConfig.POD_ALGORITHM_INIT_SCRIPT]
    job['spec']['template']['spec']['containers'][0]['image'] = \
        f"{attributes['workflow']['stages'][0]['requirements']['container']['image']}" \
            f":{attributes['workflow']['stages'][0]['requirements']['container']['tag']}"

    # Env
    did_input_0 = [e for e in attributes['workflow']['stages'][0]['input'] if e['index'] == 0][0]
    did_input_1 = [e for e in attributes['workflow']['stages'][0]['input'] if e['index'] == 1][0]
    did_transformation = attributes['workflow']['stages'][0]['transformation']

    env_did0 = f"datafile.{did_input_0['id'].replace('did:op:', '')}.0"
    env_did1 = f"datafile.{did_input_1['id'].replace('did:op:', '')}.0"
    env_transformation = f"datafile.{did_transformation['id'].replace('did:op:', '')}.0"
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'VOLUME',
                                                                    'value': '/data'})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'DID_INPUT1',
                                                                    'value': env_did0})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'DID_INPUT2',
                                                                    'value': env_did1})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'TRANSFORMATION_DID',
                                                                    'value': env_transformation})

    # Volumes
    job['spec']['template']['spec']['volumes'] = []

    # Data volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'download', 'persistentVolumeClaim': {'claimName': body['metadata']['name']}})
    volume_mount = {'mountPath': '/data', 'name': 'download', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    # Workflow config volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'workflow', 'configMap': {'defaultMode': 420, 'name': body['metadata']['name']}})
    volume_mount = {'mountPath': '/workflow.yaml', 'name': 'workflow', 'subPath': 'workflow.yaml'}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'].append(volume_mount)

    kopf.adopt(job, owner=body)

    batch_client = kubernetes.client.BatchV1Api()
    obj = batch_client.create_namespaced_job(body['metadata']['namespace'], job)
    logger.info(f"{obj.kind} {obj.metadata.name} created")


def create_publish_job(body, logger):
    init_script = OperatorConfig.POD_PUBLISH_INIT_SCRIPT

    with open("templates/job-template.yaml", 'r') as stream:
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
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'NODE',
                                                                    'value': ExternalURLs.KEEPER_URL})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'WORKFLOW',
                                                                    'value': OperatorConfig.WORKFLOW})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_ACCESS_KEY_ID',
                                                                    'value': OperatorConfig.AWS_ACCESS_KEY_ID})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AWS_SECRET_ACCESS_KEY',
                                                                    'value': OperatorConfig.AWS_SECRET_ACCESS_KEY})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'AQUARIUS_URL',
                                                                    'value': ExternalURLs.AQUARIUS_URL})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'BRIZO_URL',
                                                                    'value': ExternalURLs.BRIZO_URL})
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'SECRET_STORE_URL',
                                                                    'value': ExternalURLs.SECRET_STORE_URL})

    # Volumes
    job['spec']['template']['spec']['volumes'] = []

    # Data volume
    job['spec']['template']['spec']['volumes'].append(
        {'name': 'download', 'persistentVolumeClaim': {'claimName': body['metadata']['name']}})
    volume_mount = {'mountPath': '/data', 'name': 'download', 'readOnly': False}
    job['spec']['template']['spec']['containers'][0]['volumeMounts'] = []
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
