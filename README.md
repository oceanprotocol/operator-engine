[![banner](https://raw.githubusercontent.com/oceanprotocol/art/master/github/repo-banner%402x.png)](https://oceanprotocol.com)

# Operator-Engine

> Python library allowing to interact with the Kubernetes infrastructure


Table of Contents
=================

   * [Operator-Service](#operator-service)
      * [About](#about)
      * [Getting Started](#getting-started)
         * [Local Environment](#local-environment)
            * [Installing AWS &amp; K8s tools](#installing-aws--k8s-tools)
            * [Running the Service](#running-the-service)
         * [Testing](#testing)
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

### Local Environment

The operator engine is in charge of gathering all the Worflow requests directly from the K8s infrastructure.
To do that, in a local environment the operator engine needs connectivity to you K8s environment.

There are multiple configurations and deployments of K8s possible, but here we are going to show 
how to connect to an existing K8s cluster running in Amazon Web Services (AWS).


#### Compiling the engine

Once you have Kubectl able to connect you your K8s cluster, run the service is as simple as running the following commands:

```
virtualenv -p python3.7 venv
source venv/bin/activate
pip install -r requirements_dev.txt
```


### Testing

Automatic tests are set up via Travis, executing `tox`.
Our tests use the pytest framework.

### New Version

The `bumpversion.sh` script helps bump the project version. You can execute the script using `{major|minor|patch}` as first argument, to bump the version accordingly.

## License

Copyright 2018 Ocean Protocol Foundation Ltd.

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

   http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
