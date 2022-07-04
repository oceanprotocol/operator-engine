#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import json
import time
import kubernetes
import yaml
import kopf
import psycopg2
import os
import requests
import uuid
from web3 import Web3
from eth_account import Account
from kubernetes.client.rest import ApiException
from constants import OperatorConfig, VolumeConfig, PGConfig


def create_all_pvc(body, logger, resources):
    create_pvc_data(body, logger, resources["inputVolumesize"])
    create_pvc_adminlogs(body, logger, resources["adminlogsVolumesize"])


def create_pvc_data(body, logger, size):
    storage_class_name = VolumeConfig.STORAGE_CLASS
    with open("templates/volume-template.yaml", "r") as stream:
        try:
            volume = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    volume["metadata"]["name"] = body["metadata"]["name"] + "-data"
    volume["metadata"]["namespace"] = body["metadata"]["namespace"]
    volume["spec"]["resources"]["requests"]["storage"] = size
    volume["spec"]["storageClassName"] = storage_class_name
    create_pvc(body, logger, volume)


def create_pvc_adminlogs(body, logger, size):
    storage_class_name = VolumeConfig.STORAGE_CLASS
    with open("templates/volume-template.yaml", "r") as stream:
        try:
            volume = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)
    volume["metadata"]["name"] = body["metadata"]["name"] + "-adminlogs"
    volume["metadata"]["namespace"] = body["metadata"]["namespace"]
    volume["spec"]["resources"]["requests"]["storage"] = size
    volume["spec"]["storageClassName"] = storage_class_name
    create_pvc(body, logger, volume)


def create_pvc(body, logger, volume):
    try:
        logger.info(f"Creating volume {volume}")
        api = kubernetes.client.CoreV1Api()
        obj = api.create_namespaced_persistent_volume_claim(
            body["metadata"]["namespace"], volume
        )
        logger.info(f"{obj.kind} {obj.metadata.name} created")
    except ApiException as e:
        logger.error(
            f"Exception when calling CustomObjectsApi->create_namespaced_persistent_volume_claim: {e}"
        )


def create_configmap_workflow(body, logger):
    with open("templates/configmap-template.yaml", "r") as stream:
        try:
            configmap = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    configmap["metadata"]["name"] = body["metadata"]["name"]
    configmap["metadata"]["namespace"] = body["metadata"]["namespace"]
    data_to_dump = body["spec"]["metadata"]
    configmap["data"]["workflow.yaml"] = yaml.dump(data_to_dump)
    configmap["data"]["workflow.json"] = json.dumps(data_to_dump)
    # kopf.adopt(configmap, owner=body)
    try:
        logger.debug(f"Creating configmap {configmap}")
        api = kubernetes.client.CoreV1Api()
        obj = api.create_namespaced_config_map(body["metadata"]["namespace"], configmap)
        logger.info(f"{obj.kind} {obj.metadata.name} created")
    except ApiException as e:
        logger.error(
            f"Exception when calling CustomObjectsApi->create_namespaced_config_map: {e}"
        )


def stop_specific_job(namespace, jobname, logger):
    logger.info(f"Trying to stop {jobname} in {namespace}")
    batch_client = kubernetes.client.BatchV1Api()
    # int | The duration in seconds before the object should be deleted. Value must be non-negative integer. The value zero indicates delete immediately. If this value is nil, the default grace period for the specified type will be used. Defaults to a per object value if not specified. zero means delete immediately. (optional)
    grace_period_seconds = 0
    # str | Whether and how garbage collection will be performed. Either this field or OrphanDependents may be set, but not both. The default policy is decided by the existing finalizer set in the metadata.finalizers and the resource-specific default policy. Acceptable values are: 'Orphan' - orphan the dependents; 'Background' - allow the garbage collector to delete the dependents in the background; 'Foreground' - a cascading policy that deletes all dependents in the foreground. (optional)
    propagation_policy = "Foreground"
    try:
        api_response = batch_client.delete_namespaced_job(
            jobname,
            namespace,
            grace_period_seconds=grace_period_seconds,
            propagation_policy=propagation_policy,
        )
        logger.info(f"Got {api_response}")
    except ApiException as e:
        logger.error(
            f"Exception when calling CustomObjectsApi->delete_namespaced_custom_object: {e}"
        )


def create_configure_job(body, logger):
    logger.debug(f"create_configure_job started")
    init_script = OperatorConfig.POD_CONFIGURATION_INIT_SCRIPT

    with open("templates/configure-job-template.yaml", "r") as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job["metadata"]["labels"]["app"] = body["metadata"]["name"]
    job["metadata"]["labels"]["workflow"] = body["metadata"]["labels"]["workflow"]
    job["metadata"]["labels"]["component"] = "configure"
    job["metadata"]["name"] = f"{body['metadata']['name']}-configure-job"
    job["metadata"]["namespace"] = body["metadata"]["namespace"]

    job["spec"]["template"]["metadata"]["labels"]["workflow"] = body["metadata"][
        "labels"
    ]["workflow"]
    job["spec"]["template"]["metadata"]["labels"]["component"] = "configure"

    job["spec"]["template"]["spec"]["containers"][0]["command"] = [
        "sh",
        "-c",
        init_script,
    ]
    job["spec"]["template"]["spec"]["containers"][0][
        "image"
    ] = OperatorConfig.POD_CONFIGURATION_CONTAINER

    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "INPUTS", "value": OperatorConfig.INPUTS_FOLDER}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "TRANSFORMATIONS", "value": OperatorConfig.TRANSFORMATIONS_FOLDER}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "VOLUME", "value": "/data"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "WORKFLOW", "value": OperatorConfig.WORKFLOW}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "WORKFLOWID", "value": body["metadata"]["name"]}
    )

    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_USER", "value": PGConfig.POSTGRES_USER}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_PASSWORD", "value": PGConfig.POSTGRES_PASSWORD}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_HOST", "value": PGConfig.POSTGRES_HOST}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_PORT", "value": PGConfig.POSTGRES_PORT}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_DB", "value": PGConfig.POSTGRES_DB}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "PRIVATE_KEY", "value": OperatorConfig.OPERATOR_PRIVATE_KEY}
    )

    # Volumes
    job["spec"]["template"]["spec"]["volumes"] = []
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"] = []
    # Data volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "data",
            "persistentVolumeClaim": {"claimName": body["metadata"]["name"] + "-data"},
        }
    )
    volume_mount = {"mountPath": "/data/", "name": "data", "readOnly": False}
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    # Admin logs volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "adminlogs",
            "persistentVolumeClaim": {
                "claimName": body["metadata"]["name"] + "-adminlogs"
            },
        }
    )
    volume_mount = {
        "mountPath": "/data/adminlogs",
        "name": "adminlogs",
        "readOnly": False,
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    # set the account
    job["spec"]["template"]["spec"]["serviceAccount"] = OperatorConfig.SERVICE_ACCOUNT
    job["spec"]["template"]["spec"][
        "serviceAccountName"
    ] = OperatorConfig.SERVICE_ACCOUNT
    # Workflow config volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "workflow",
            "configMap": {"defaultMode": 420, "name": body["metadata"]["name"]},
        }
    )
    volume_mount = {
        "mountPath": "/workflow.yaml",
        "name": "workflow",
        "subPath": "workflow.yaml",
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    volume_mount = {
        "mountPath": "/workflow.json",
        "name": "workflow",
        "subPath": "workflow.json",
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    job = jobs_common_params(job, logger)
    create_job(logger, body, job)


def create_algorithm_job(body, logger, resources):
    metadata = body["spec"]["metadata"]
    logger.debug(f"create_algorithm_job:{metadata}")
    # attributes = metadata['service'][0]['attributes']
    with open("templates/algo-job-template.yaml", "r") as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job["metadata"]["labels"]["app"] = body["metadata"]["name"]
    job["metadata"]["labels"]["workflow"] = body["metadata"]["labels"]["workflow"]
    job["metadata"]["labels"]["component"] = "algorithm"

    job["metadata"]["name"] = f"{body['metadata']['name']}-algorithm-job"
    job["metadata"]["namespace"] = body["metadata"]["namespace"]

    job["spec"]["template"]["metadata"]["labels"]["workflow"] = body["metadata"][
        "labels"
    ]["workflow"]
    job["spec"]["template"]["metadata"]["labels"]["component"] = "algorithm"

    # job['spec']['template']['spec']['containers'][0]['command'] = ['sh', '-c', OperatorConfig.POD_ALGORITHM_INIT_SCRIPT]
    command = OperatorConfig.POD_ALGORITHM_INIT_SCRIPT
    fullcommand = command.replace(
        "CMDLINE",
        metadata["stages"][0]["algorithm"]["container"]["entrypoint"].replace(
            "$ALGO", OperatorConfig.TRANSFORMATIONS_FOLDER + "/algorithm"
        ),
    )
    job["spec"]["template"]["spec"]["containers"][0]["command"] = [
        "sh",
        "-c",
        fullcommand,
    ]
    # job['spec']['template']['spec']['containers'][0]['command'] = metadata['stages'][0]['algorithm']['container']['entrypoint'].replace('$ALGO', OperatorConfig.TRANSFORMATIONS_FOLDER+"/algorithm")
    if "checksum" in metadata["stages"][0]["algorithm"]["container"] and metadata[
        "stages"
    ][0]["algorithm"]["container"]["checksum"].startswith("sha256:"):
        job["spec"]["template"]["spec"]["containers"][0]["image"] = (
            f"{metadata['stages'][0]['algorithm']['container']['image']}"
            f"@{metadata['stages'][0]['algorithm']['container']['checksum']}"
        )
    else:
        job["spec"]["template"]["spec"]["containers"][0]["image"] = (
            f"{metadata['stages'][0]['algorithm']['container']['image']}"
            f":{metadata['stages'][0]['algorithm']['container']['tag']}"
        )

    # Env
    dids = list()
    for inputs in metadata["stages"][0]["input"]:
        logger.debug(f"{inputs} as inputs")
        id = inputs["id"]
        id = id.replace("did:op:", "")
        dids.append(id)
    dids = json.dumps(dids)
    did_transformation = metadata["stages"][0]["algorithm"]
    env_transformation = did_transformation["id"].replace("did:op:", "")
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "DIDS", "value": dids}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "TRANSFORMATION_DID", "value": env_transformation}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "VOLUME", "value": "/data"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "LOGS", "value": "/data/logs"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "INPUTS", "value": "/data/inputs"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "OUTPUTS", "value": "/data/outputs"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "secret", "value": body["metadata"]["secret"]}
    )
    # Resources  (CPU & Memory)
    job["spec"]["template"]["spec"]["containers"][0]["resources"] = dict()
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"] = dict()
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"][
        "memory"
    ] = resources["requests_memory"]
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["requests"][
        "cpu"
    ] = resources["requests_cpu"]
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"] = dict()
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"][
        "memory"
    ] = resources["limits_memory"]
    job["spec"]["template"]["spec"]["containers"][0]["resources"]["limits"][
        "cpu"
    ] = resources["limits_cpu"]

    # Volumes
    job["spec"]["template"]["spec"]["volumes"] = []
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"] = []

    # Output volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "data",
            "persistentVolumeClaim": {"claimName": body["metadata"]["name"] + "-data"},
        }
    )
    volume_mount = {"mountPath": "/data/", "name": "data", "readOnly": False}
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    # Admin logs volume -  Do not mount it here

    # set the account
    job["spec"]["template"]["spec"]["serviceAccount"] = OperatorConfig.SERVICE_ACCOUNT
    job["spec"]["template"]["spec"][
        "serviceAccountName"
    ] = OperatorConfig.SERVICE_ACCOUNT
    # Workflow config volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "workflow",
            "configMap": {"defaultMode": 420, "name": body["metadata"]["name"]},
        }
    )
    volume_mount = {
        "mountPath": "/workflow.yaml",
        "name": "workflow",
        "subPath": "workflow.yaml",
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    job = jobs_common_params(job, logger)
    create_job(logger, body, job)


def create_filter_job(body, logger, resources):
    metadata = body["spec"]["metadata"]
    logger.info(f"create_filter_job:{metadata}")
    # attributes = metadata['service'][0]['attributes']
    with open("templates/filter-job-template.yaml", "r") as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job["metadata"]["labels"]["app"] = body["metadata"]["name"]
    job["metadata"]["labels"]["workflow"] = body["metadata"]["labels"]["workflow"]
    job["metadata"]["labels"]["component"] = "filter"

    job["metadata"]["name"] = f"{body['metadata']['name']}-filter-job"
    job["metadata"]["namespace"] = body["metadata"]["namespace"]

    job["spec"]["template"]["metadata"]["labels"]["workflow"] = body["metadata"][
        "labels"
    ]["workflow"]
    job["spec"]["template"]["metadata"]["labels"]["component"] = "filter"

    job["spec"]["template"]["spec"]["containers"][0][
        "image"
    ] = OperatorConfig.FILTERING_CONTAINER

    # Env
    dids = list()
    for inputs in metadata["stages"][0]["input"]:
        logger.debug(f"{inputs} as inputs")
        id = inputs["id"]
        id = id.replace("did:op:", "")
        dids.append(id)
    dids = json.dumps(dids)
    did_transformation = metadata["stages"][0]["algorithm"]
    env_transformation = did_transformation["id"].replace("did:op:", "")
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "DIDS", "value": dids}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "TRANSFORMATION_DID", "value": env_transformation}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "VOLUME", "value": "/data"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "LOGS", "value": "/data/logs"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "INPUTS", "value": "/data/inputs"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "OUTPUTS", "value": "/data/outputs"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "secret", "value": body["metadata"]["secret"]}
    )

    # Volumes
    job["spec"]["template"]["spec"]["volumes"] = []
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"] = []

    # Output volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "data",
            "persistentVolumeClaim": {"claimName": body["metadata"]["name"] + "-data"},
        }
    )
    volume_mount = {"mountPath": "/data/", "name": "data", "readOnly": False}
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )

    # set the account
    job["spec"]["template"]["spec"]["serviceAccount"] = OperatorConfig.SERVICE_ACCOUNT
    job["spec"]["template"]["spec"][
        "serviceAccountName"
    ] = OperatorConfig.SERVICE_ACCOUNT
    # Workflow config volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "workflow",
            "configMap": {"defaultMode": 420, "name": body["metadata"]["name"]},
        }
    )
    volume_mount = {
        "mountPath": "/workflow.yaml",
        "name": "workflow",
        "subPath": "workflow.yaml",
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    job = jobs_common_params(job, logger)
    create_job(logger, body, job)


def create_publish_job(body, logger):
    init_script = OperatorConfig.POD_PUBLISH_INIT_SCRIPT

    with open("templates/publish-job-template.yaml", "r") as stream:
        try:
            job = yaml.safe_load(stream)
        except yaml.YAMLError as exc:
            print(exc)

    job["metadata"]["labels"]["app"] = body["metadata"]["name"]
    job["metadata"]["labels"]["workflow"] = body["metadata"]["labels"]["workflow"]
    job["metadata"]["labels"]["component"] = "publish"

    job["metadata"]["name"] = f"{body['metadata']['name']}-publish-job"
    job["metadata"]["namespace"] = body["metadata"]["namespace"]

    job["spec"]["template"]["metadata"]["labels"]["workflow"] = body["metadata"][
        "labels"
    ]["workflow"]
    job["spec"]["template"]["metadata"]["labels"]["component"] = "publish"

    job["spec"]["template"]["spec"]["containers"][0]["command"] = [
        "sh",
        "-c",
        init_script,
    ]
    job["spec"]["template"]["spec"]["containers"][0][
        "image"
    ] = OperatorConfig.POD_PUBLISH_CONTAINER

    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "CREDENTIALS", "value": OperatorConfig.ACCOUNT_JSON}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "PASSWORD", "value": OperatorConfig.ACCOUNT_PASSWORD}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "INPUTS", "value": OperatorConfig.INPUTS_FOLDER}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "TRANSFORMATIONS", "value": OperatorConfig.TRANSFORMATIONS_FOLDER}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "VOLUME", "value": "/data"}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "WORKFLOW", "value": OperatorConfig.WORKFLOW}
    )

    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_USER", "value": PGConfig.POSTGRES_USER}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_PASSWORD", "value": PGConfig.POSTGRES_PASSWORD}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_HOST", "value": PGConfig.POSTGRES_HOST}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_PORT", "value": PGConfig.POSTGRES_PORT}
    )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "POSTGRES_DB", "value": PGConfig.POSTGRES_DB}
    )

    if OperatorConfig.AWS_ACCESS_KEY_ID is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "AWS_ACCESS_KEY_ID", "value": OperatorConfig.AWS_ACCESS_KEY_ID}
        )
    if OperatorConfig.AWS_SECRET_ACCESS_KEY is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {
                "name": "AWS_SECRET_ACCESS_KEY",
                "value": OperatorConfig.AWS_SECRET_ACCESS_KEY,
            }
        )
    if OperatorConfig.AWS_REGION is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "AWS_REGION", "value": OperatorConfig.AWS_REGION}
        )
    if OperatorConfig.AWS_BUCKET_OUTPUT is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "AWS_BUCKET_OUTPUT", "value": OperatorConfig.AWS_BUCKET_OUTPUT}
        )
    if OperatorConfig.AWS_BUCKET_ADMINLOGS is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {
                "name": "AWS_BUCKET_ADMINLOGS",
                "value": OperatorConfig.AWS_BUCKET_ADMINLOGS,
            }
        )
    if OperatorConfig.IPFS_OUTPUT is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "IPFS_OUTPUT", "value": OperatorConfig.IPFS_OUTPUT}
        )
    if OperatorConfig.IPFS_ADMINLOGS is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "IPFS_ADMINLOGS", "value": OperatorConfig.IPFS_ADMINLOGS}
        )
    if OperatorConfig.IPFS_OUTPUT_PREFIX is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "IPFS_OUTPUT_PREFIX", "value": OperatorConfig.IPFS_OUTPUT_PREFIX}
        )
    if OperatorConfig.IPFS_ADMINLOGS_PREFIX is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {
                "name": "IPFS_ADMINLOGS_PREFIX",
                "value": OperatorConfig.IPFS_ADMINLOGS_PREFIX,
            }
        )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {
            "name": "STORAGE_EXPIRY",
            "value": str(
                body["spec"]["metadata"]["stages"][0]["compute"]["storageExpiry"]
            ),
        }
    )
    if OperatorConfig.IPFS_API_KEY is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "IPFS_API_KEY", "value": OperatorConfig.IPFS_API_KEY}
        )
    if OperatorConfig.IPFS_API_CLIENT is not None:
        job["spec"]["template"]["spec"]["containers"][0]["env"].append(
            {"name": "IPFS_API_CLIENT", "value": OperatorConfig.IPFS_API_CLIENT}
        )
    job["spec"]["template"]["spec"]["containers"][0]["env"].append(
        {"name": "WORKFLOWID", "value": body["metadata"]["name"]}
    )
    # Volumes
    job["spec"]["template"]["spec"]["volumes"] = []
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"] = []

    # Output volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "data",
            "persistentVolumeClaim": {"claimName": body["metadata"]["name"] + "-data"},
        }
    )
    volume_mount = {"mountPath": "/data/", "name": "data", "readOnly": False}
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    # Admin logs volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "adminlogs",
            "persistentVolumeClaim": {
                "claimName": body["metadata"]["name"] + "-adminlogs"
            },
        }
    )
    volume_mount = {
        "mountPath": "/data/adminlogs",
        "name": "adminlogs",
        "readOnly": False,
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )

    # set the account
    job["spec"]["template"]["spec"]["serviceAccount"] = OperatorConfig.SERVICE_ACCOUNT
    job["spec"]["template"]["spec"][
        "serviceAccountName"
    ] = OperatorConfig.SERVICE_ACCOUNT

    # Workflow config volume
    job["spec"]["template"]["spec"]["volumes"].append(
        {
            "name": "workflow",
            "configMap": {"defaultMode": 420, "name": body["metadata"]["name"]},
        }
    )
    volume_mount = {
        "mountPath": "/workflow.yaml",
        "name": "workflow",
        "subPath": "workflow.yaml",
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    volume_mount = {
        "mountPath": "/workflow.json",
        "name": "workflow",
        "subPath": "workflow.json",
    }
    job["spec"]["template"]["spec"]["containers"][0]["volumeMounts"].append(
        volume_mount
    )
    job = jobs_common_params(job, logger)
    create_job(logger, body, job)


def create_job(logger, body, job):
    try:
        logger.debug(f"Creating job {job}")
        batch_client = kubernetes.client.BatchV1Api()
        obj = batch_client.create_namespaced_job(body["metadata"]["namespace"], job)
        logger.info(f"{obj.kind} {obj.metadata.name} created")
    except ApiException as e:
        logger.debug(f"Exception when calling BatchV1Api->create_namespaced_job: {e}\n")


def wait_finish_job(namespace, pod_name, logger):
    try:
        api = kubernetes.client.BatchV1Api()
        obj = api.read_namespaced_job(namespace=namespace, name=pod_name)
        if obj.status.succeeded is None:
            return False
        status = obj.status.succeeded
        if int(status) > 0:
            return True
        else:
            return False
    except ApiException as e:
        logger.debug(f"Exception when calling BatchV1Api->read_namespaced_job: {e}\n")
        if e.reason == "Not Found":
            return True
    return False


def cleanup_job(namespace, jobId, logger):
    if OperatorConfig.DEBUG_NO_CLEANUP is None:
        api = kubernetes.client.CoreV1Api()
        # pvc claims
        try:
            name = jobId + "-adminlogs"
            logger.debug(f"Removing pvc {name}")
            api.delete_namespaced_persistent_volume_claim(
                namespace=namespace,
                name=name,
                propagation_policy="Foreground",
                grace_period_seconds=1,
            )
        except ApiException as e:
            logger.warning(f"Failed to remove admin logs pvc\n")
        try:
            name = jobId + "-data"
            logger.debug(f"Removing pvc {name}")
            api.delete_namespaced_persistent_volume_claim(
                namespace=namespace,
                name=name,
                propagation_policy="Foreground",
                grace_period_seconds=1,
            )
        except ApiException as e:
            logger.warning(f"Failed to remove data pvc\n")

        # config map
        try:
            name = jobId
            logger.debug(f"Removing configmap {name}")
            api.delete_namespaced_config_map(
                namespace=namespace,
                name=name,
                propagation_policy="Foreground",
                grace_period_seconds=1,
            )
        except ApiException as e:
            logger.warning(f"Failed to remove configmap\n")
        logger.debug(f"Clean up done for {jobId}")
    else:
        logger.info(f"No Clean up done for {jobId} !!")
    return


def update_sql_job_datefinished(jobId, logger):
    connection = getpgconn(logger)
    try:
        cursor = connection.cursor()
        postgres_update_query = (
            """ UPDATE jobs SET dateFinished=NOW() WHERE workflowId=%s"""
        )
        record_to_update = (jobId,)
        cursor.execute(postgres_update_query, record_to_update)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        logger.error("Error in  update_sql_job_datefinished PostgreSQL:" + str(error))
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()


def jobs_common_params(job, logger):
    job = create_node_selector(job, logger)
    job = update_imagePullSecrets(job, logger)
    job = update_imagePullPolicy(job, logger)
    return job


def create_node_selector(job, logger):
    if OperatorConfig.NODE_SELECTOR is None:
        return job
    try:
        job["spec"]["template"]["spec"]["affinity"] = dict()
        job["spec"]["template"]["spec"]["affinity"]["nodeAffinity"] = dict()
        affinity = (
            """{
                "requiredDuringSchedulingIgnoredDuringExecution": {
                    "nodeSelectorTerms": [
                        {
                            "matchExpressions": [
                                {
                                    "key": "scope",
                                    "operator": "In",
                                    "values": [
                                        "%s"
                                    ]
                                }
                            ]
                        }
                    ]
                }
        }"""
            % OperatorConfig.NODE_SELECTOR
        )
        job["spec"]["template"]["spec"]["affinity"]["nodeAffinity"] = json.loads(
            affinity
        )
    except Exception as e:
        logger.error(e)
    return job


def update_imagePullSecrets(job, logger):
    if OperatorConfig.PULL_SECRET is None:
        return job
    job["spec"]["template"]["spec"]["imagePullSecrets"] = list()
    job["spec"]["template"]["spec"]["imagePullSecrets"].append(
        {"name": OperatorConfig.PULL_SECRET}
    )
    return job


def update_imagePullPolicy(job, logger):
    if OperatorConfig.PULL_POLICY is None:
        return job
    job["spec"]["template"]["spec"]["containers"][0][
        "imagePullPolicy"
    ] = OperatorConfig.PULL_POLICY
    return job


def update_sql_job_istimeout(jobId, logger):
    connection = getpgconn(logger)
    try:
        cursor = connection.cursor()
        postgres_update_query = """ UPDATE jobs SET stopreq=2 WHERE workflowId=%s"""
        record_to_update = (jobId,)
        cursor.execute(postgres_update_query, record_to_update)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        logger.error("Error in  update_sql_job_istimeout PostgreSQL:" + str(error))
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()


def update_sql_job_status(jobId, status, logger):
    connection = getpgconn(logger)
    try:
        switcher = {
            10: "Job started",
            20: "Configuring volumes",
            40: "Running algorithm ",
            50: "Filtering results",
            60: "Publishing results",
            70: "Job finished",
        }
        statusText = switcher.get(status, "Unknown status")
        cursor = connection.cursor()
        postgres_update_query = (
            """ UPDATE jobs SET status=%s,statusText=%s WHERE workflowId=%s"""
        )
        record_to_update = (status, statusText, jobId)
        cursor.execute(postgres_update_query, record_to_update)
        connection.commit()
    except (Exception, psycopg2.Error) as error:
        logger.error("Error in update_sql_job_status PostgreSQL:" + str(error))
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()


def get_sql_job_status(jobId, logger):
    connection = getpgconn(logger)
    try:
        cursor = connection.cursor()
        params = dict()
        select_query = "SELECT status FROM jobs WHERE workflowId=%(jobId)s LIMIT 1"
        params["jobId"] = jobId
        cursor.execute(select_query, params)
        returnstatus = -1
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            returnstatus = row[0]
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Got PG error in get_sql_job_status: {error}")
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
    return returnstatus


def get_sql_job_workflow(jobId, logger):
    connection = getpgconn(logger)
    try:
        cursor = connection.cursor()
        params = dict()
        select_query = "SELECT workflow FROM jobs WHERE workflowId=%(jobId)s LIMIT 1"
        params["jobId"] = jobId
        cursor.execute(select_query, params)
        returnstatus = None
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            returnstatus = row[0]
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Got PG error in get_sql_job_status: {error}")
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
    return returnstatus


def announce_and_get_sql_pending_jobs(logger, announce, limit):
    if limit < 0:
        limit = 0
    connection = getpgconn(logger)
    returnstatus = []
    try:
        cursor = connection.cursor()
        params = dict()
        select_query = "SELECT * FROM announce(%(namespace)s, %(status)s, %(lmt)s)"
        params["namespace"] = announce["id"]
        params["status"] = json.dumps(announce)
        params["lmt"] = limit
        logger.debug(f" Doing {select_query} with {params}")
        cursor.execute(select_query, params)
        connection.commit()
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            returnstatus.append(row[0])
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Got PG error in get_sql_job_status: {error}")
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
    logger.debug(f"announce_and_get_sql_pending_jobs goes back with  {returnstatus}")
    return returnstatus


def check_sql_stop_requested(jobId, logger):
    connection = getpgconn(logger)
    returnstatus = False
    try:
        cursor = connection.cursor()
        params = dict()
        select_query = "SELECT stopreq FROM jobs WHERE workflowId=%(jobId)s LIMIT 1"
        params["jobId"] = jobId
        cursor.execute(select_query, params)
        while True:
            row = cursor.fetchone()
            if row == None:
                break
            if row[0] == 1:
                returnstatus = True
    except (Exception, psycopg2.Error) as error:
        logger.error(f"Got PG error in check_sql_stop_requested: {error}")
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
    return returnstatus


def getpgconn(logger):
    try:
        connection = psycopg2.connect(
            user=PGConfig.POSTGRES_USER,
            password=PGConfig.POSTGRES_PASSWORD,
            host=PGConfig.POSTGRES_HOST,
            port=PGConfig.POSTGRES_PORT,
            database=PGConfig.POSTGRES_DB,
        )
        connection.set_client_encoding("LATIN9")
        return connection
    except (Exception, psycopg2.Error) as error:
        logger.error(f"New PG connect error: {error}")
        return None


def generate_new_id():
    """
    Generate a new id without prefix.
    :return: Id, str
    """
    return uuid.uuid4().hex


def notify_start(body, logger):
    if OperatorConfig.NOTIFY_START_URL is not None:
        do_notify(OperatorConfig.NOTIFY_START_URL, body, logger)


def notify_stop(body, logger):
    if OperatorConfig.NOTIFY_STOP_URL is not None:
        do_notify(OperatorConfig.NOTIFY_STOP_URL, body, logger)


def do_notify(url, body, logger):
    """
    Call URL to notify that a new job is starting or ended
    POST requests containing jobId,input DIDS, algo DID, secret
    """
    payload = dict()
    payload["algoDID"] = None
    if "id" in body["spec"]["metadata"]["stages"][0]["algorithm"]:
        payload["algoDID"] = body["spec"]["metadata"]["stages"][0]["algorithm"]["id"]
    payload["jobId"] = body["metadata"]["name"]
    payload["secret"] = body["metadata"]["secret"]
    payload["DID"] = list()
    for input in body["spec"]["metadata"]["stages"][0]["input"]:
        payload["DID"].append(input["id"])
    message_to_sign = (
        json.dumps(payload["secret"])
        + json.dumps(payload["DID"])
        + json.dumps(payload["jobId"])
        + json.dumps(payload["algoDID"])
    )
    payload["signature"] = sign_message(message_to_sign)
    logger.info(f"Notify url {url} with payload")
    logger.info(json.dumps(payload))
    try:
        r = requests.post(url, json=payload)
    except requests.exceptions.RequestException as e:  # This is the correct syntax
        logger.warning(f"Notify failed:{e}")


def add_ethereum_prefix_and_hash_msg(text):
    """
    This method of adding the ethereum prefix seems to be used in web3.personal.sign/ecRecover.
    :param text: str any str to be signed / used in recovering address from a signature
    :return: hash of prefixed text according to the recommended ethereum prefix
    """
    prefixed_msg = f"\x19Ethereum Signed Message:\n{len(text)}{text}"
    return Web3.sha3(text=prefixed_msg)


def sign_message(text):
    if OperatorConfig.OPERATOR_PRIVATE_KEY is None:
        return None
    prefixed_msg = f"\x19Ethereum Signed Message:\n{len(text)}{text}"
    msg_hash = Web3.sha3(text=prefixed_msg)
    account = Account.from_key(OperatorConfig.OPERATOR_PRIVATE_KEY)
    s = account.signHash(msg_hash)
    return s.signature.hex()


def enforce_compute_resources(body):
    """
    Enforces job resources based on config and returns the job object
    """
    resources = dict()
    resources["inputVolumesize"] = str(OperatorConfig.ENVIROMENT_diskGB) + "Gi"
    resources["outputVolumesize"] = str(OperatorConfig.ENVIROMENT_diskGB) + "Gi"
    resources["adminlogsVolumesize"] = str(OperatorConfig.ENVIROMENT_diskGB) + "Gi"
    resources["requests_cpu"] = str(OperatorConfig.ENVIROMENT_nCPU)
    resources["requests_memory"] = str(OperatorConfig.ENVIROMENT_ramGB) + "Gi"
    resources["limits_cpu"] = str(OperatorConfig.ENVIROMENT_nCPU)
    resources["limits_memory"] = str(OperatorConfig.ENVIROMENT_ramGB) + "Gi"
    for count, stage in enumerate(body["spec"]["metadata"]["stages"]):
        stage["compute"]["resources"] = resources
        stage["compute"]["storageExpiry"] = OperatorConfig.ENVIROMENT_storageExpiry
        stage["compute"]["maxtime"] = OperatorConfig.ENVIROMENT_maxJobDuration
    return body
