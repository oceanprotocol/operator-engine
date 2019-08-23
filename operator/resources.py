#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import json

import kopf
import kubernetes
import yaml

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


def create_first_job(body, logger):
    init_script = OperatorConfig.POD_CONFIGURATION_INIT_SCRIPT

    with open("templates/job-template.yaml", 'r') as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job['metadata']['labels']['app'] = body['metadata']['name']
    job['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['metadata']['labels']['did'] = body['metadata']['labels']['did']
    job['metadata']['name'] = f"{body['metadata']['name']}-job-1"
    job['metadata']['namespace'] = body['metadata']['namespace']

    job['spec']['template']['labels']['workflow'] = body['metadata']['labels']['workflow']
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


def create_second_job(body, logger):
    init_script = """#!/usr/bin/env bash -e

    touch /data/test2
    echo 'The second container was here' > /data/test2
    cat /data/test1
    sleep 100
    """
    metadata = body['spec']['metadata']
    with open("templates/job-template.yaml", 'r') as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job['metadata']['labels']['app'] = body['metadata']['name']
    job['metadata']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['metadata']['labels']['did'] = body['metadata']['labels']['did']
    job['metadata']['name'] = f"{body['metadata']['name']}-job-2"
    job['metadata']['namespace'] = body['metadata']['namespace']
    # pod['spec']['containers'][0]['command'] = ['sleep']
    # pod['spec']['containers'][0]['args'] = ['60']
    job['spec']['template']['labels']['workflow'] = body['metadata']['labels']['workflow']
    job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', init_script]
    job['spec']['template']['spec']['containers'][0]['image'] = \
        f"{metadata['service'][0]['metadata']['workflow']['stages'][0]['requirements']['container']['image']}" \
        f":{metadata['service'][0]['metadata']['workflow']['stages'][0]['requirements']['container']['tag']}"
    did_input_0 = [e for e in metadata['service'][0]['metadata']['workflow']['stages'][0]['input'] if e['index'] == 0][0]
    did_input_1 = [e for e in metadata['service'][0]['metadata']['workflow']['stages'][0]['input'] if e['index'] == 1][0]
    job['spec']['template']['spec']['containers'][0]['env'].append({'name': 'DID', 'value': did_input_0['id']})

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
