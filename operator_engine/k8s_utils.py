#  Copyright 2019 Ocean Protocol Foundation
#  SPDX-License-Identifier: Apache-2.0
import kubernetes


def wait_finish_job(namespace, pod_name):
    api = kubernetes.client.BatchV1Api()
    try:
        obj = api.read_namespaced_job(namespace=namespace, name=pod_name)
        status = obj.status.succeeded
        if int(status) > 0:
            return True
        else:
            return False
    except Exception:
        return False
