# DWS Utility
The DWS Utility attempts to perform basic interactivity with the DWS API endpoint.

## Basic functionality
---
- Get a list of Workflows
- Retrieve basic information on a single Workflow
- Create a new Workflow
- Assign resources to a Workflow
- Progress a Workflow through all desired states
- Progress a Workflow directly to teardown
- Delete a Workflow
- Show inventory from a cluster or an inventory file

## Basic DWS Utility setup
### From a git repository
---
NOTE: This approach is based on venv and always requires you to source venv/bin/activate to work.
- DWS Utility requires Python 3 and several Python packages, recommend using VENV
- DWS Utility requires a valid kube config file and will utilize the following in order:
     **-k path_to_config** command line option
     The **config** item in the **k8s** section of the dwsutil config file in use
     The normal Kubernetes configuration as specified by \$KUBECONFIG or \$HOME/.kube
- DWS Utility will use the default Kubernetes context, however the context may be overriden with the --kctx flag
- TIP: Use the --showconfig flag to see what dwsutil.py will be using


```
$ git clone git@github.hpe.com:hpe/hpc-rabsw-dwsutil.git ; cd hpc-rabsw-dwsutil

$ python3 -m venv venv

$ . venv/bin/activate
(venv) $ pip install -r requirements.txt

(venv) $ ./dwsutil.py --showconfig --notimestamp
    DWS API Endpoint....: https://127.0.0.1:37645
    config file.........: dwsutil.cfg                    ( Existing dwsutil.cfg )
    k8s config file.....: /home/developer/.kube/config   ( $KUBECONFIG env )
    Preview.............: False
    Context.............: WFR
    Operation...........:
    ...Count............: 1
    WFR name............:
    WLM id..............: 5f239bd8-30db-450b-8c2c-a1a7c8631a1a
    Job id..............: 5555
    User id.............: 1001
    # of nodes..........: 1
    Exclude computes....: ['bogus 1', 'bogus 2']
    Exclude rabbits.....: ['bogus rabbit 1', 'bogus rabbit 2']
    Inventory file......: None
    dw directive........: #DW jobdw type=xfs capacity=5GB name=vm-test-1-raw
    ShowConfig..........: True
    Munge WFR names.....: False
    Munge Compute names.: False
    Allow regexes.......: False

```

## Basic DWS Utility configuration
By default, dwsutil.py will look for a configuration file named dwsutil.cfg.  The configuration file may also be specified by setting the DWSUTIL_CONFIG environment variable to point to a configuration file.  The configuration file may be overriden using the command line flag -c path_to_config.  A configuration file is NOT NECESSARY if a kube config can be resolved using other means.  See the note above on kube config resolution.

Many of the command line options may be specified in a configuration file. 
- All of the fields are optional and have defaults in dwsutil
- Individual items may be commented out with a '#'
- The path for the k8s config file may contain environment variables

The following is an example configuration containing most of the configurable items:
```yaml
k8s:
  config: $HOME/.kube/config
  context: kind-vm
config:
  userid: 1001
  jobid: 987
  wlmid: "flux01"
  wfrname: "mywfr"
  pretty: true
  quiet: true
  munge: false
  nodes: 1
  regex: true
  inventory: "data/compute_inventory.yaml"
  mungecomputes: true
  preview: true
  directives:
    - dw: "#DW jobdw type=xfs capacity=5GB name=vm-test-1-raw"
  exclude_computes:
    - name: "Compute 0"
    - name: "Compute 3"
  exclude_rabbits:
    - name: "rabbit-node-0"
    - name: "rabbit-node-123"
```

## Basic DWS Utility usage
---
**NOTE:**
- The default context for dwsutil is Workflow/WFR
- The --preview flag will show any changes that would be made to the system without actually performing the operation

**Display program usage**
`$ ./dwsutil -?`

**Create a Workflow Resource**
```
$ ./dwsutil.py --operation create -n wfr-demo
```
```json
{
    "action": "create",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-demo created",
            "name": "wfr-demo",
            "result": "succeeded"
        }
    ]
}
```

**List existing Workflow resources (no filtering currently available)**
```
$ ./dwsutil.py --operation list
```
```json
{
    "wfrs": [
        "wfr-demo"
    ]
}
```

**Get basic Workflow information**
```
$ ./dwsutil.py --operation get -n wfr-demo
```
```json
{
    "desiredState": "proposal",
    "name": "wfr-demo",
    "ready": true,
    "state": "proposal"
}
```

**Assign resources to a Workflow resource**
NOTE: This will use cluster inventory unless overridden with an inventory file**
```
$ ./dwsutil.py --operation assignresources -n wfr-demo
```
```json
{
    "action": "assignresources",
    "preview": false,
    "results": [
        {
            "computes": [
                "Compute 0"
            ],
            "name": "wfr-demo",
            "result": "succeeded",
            "servers": [
                "kind-worker"
            ]
        }
    ]
}
```

**Progress a Workflow to the next desiredState**
NOTE: Workflow will not progress if it is not in a Ready state
```
$ ./dwsutil.py --operation progress -n wfr-demo
```
```json
{
    "action": "progress",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-demo' progressed from 'proposal' to 'setup'",
            "name": "wfr-demo",
            "result": "succeeded"
        }
    ]
}
```

**Progress a Workflow directly to the teardown desiredState**
```
$ ./dwsutil.py --operation progressteardown -n wfr-demo
```
```json
{
    "action": "progress",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-demo' progressed from 'setup' to 'teardown'",
            "name": "wfr-demo",
            "result": "succeeded"
        }
    ]
}
```
**Delete a Workflow**
NOTE: A Workflow must be in a teardown state to be deleted
```
$ ./dwsutil.py --operation delete -n wfr-demo
```
```json
{
    "action": "delete",
    "preview": false,
    "results": [
        {
            "name": "wfr-demo",
            "result": "succeeded"
        }
    ]
}
```

**Display cluster inventory**
```
$ ./dwsutil.py --context inventory --operation show
```
```json
{
    "nnfnodes": [
        {
            "capacity": 37383395344384,
            "computes": [
                {
                    "health": "OK",
                    "id": "0",
                    "name": "Rabbit",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "1",
                    "name": "Compute 0",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "2",
                    "name": "Compute 1",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "3",
                    "name": "Compute 2",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "4",
                    "name": "Compute 3",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "5",
                    "name": "Compute 4",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "6",
                    "name": "Compute 5",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "7",
                    "name": "Compute 6",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "8",
                    "name": "Compute 7",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "9",
                    "name": "Compute 8",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "10",
                    "name": "Compute 9",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "11",
                    "name": "Compute 10",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "12",
                    "name": "Compute 11",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "13",
                    "name": "Compute 12",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "14",
                    "name": "Compute 13",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "15",
                    "name": "Compute 14",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "16",
                    "name": "Compute 15",
                    "status": "Ready"
                }
            ],
            "name": "kind-worker",
            "status": "Ready"
        },
        {
            "capacity": 37378395406336,
            "computes": [
                {
                    "health": "OK",
                    "id": "0",
                    "name": "Rabbit",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "1",
                    "name": "Compute 0",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "2",
                    "name": "Compute 1",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "3",
                    "name": "Compute 2",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "4",
                    "name": "Compute 3",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "5",
                    "name": "Compute 4",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "6",
                    "name": "Compute 5",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "7",
                    "name": "Compute 6",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "8",
                    "name": "Compute 7",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "9",
                    "name": "Compute 8",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "10",
                    "name": "Compute 9",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "11",
                    "name": "Compute 10",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "12",
                    "name": "Compute 11",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "13",
                    "name": "Compute 12",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "14",
                    "name": "Compute 13",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "15",
                    "name": "Compute 14",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "16",
                    "name": "Compute 15",
                    "status": "Ready"
                }
            ],
            "name": "kind-worker2",
            "status": "Ready"
        }
    ],
    "source": "Cluster-http://192.168.100.12:8080"
}
```

## Advanced DWS Utility usage
---
**Specify additional attributes for a Workflow**
The following attributes may be specified when creating a Workflow:
- name
- wlmID
- jobID
- userID
- dw (datawarp directives)
  
`$ ./dwsutil.py --operation create -n wfr-06 --wlmid flux01 --jobid 5055 --userid 1002 --dw "#DW jobdw type=xfs capacity=5GB name=xfs01"`
```json
{
    "action": "create",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-06 created",
            "name": "wfr-06",
            "result": "succeeded"
        }
    ]
}
```

**Create multiple Workflow in a single operation (not multi-threaded)**
`$ ./dwsutil.py --operation create -n wfr-batch --opcount 5`
```json
{
    "action": "create",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-batch-0 created",
            "name": "wfr-batch-0",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-batch-1 created",
            "name": "wfr-batch-1",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-batch-2 created",
            "name": "wfr-batch-2",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-batch-3 created",
            "name": "wfr-batch-3",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-batch-4 created",
            "name": "wfr-batch-4",
            "result": "succeeded"
        }
    ]
}
```

`$ ./dwsutil.py --operation list`
```json
{
    "wfrs": [
        "wfr-batch-0",
        "wfr-batch-1",
        "wfr-batch-2",
        "wfr-batch-3",
        "wfr-batch-4"
    ]
}
```

**Many following operations allow regular expressions to be specified with the -n flag**
- progress
- progressteardown
- delete

`$ ./dwsutil.py --operation list`
```json
{
    "wfrs": [
        "wfr-01",
        "wfr-02",
        "wfr-03",
        "wfr-04",
        "wfr-05"
    ]
}
```

`$ ./dwsutil.py --operation progress --regex -n "wfr-0[1-3]"`
```json
{
    "action": "progress",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-01' progressed from 'proposal' to 'setup'",
            "name": "wfr-01",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-02' progressed from 'proposal' to 'setup'",
            "name": "wfr-02",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-03' progressed from 'proposal' to 'setup'",
            "name": "wfr-03",
            "result": "succeeded"
        }
    ]
}
```

`$ ./dwsutil.py --operation progressteardown --regex -n "wfr-0[1-5]"`
```json
{
    "action": "progressteardown",
    "preview": false,
    "results": [
        {
            "message": "Workflow 'wfr-01' progressed from 'setup' to 'teardown'",
            "name": "wfr-01",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-02' progressed from 'setup' to 'teardown'",
            "name": "wfr-02",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-03' progressed from 'setup' to 'teardown'",
            "name": "wfr-03",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-04' progressed from 'proposal' to 'teardown'",
            "name": "wfr-04",
            "result": "succeeded"
        },
        {
            "message": "Workflow 'wfr-05' progressed from 'proposal' to 'teardown'",
            "name": "wfr-05",
            "result": "succeeded"
        }
    ]
}
```

`$ ./dwsutil.py --operation delete --regex -n "wfr-0[2,4]"`
```json
{
    "action": "delete",
    "preview": false,
    "results": [
        {
            "name": "wfr-02",
            "result": "succeeded"
        },
        {
            "name": "wfr-04",
            "result": "succeeded"
        }
    ]
}
```

`$ ./dwsutil.py --operation list`
```json
{
    "wfrs": [
        "wfr-01",
        "wfr-03",
        "wfr-05"
    ]
}
```

`$ ./dwsutil.py --operation delete --regex -n "wfr-.*"`
```json
{
    "action": "delete",
    "preview": false,
    "results": [
        {
            "name": "wfr-01",
            "result": "succeeded"
        },
        {
            "name": "wfr-03",
            "result": "succeeded"
        },
        {
            "name": "wfr-05",
            "result": "succeeded"
        }
    ]
}
```

`$ ./dwsutil.py --operation list`
```json
{
    "wfrs": []
}
```

**Display cluster inventory with compute names munged**
NOTE: In some of the earlier versions, non-unique compute names are implemented.  Use the --mungecompute arg to overcome if so desired.
```
$ ./dwsutil.py --context inventory --operation show --mungecompute
```
```json
{
    "nnfnodes": [
        {
            "capacity": 37383395344384,
            "computes": [
                {
                    "health": "OK",
                    "id": "0",
                    "name": "Rabbit",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "1",
                    "name": "kind-worker-Compute-0",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "2",
                    "name": "kind-worker-Compute-1",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "3",
                    "name": "kind-worker-Compute-2",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "4",
                    "name": "kind-worker-Compute-3",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "5",
                    "name": "kind-worker-Compute-4",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "6",
                    "name": "kind-worker-Compute-5",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "7",
                    "name": "kind-worker-Compute-6",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "8",
                    "name": "kind-worker-Compute-7",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "9",
                    "name": "kind-worker-Compute-8",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "10",
                    "name": "kind-worker-Compute-9",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "11",
                    "name": "kind-worker-Compute-10",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "12",
                    "name": "kind-worker-Compute-11",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "13",
                    "name": "kind-worker-Compute-12",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "14",
                    "name": "kind-worker-Compute-13",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "15",
                    "name": "kind-worker-Compute-14",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "16",
                    "name": "kind-worker-Compute-15",
                    "status": "Ready"
                }
            ],
            "name": "kind-worker",
            "status": "Ready"
        },
        {
            "capacity": 37378395406336,
            "computes": [
                {
                    "health": "OK",
                    "id": "0",
                    "name": "Rabbit",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "1",
                    "name": "kind-worker2-Compute-0",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "2",
                    "name": "kind-worker2-Compute-1",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "3",
                    "name": "kind-worker2-Compute-2",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "4",
                    "name": "kind-worker2-Compute-3",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "5",
                    "name": "kind-worker2-Compute-4",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "6",
                    "name": "kind-worker2-Compute-5",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "7",
                    "name": "kind-worker2-Compute-6",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "8",
                    "name": "kind-worker2-Compute-7",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "9",
                    "name": "kind-worker2-Compute-8",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "10",
                    "name": "kind-worker2-Compute-9",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "11",
                    "name": "kind-worker2-Compute-10",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "12",
                    "name": "kind-worker2-Compute-11",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "13",
                    "name": "kind-worker2-Compute-12",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "14",
                    "name": "kind-worker2-Compute-13",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "15",
                    "name": "kind-worker2-Compute-14",
                    "status": "Ready"
                },
                {
                    "health": "OK",
                    "id": "16",
                    "name": "kind-worker2-Compute-15",
                    "status": "Ready"
                }
            ],
            "name": "kind-worker2",
            "status": "Ready"
        }
    ],
    "source": "Cluster-http://192.168.100.12:8080"
}
```
**Investigate overall system configuration**
```
$ ./dwsutil.py --context system --operation investigate
```
```
Configuration
--------------------
DWS API Endpoint....: https://16.104.218.143:6443
config file.........: dwsutil.cfg                    ( Existing dwsutil.cfg )
K8S default.........: ../dwsutil-save/kube-dp1b.cfg:../dwsutil-save/kube-vm.cfg:/Users/billj/.kube/config:localdata/kube-dp0.cfg
Available contexts..: ['dp1b', 'kind-vm', 'kind-kind', 'dp0']
Using K8S context...: dp1b                           ( Default context )

HPE Manager Nodes
--------------------
rabbit-k8s-worker    Ready      labels: ['cray.nnf.manager:true', 'cray.wlm.manager:true'] taints: None

HPE Rabbit Nodes
--------------------
rabbit-node-0        Ready      labels: ['cray.nnf.node:true', 'cray.nnf.x-name:rabbit-node-0'] taints: ['cray.nnf.node NoSchedule:true']
rabbit-node-1        Ready      labels: ['cray.nnf.node:true', 'cray.nnf.x-name:rabbit-node-1'] taints: ['cray.nnf.node NoSchedule:true']

Other Nodes
--------------------
rabbit-k8s-master    Ready      labels: None taints: None

Pods
--------------------
cert-manager         cert-manager-5d7f97b46d-fs5h6                                Running         10.42.0.9
cert-manager         cert-manager-webhook-54754dcdfd-4tpjx                        Running         10.42.1.4
nnf-system           nnf-controller-manager-658d8c4b46-pgdxz                      Running         10.42.1.55
nnf-system           nnf-node-manager-kl6d6                                       Running         10.42.2.92
nnf-system           nnf-node-manager-c72fg                                       Running         10.42.3.83
dws-operator-system  dws-operator-controller-manager-57bf7c467d-z8bjp             Running         10.42.1.10

Custom Resource Definitions
--------------------------------------------------
computes.dws.cray.hpe.com
directivebreakdowns.dws.cray.hpe.com
dwdirectiverules.dws.cray.hpe.com
servers.dws.cray.hpe.com
storagepools.dws.cray.hpe.com
storages.dws.cray.hpe.com
workflows.dws.cray.hpe.com
nnfjobstorageinstances.nnf.cray.hpe.com
nnfnodes.nnf.cray.hpe.com
nnfnodestorages.nnf.cray.hpe.com
nnfstorages.nnf.cray.hpe.com

Summary
--------------------
Total nodes: 4
Total Rabbit nodes: 2
Total Manager nodes: 1
HPE custom resource definitions: 11
```

**Investigate a specific Workflow resource**
```
$ ./dwsutil.py --operation investigate -n wfr-20220202-1636
```
```
-------------------- Object: Workflow default.wfr-20220202-1636--------------------
{
    "apiVersion": "dws.cray.hpe.com/v1alpha1",
    "kind": "Workflow",
    "metadata": {
        "creationTimestamp": "2022-02-02T22:36:48Z",
        "generation": 11,
        "name": "wfr-20220202-1636",
        "namespace": "default",
        "resourceVersion": "5272024",
        "uid": "b68e2093-38f9-4abd-997e-1de2e6390396"
    },
    "spec": {
        "desiredState": "setup",
        "dwDirectives": [
            "#DW jobdw type=xfs capacity=5GB name=vm-test-1-raw"
        ],
        "jobID": 5555,
        "userID": 1001,
        "wlmID": "5f239bd8-30db-450b-8c2c-a1a7c8631a1a"
    },
    "status": {
        "computes": {
            "name": "wfr-20220202-1636",
            "namespace": "default"
        },
        "desiredStateChange": "2022-02-02T22:36:55.235048Z",
        "directiveBreakdowns": [
            {
                "name": "wfr-20220202-1636-0",
                "namespace": "default"
            }
        ],
        "drivers": [
            {
                "completeTime": "2022-02-02T22:36:48.442728Z",
                "completed": true,
                "driverID": "nnf",
                "dwdIndex": 0,
                "lastHB": 0,
                "taskID": "",
                "watchState": "proposal"
            },
            {
                "completeTime": "2022-02-02T22:36:55.281755Z",
                "completed": true,
                "driverID": "nnf",
                "dwdIndex": 0,
                "lastHB": 0,
                "taskID": "",
                "watchState": "setup"
            },
            {
                "completed": false,
                "driverID": "nnf",
                "dwdIndex": 0,
                "lastHB": 0,
                "taskID": "",
                "watchState": "pre_run"
            },
            {
                "completed": false,
                "driverID": "nnf",
                "dwdIndex": 0,
                "lastHB": 0,
                "taskID": "",
                "watchState": "post_run"
            },
            {
                "completed": false,
                "driverID": "nnf",
                "dwdIndex": 0,
                "lastHB": 0,
                "taskID": "",
                "watchState": "teardown"
            }
        ],
        "elapsedTimeLastState": "96.633ms",
        "message": "Workflow setup completed successfully",
        "ready": true,
        "readyChange": "2022-02-02T22:36:55.331681Z",
        "reason": "Completed",
        "state": "setup"
    }
}
-------------------- Object: computes default.wfr-20220202-1636 --------------------
{
    "apiVersion": "dws.cray.hpe.com/v1alpha1",
    "kind": "Computes",
    "metadata": {
        "creationTimestamp": "2022-02-02T22:36:48Z",
        "generation": 1,
        "name": "wfr-20220202-1636",
        "namespace": "default",
        "ownerReferences": [
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "blockOwnerDeletion": true,
                "controller": true,
                "kind": "Workflow",
                "name": "wfr-20220202-1636",
                "uid": "b68e2093-38f9-4abd-997e-1de2e6390396"
            }
        ],
        "resourceVersion": "5271982",
        "uid": "7fbaddcb-d0dd-4cfc-aad9-0dd0fb3bcbd0"
    }
}
-------------------- Object: directiveBreakdown default.wfr-20220202-1636-0 --------------------
{
    "apiVersion": "dws.cray.hpe.com/v1alpha1",
    "kind": "DirectiveBreakdown",
    "metadata": {
        "creationTimestamp": "2022-02-02T22:36:48Z",
        "generation": 1,
        "name": "wfr-20220202-1636-0",
        "namespace": "default",
        "ownerReferences": [
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "blockOwnerDeletion": true,
                "controller": true,
                "kind": "Workflow",
                "name": "wfr-20220202-1636",
                "uid": "b68e2093-38f9-4abd-997e-1de2e6390396"
            }
        ],
        "resourceVersion": "5271979",
        "uid": "d56ede8f-f1de-4f54-aed7-ed71be7babfc"
    },
    "spec": {
        "dwRecord": {
            "dwDirective": "#DW jobdw type=xfs capacity=5GB name=vm-test-1-raw",
            "dwDirectiveIndex": 0
        },
        "lifetime": "job",
        "name": "vm-test-1-raw",
        "type": "xfs"
    },
    "status": {
        "allocationSet": [
            {
                "allocationStrategy": "AllocatePerCompute",
                "constraints": {
                    "labels": [
                        "dws.cray.hpe.com/storage=Rabbit"
                    ]
                },
                "label": "xfs",
                "minimumCapacity": 5000000000
            }
        ],
        "ready": true,
        "servers": {
            "name": "wfr-20220202-1636-0",
            "namespace": "default"
        }
    }
}
-------------------- Object: Server default.wfr-20220202-1636-0 --------------------
{
    "apiVersion": "dws.cray.hpe.com/v1alpha1",
    "kind": "Servers",
    "metadata": {
        "creationTimestamp": "2022-02-02T22:36:48Z",
        "finalizers": [
            "nnf.cray.hpe.com/nnf-servers"
        ],
        "generation": 1,
        "name": "wfr-20220202-1636-0",
        "namespace": "default",
        "ownerReferences": [
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "blockOwnerDeletion": true,
                "controller": true,
                "kind": "DirectiveBreakdown",
                "name": "wfr-20220202-1636-0",
                "uid": "d56ede8f-f1de-4f54-aed7-ed71be7babfc"
            }
        ],
        "resourceVersion": "5271981",
        "uid": "9fd9f344-3549-463b-a2bc-ed48c2e4a2dd"
    },
    "spec": {},
    "status": {
        "lastUpdate": "2022-02-02T22:36:48.414713Z",
        "ready": false
    }
}

Objects evaluated
--------------------
Workflow             name : default.wfr-20220202-1636      owner: n/a                                           created: 2022-02-02T22:36:48Z
Computes             name : default.wfr-20220202-1636      owner: Workflow wfr-20220202-1636                    created: 2022-02-02T22:36:48Z
DirectiveBreakdowns  name : default.wfr-20220202-1636-0    owner: Workflow wfr-20220202-1636                    created: 2022-02-02T22:36:48Z
Server               name : default.wfr-20220202-1636-0    owner: DirectiveBreakdown wfr-20220202-1636-0        created: 2022-02-02T22:36:48Z

Missing objects
--------------------
No missing objects

Summary
--------------------
WORKFLOW: desiredState 'setup' has been achieved
WARNING: Workflow desiredState is 'setup' but no computes have been assigned
WARNING: Workflow desiredState is 'setup' but no servers have been assigned to 'wfr-20220202-1636-0'
```

## Error examples
**Querying a missing WFR**
`$ ./dwsutil.py --operation get -n wfr-bogus`
```json
{
    "dwserrorcode": 101,
    "error": true,
    "function": "Dws.py:wfr_get",
    "message": "Workflow Resource named 'wfr-bogus' was not found"
}
```
```
$ echo $?
101
```

`$ ./dwsutil.py --operation delete -n "wfr-batch-2"`
```json
{
    "action": "delete",
    "preview": false,
    "results": [
        {
            "message": "Workflow Resource named 'wfr-batch-2' must be in a state of 'teardown' to be deleted, current state is 'proposal'",
            "name": "wfr-batch-2",
            "result": "failed"
        }
    ]
}
```
```
$ echo $?
104
```

`$ ./dwsutil.py --operation delete -n "wfr-bogus"`
```json
{
    "action": "delete",
    "preview": false,
    "results": [
        {
            "message": "Workflow Resource named 'wfr-bogus' was not found",
            "name": "wfr-bogus",
            "result": "failed"
        }
    ]
}
```
```
$ echo $?
101
```

**Errors when multiple operations are occurring**
`$ ./dwsutil.py --operation delete --regex -n "wfr.*"`
```json
{
    "action": "delete",
    "preview": false,
    "results": [
        {
            "name": "wfr-batch-0",
            "result": "succeeded"
        },
        {
            "message": "Workflow Resource named 'wfr-batch-1' must be in a state of 'teardown' to be deleted, current state is 'proposal'",
            "name": "wfr-batch-1",
            "result": "failed"
        },
        {
            "message": "Workflow Resource named 'wfr-batch-2' must be in a state of 'teardown' to be deleted, current state is 'proposal'",
            "name": "wfr-batch-2",
            "result": "failed"
        },
        {
            "message": "Workflow Resource named 'wfr-batch-3' must be in a state of 'teardown' to be deleted, current state is 'proposal'",
            "name": "wfr-batch-3",
            "result": "failed"
        },
        {
            "message": "Workflow Resource named 'wfr-batch-4' must be in a state of 'teardown' to be deleted, current state is 'proposal'",
            "name": "wfr-batch-4",
            "result": "failed"
        }
    ]
}
```
```
$ echo $?
107
```

## Return values
---
0 - Operation completed successfully
!0 - Something failed

Specified returned error values:
- 100 - DWS_GENERAL - A general DWS / Kubernetes error occurred, inspect the resulting message
- 101 - DWS_NOTFOUND - The named object was not found
- 102 - DWS_ALREADY_EXISTS - An attempt to create an object was made for an object that already exists
- 103 - DWS_NOTREADY - An operation was attempted on an object that was not in a Ready state
- 104 - DWS_IMPROPERSTATE An operation was attempted on an object that was in the wrong state
- 105 - DWS_INCOMPLETE - An operation was attempted on an object that was missing components (e.g. DirectiveBreakdown missing)
- 106 - DWS_NO_INVENTORY - An operation that requires inventory was attempted when no inventory was present/available
- 107 - DWS_SOME_OPERATION_FAILED - An batch operation had at least 1 failure
- 500 - DWS_K8S_ERROR - An uncaught kubernetes error occurred, inspect the resulting message for more information

## Linting and Testing
---
DWS Utility was continually linted during development using flake8 for various PEP violations

Unit tests and code coverage have been implemented in DWSUtility.

To run a single unit test file:
```python3 -m unittest run tests/testArgs.py -v```

To run all unit tests with python3:
```python3 -m unittest discover -s tests/ -v```

To run all unit tests with make:
```make test```

To generate a code coverage report:
```make coveragereport```

To generate a code coverage html report:
```make coveragehtml```

To generate a code coverage html report and open in a browser (MacOS only )
```make showcoverage```