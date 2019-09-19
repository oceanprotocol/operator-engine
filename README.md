[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# Operator-Engine

> Python library allowing to interact with the Kubernetes infrastructure

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
* Start the publishing pod that publish the new assets created in the Ocean Protocol network.

The Operator Engine doesn't provide any storage capability, all the state is stored directly in the K8s cluster.

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
$ kubectl apply -f k8s_install/sa.yml
$ kubectl apply -f k8s_install/binding.yml
$ kubectl apply -f k8s_install/operator.yml
$ kubectl apply -f k8s_install/computejob-crd.yaml
$ kubectl apply -f k8s_install/workflow-crd.yaml
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


#### Running in Development mode

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
