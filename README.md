[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

<h1 align="center">Operator-Engine</h1>

> Orchestrates a compute job

![Travis (.com) branch](https://img.shields.io/travis/com/oceanprotocol/operator-engine/develop)
![GitHub contributors](https://img.shields.io/github/contributors/oceanprotocol/operator-engine)
 

Table of Contents
=================

   * [Operator-Engine](#operator-engine)
   * [Table of Contents](#table-of-contents)
      * [About](#about)
      * [Getting Started](#getting-started)
         * [Running the Engine](#running-the-engine)
            * [Applying the Operator Engine deployment](#applying-the-operator-engine-deployment)
            * [Running in Development mode](#running-in-development-mode)
            * [Running in a not Develop mode](#running-in-a-not-develop-mode)
            * [Preparation of your local environment](#preparation-of-your-local-environment)
         * [Continuous Integration &amp; Delivery](#continuous-integration--delivery)
         * [Testing](#testing)
         * [Testing in the K8s cluster](#testing-in-the-k8s-cluster)
         * [New Version](#new-version)
      * [License](#license)


## About

The Operator Engine is a backend agent implementing part of the Ocean Protocol 
[Compute to the Data OEP-12](https://github.com/oceanprotocol/OEPs/tree/master/12#infrastructure-orchestration), 
in charge of orchestrate the compute infrastructure using Kubernetes as backend.
Typically the Operator Engine retrieve the Workflows created by the [Operator Service](https://github.com/oceanprotocol/operator-service),
in Kubernetes and manage the infrastructure necessary to complete the execution of the compute workflows.

The Operator Engine is in charge of retrieving all the Workflows registered in a K8s cluster, allowing to:

* Orchestrate the flow of the execution
* Start the configuration pod in charge of download the workflow dependencies (datasets and algorithms)
* Start the pod including the algorithm to execute
* Start the publishing pod that uploads the results to a remote storage(ipfs or S3)


## Getting Started

### Running the Engine

The operator engine is in charge of gathering all the Worflow requests directly from the K8s infrastructure.
To do that, the operator engine needs to be running inside the K8s cluster where the engine will read the Workflows registered.

There are multiple configurations and deployments of K8s possible, it's out of the scope of this documentation page
to describe how to configure your K8s cluster.

#### Applying the Operator Engine deployment

First is necessary to apply the `operator-engine` YAML defining the K8s deployment:

```
$ kubectl create ns ocean-compute
$ kubectl config set-context --current --namespace ocean-compute 
$ kubectl apply -f kubernetes/sa.yml
$ kubectl apply -f kubernetes/binding.yml
$ kubectl apply -f kubernetes/operator.yml
```

This will generate the `ocean-compute-operator` deployment in K8s. You can check the `Deployment` was created successfully 
using the following command:

```
$ kubectl  get deployment ocean-compute-operator -o yaml
``` 

By default we use the `ocean-compute` namespace in the K8s deployments.

After apply the `Deployment` you should be able to see the `operator-engine` pod with the prefix `ocean-compute-operator`:

```
$ kubectl  get pod ocean-compute-operator-7b5779c47b-2r4j8 

NAME                                      READY   STATUS    RESTARTS   AGE
ocean-compute-operator-7b5779c47b-2r4j8   1/1     Running   0          12m

```

## Customize your Operator Engine deployment

The following resources need attention:

| Variable                                               | Description                                                                                 |
| ------------------------------------------------------ | ------------------------------------------------------------------------------------------- |
| `OPERATOR_PRIVATE_KEY`                                 | Private key of address used to sign notifications and consume algo/inputs (operator service has the same address)                   |
| `IPFS_TYPE`                                            | IPFS library to use. 'CLUSTER' to use ipfs-cluster, 'CLIENT' to use ipfs-client (default)   |
| `IPFS_OUTPUT`, `IPFS_ADMINLOGS`                        | IPFS gateway to upload the output data (algorithm logs & algorithm output) and admin logs (logs from pod-configure & pod-publish)|
| `IPFS_OUTPUT_PREFIX`, `IPFS_ADMINLOGS_PREFIX`          | Prefix used for the results files (see below)                                               |
| `IPFS_EXPIRY_TIME`                                     | Default expiry time  for ipfs  (see https://github.com/ipfs/ipfs-cluster/blob/dbca14e83295158558234e867477ce07a523b81b/CHANGELOG.md#rest-api-2_), with an expected value in Go's time format, i.e. 12h (optional)
| `IPFS_API_KEY`, `IPFS_API_CLIENT `                     | IPFS API Key and Client ID for authentication purpose (optional)                            |
| `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION` | S3 credentials for the logs and output buckets.                                         |
| `AWS_BUCKET_OUTPUT`                                    | Bucket that will hold the output data (algorithm logs & algorithm output).                  |
| `AWS_BUCKET_ADMINLOGS`                                 | Bucket that will hold the admin logs (logs from pod-configure & pod-publish).               |
| `STORAGE_CLASS`                                        | Storage class to use (see next section).                                                    |
| `NOTIFY_START_URL`                                     | URL to call when a new job starts.                                                          |
| `NOTIFY_STOP_URL`                                      | URL to call when a new job ends.                                                            |
| `SERVICE_ACCOUNT`                                      | K8 service account to run pods (same as the one used in deployment). Defaults to db-operator|
| `NODE_SELECTOR`                                        | K8 node selector (if defined)                                                               |


 
 Only one method of uploading is going to be used. Priority is:
  - first IPFS vars are checked. If they exists, then IPFS will be used
  - 2nd, AWS vars are checked. If they exists, then AWS S3 will be used

## Usage of IPFS_OUTPUT and IPFS_OUTPUT_PREFIX (IPFS_ADMINLOGS/IPFS_ADMINLOGS_PREFIX)
   This will allow you to have the following scenarios:
   1. IPFS_OUTPUT=ipfs.oceanprotocol.com:5001 , IPFS_OUTPUT_PREFIX=ipfs.oceanprotocol.com:8080/ipfs/

            Port 5001 will be used to call addFIle, but the result will look like "ipfs.oceanprotocol.com:8080/ipfs/HASH"
   2. IPFS_OUTPUT=ipfs.oceanprotocol.com:5001 , IPFS_OUTPUT_PREFIX=ipfs://

            Port 5001 will be used to call addFIle, but the result will look like "ipfs://HASH"  (you will hide your ipfs deployment)
   3. IPFS_EXPIRY_TIME  = the default expiry time. "0"  = unlimited

## Usage of NOTIFY_START_URL and NOTIFY_STOP_URL
   Engine will JSON POST the following for each action:
    - algoDID: Algorithm DID (if any)
    - jobId: Job ID
    - secret: Secret value (exported to algo pod as secret env)
    - DID: Array of input DIDs

## Usage of NODE_SELECTOR
   If defined, all pods are going to contain the following selectors in the specs:
   ```
   spec:
      template:
         spec:
            affinity:
               nodeAffinity:
                  requiredDuringSchedulingIgnoredDuringExecution:
                     nodeSelectorTerms:
                     - matchExpressions:
                        - key: scope
                           operator: In
                           values:
                           - $NODE_SELECTOR
   ```

   This allows you to run C2D pods on specific nodes

## Storage class

For minikube, you can use 'standard' class.

For AWS , please make sure that your class allocates volumes in the same region and zone in which you are running your pods.

We created our own 'standard' class in AWS:

```bash
kubectl get storageclass standard -o yaml
```

```yaml
allowedTopologies:
- matchLabelExpressions:
    - key: failure-domain.beta.kubernetes.io/zone
          values:
          - us-east-1a
apiVersion: storage.k8s.io/v1
kind: StorageClass
parameters:
    fsType: ext4
    type: gp2
provisioner: kubernetes.io/aws-ebs
reclaimPolicy: Delete
volumeBindingMode: Immediate
```

Or we can use this for minikube:

```yaml
apiVersion: storage.k8s.io/v1
kind: StorageClass
metadata:
  name: standard
provisioner: docker.io/hostpath
reclaimPolicy: Retain
```

For more information, please visit https://kubernetes.io/docs/concepts/storage/storage-classes/


## Customizing job templates

All pods(jobs) are started using the templates from operator_engine/templates/ folder. If you want to customize them (adding some apps customizations, labels, etc) then you can mount that folder using an external volume.  Please make sure that you have all template and not only the custom ones.


## Running in Development mode

If you run the `operator-engine` in development mode, it will allows to:

* Get access to the `operator-engine` pod
* Start and stop multiple times the `operator-engine` process, changing the code directly in the pod
* Test with different configurations without re-generating docker images

Typically the main process of the `operator-engine` pod is the `kopf` process. You can get access to any `operator-engine`
pod running the typical `kubectl exec` command, but if you want to stop `kopf`, modify the config and the code and try again, 
it's recommended to modify the starting command of the pod. You can do that un-comment the startup command in the 
`Dockerfile` file where you use `tail` instead of the `kopf` command. This will start the pod but not the `kopf` process
inside the pod. Allowing to you to get access there and start/stop kopf as many times you want. 

After changing the `Dockerfile` you can publish a new version of the `operator-engine` docker image. At this point,
you can stop the `ocean-compute-operator` pod. Take into account the pod id in your deployment will be different: 
```
$ kubectl delete pod ocean-compute-operator-7b5779c47b-2jrlp
```

This will force the pull of the latest version of the `operator-engine` to be downloaded and run in the K8s cluster.
Having that you should be able to get access to the pod:

```
$ kubectl exec -it ocean-compute-operator-7b5779c47b-2jrlp bash

root@ocean-compute-operator-7b5779c47b-2jrlp:/operator_engine# ps aux

USER       PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND
root         1  0.0  0.0   4080   736 ?        Ss   09:35   0:00 tail -f /dev/null
root         9  0.3  0.0   5752  3544 pts/0    Ss   09:45   0:00 bash
root        16  0.0  0.0   9392  3064 pts/0    R+   09:45   0:00 ps aux

```

Now inside the pod you can start `kopf` running the following command:

```
$ kopf run --standalone /operator_engine/operator_main.py
``` 

This should start the `operator-engine` subscribed to the `Workflows` registered in K8s. 

#### Running in a not Develop mode

First time you create the operator setup, you need to initialize the operator deployment as we saw above using the command:

```
$ kubectl apply -f k8s_install/operator.yml
```

This should start automatically the `ocean-compute-operator` pod using by default the latest Docker image of the `operator-engine`. 
You can check everything is running:

```
$ kubectl get pod ocean-compute-operator-7b5779c47b-2r4j8  
NAME                                      READY   STATUS    RESTARTS   AGE
ocean-compute-operator-7b5779c47b-2r4j8   1/1     Running   0          114m
```


#### Preparation of your local environment

Once you have Kubectl able to connect you your K8s cluster, run the service is as simple as running the following commands:

```
virtualenv -p python3.7 venv
source venv/bin/activate
pip install -r requirements_dev.txt
```

### Continuous Integration & Delivery

You can find the Travis compilation here: https://travis-ci.com/oceanprotocol/operator-engine

And the Docker images here: https://hub.docker.com/r/oceanprotocol/operator-engine/


### Testing

Automatic tests are set up via Travis, executing `tox`.
Our tests use the pytest framework.

### Testing in the K8s cluster

You can register a `Workflow` in K8s to check how the `operator-engine` orchestrate the compute execution using one of the test examples
included in the project. You can register it running the following command:

```
$ kubectl apply -f k8s_install/workflow-1.yaml 
workflow.oceanprotocol.com/workflow-1 created

```

In the `operator-engine` pod you should see in the logs how the `engine` is doing some job:

```
[2019-09-17 12:27:03,730] ocean-operator       [INFO    ] Stage 0 with stageType Filtering
[2019-09-17 12:27:03,731] ocean-operator       [INFO    ] Running container openjdk:14-jdk
[2019-09-17 12:27:03,757] ocean-operator       [INFO    ] ConfigMap workflow-1 created
[2019-09-17 12:27:03,771] ocean-operator       [INFO    ] PersistentVolumeClaim workflow-1 created
[2019-09-17 12:27:03,790] ocean-operator       [INFO    ] Job workflow-1-configure-job created
[2019-09-17 12:27:03,803] ocean-operator       [INFO    ] Waiting configure pod to finish
[2019-09-17 12:27:13,826] ocean-operator       [INFO    ] Waiting configure pod to finish
[2019-09-17 12:27:23,853] ocean-operator       [INFO    ] Waiting configure pod to finish
[2019-09-17 12:27:33,892] ocean-operator       [INFO    ] Job workflow-1-algorithm-job created
[2019-09-17 12:27:33,901] ocean-operator       [INFO    ] Waiting algorithm pod to finish
[2019-09-17 12:27:43,942] ocean-operator       [INFO    ] Job workflow-1-publish-job created
[2019-09-17 12:27:43,951] ocean-operator       [INFO    ] Waiting publish pod to finish
[2019-09-17 12:27:53,978] ocean-operator       [INFO    ] Waiting publish pod to finish
[2019-09-17 12:28:04,003] ocean-operator       [INFO    ] Waiting publish pod to finish
```

You can check the individual logs of the compute pods using the standard K8s log command:

```
$ kubectl logs 
ocean-compute-operator-7b5779c47b-2r4j8  workflow-1-configure-job-qk4pv           
workflow-1-algorithm-job-c9m4t           workflow-1-publish-job-dcfjc             
$ kubectl logs ocean-compute-operator-7b5779c47b-2r4j8 

```

### New Version

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.

## License

Copyright 2019 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
