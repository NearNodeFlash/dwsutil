#
# Copyright 2021, 2022 Hewlett Packard Enterprise Development LP
# Other additional copyright holders may be indicated within.
#
# The entirety of this work is licensed under the Apache License,
# Version 2.0 (the "License"); you may not use this file except
# in compliance with the License.
#
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
# DWS unit tests

import random


class TestUtil(object):
    number_gen = None

    @classmethod
    def number_generator(cls):
        nbr = 0
        while True:
            nbr += 1
            yield nbr

    @classmethod
    def random_wfr(cls):
        wfr_name = f"test-wfr-{random.randrange(1000000)}"
        return wfr_name

    @classmethod
    def setUpClass(cls):
        # print("Setting up BaseTest class")
        TestUtil.number_gen = TestUtil.number_generator()

    # *********************************************
    # * Test JSON data
    # *********************************************
    ALLOC_JSON = {"label": "myalloc", "allocationStrategy": "allocateacrossservers", "minimumCapacity": 1000000, "constraints": {"colocation": ["test1"]}}

    BREAKDOWN_JSON = {
        "metadata": {
            "name": "mybreakdown"
        },
        "status": {
            "storage": {
                "allocationSets": [
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
                "reference": {
                    "kind": "Servers",
                    "name": "w-0",
                    "namespace": "default"
                }
            },
            "compute": {
                "constraints": {
                    "location": [
                        {
                            "type": "physical",
                            "reference": {
                                "kind": "Servers",
                                "name": "w-0",
                                "namespace": "default"
                            }
                        }
                    ]
                }
            },
            "ready": True
        }
    }

    BREAKDOWNNOSTORAGE_JSON = {
        "metadata": {
            "name": "mybreakdown"
        },
        "status": {
            "ready": False
        }
    }

    BREAKDOWNNOREFERENCE_JSON = {
        "metadata": {
            "name": "mybreakdown"
        },
        "status": {
            "storage": {
                "allocationSets": [
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
                ]
            },
            "ready": False
        }
    }

    BREAKDOWNNOCOMPUTE_JSON = {
        "metadata": {
            "name": "mybreakdown"
        },
        "status": {
            "storage": {
                "allocationSets": [
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
                "reference": {
                    "kind": "Servers",
                    "name": "w-0",
                    "namespace": "default"
                }
            },
            "ready": True
        }
    }


    NNFNODE_JSON = {
        "metadata": {
            "name": "mynnfnode",
            "namespace": "default"
        },
        "spec": {
            "name": "mynnfnode"
        },
        "status": {
            "status": "ready",
            "capacity": 1000000000,
            "servers": [
                {
                    "name": "nnfnode-01",
                    "namespace": "default"
                }
            ]
        }
    }

    NNFNODEBOGUSSERVERS_JSON = {
        "metadata": {
            "name": "mynnfnode",
            "namespace": "default"
        },
        "spec": {
            "name": "mynnfnode"
        },
        "status": {
            "status": "ready",
            "capacity": 1000000000,
            "servers": [
                {
                    "name": "Compute 1",
                    "namespace": "default"
                },
                {
                    "name": "Compute 1",
                    "namespace": "default"
                }
            ]
        }
    }

    NNFNODELIST_JSON = {
        "apiVersion": "nnf.cray.hpe.com/v1alpha1",
        "items": [
            {
                "apiVersion": "nnf.cray.hpe.com/v1alpha1",
                "kind": "NnfNode",
                "metadata": {
                    "name": "nnf-nlc",
                    "namespace": "kind-worker"
                },
                "spec": {
                    "name": "kind-worker",
                    "pod": "nnf-node-manager-htzxh",
                    "state": "Enable"
                },
                "status": {
                    "capacity": 39582418599936,
                    "health": "OK",
                    "servers": [
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
                        }
                    ],
                    "status": "Ready"
                }
            },
            {
                "apiVersion": "nnf.cray.hpe.com/v1alpha1",
                "kind": "NnfNode",
                "metadata": {
                    "name": "nnf-nlc",
                    "namespace": "kind-worker2"
                },
                "spec": {
                    "name": "kind-worker2",
                    "pod": "nnf-node-manager-ztbvh",
                    "state": "Enable"
                },
                "status": {
                    "capacity": 39582418599936,
                    "health": "OK",
                    "servers": [
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
                        }
                    ],
                    "status": "NotReady"
                }
            }
        ],
        "kind": "NnfNodeList",
        "metadata": {
            "continue": "",
            "resourceVersion": "28009099"
        }
    }

    STORAGE_JSON = {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "data": {
                    "access": {
                        "computes": [
                            {
                                "name": "Compute 0",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 1",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 2",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 3",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 4",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 5",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 6",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 7",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 8",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 9",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 10",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 11",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 12",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 13",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 14",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 15",
                                "status": "Ready"
                            }
                        ],
                        "protocol": "PCIe",
                        "servers": [
                            {
                                "name": "Rabbit",
                                "status": "Ready"
                            }
                        ]
                    },
                    "capacity": 39582418599936,
                    "status": "Ready",
                    "type": "NVMe"
                },
                "kind": "Storage",
                "metadata": {
                    "creationTimestamp": "2021-12-10T18:07:47Z",
                    "generation": 1,
                    "labels": {
                        "dws.cray.hpe.com/storage": "Rabbit"
                    },
                    "managedFields": [
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:data": {
                                    ".": {},
                                    "f:access": {
                                        ".": {},
                                        "f:computes": {},
                                        "f:protocol": {},
                                        "f:servers": {}
                                    },
                                    "f:capacity": {},
                                    "f:status": {},
                                    "f:type": {}
                                },
                                "f:metadata": {
                                    "f:labels": {
                                        ".": {},
                                        "f:dws.cray.hpe.com/storage": {}
                                    }
                                }
                            },
                            "manager": "manager",
                            "operation": "Update",
                            "time": "2021-12-10T18:07:47Z"
                        }
                    ],
                    "name": "kind-worker",
                    "namespace": "default",
                    "resourceVersion": "9505656",
                    "uid": "b1ab3cb0-d8f5-4f19-b703-a5c47a01b934"
                }
            }

    STORAGELIST_JSON = {
        "apiVersion": "v1",
        "items": [
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "data": {
                    "access": {
                        "computes": [
                            {
                                "name": "Compute 0",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 1",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 2",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 3",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 4",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 5",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 6",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 7",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 8",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 9",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 10",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 11",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 12",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 13",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 14",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 15",
                                "status": "Ready"
                            }
                        ],
                        "protocol": "PCIe",
                        "servers": [
                            {
                                "name": "Rabbit",
                                "status": "Ready"
                            }
                        ]
                    },
                    "capacity": 39582418599936,
                    "status": "Ready",
                    "type": "NVMe"
                },
                "kind": "Storage",
                "metadata": {
                    "creationTimestamp": "2021-12-10T18:07:47Z",
                    "generation": 1,
                    "labels": {
                        "dws.cray.hpe.com/storage": "Rabbit"
                    },
                    "managedFields": [
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:data": {
                                    ".": {},
                                    "f:access": {
                                        ".": {},
                                        "f:computes": {},
                                        "f:protocol": {},
                                        "f:servers": {}
                                    },
                                    "f:capacity": {},
                                    "f:status": {},
                                    "f:type": {}
                                },
                                "f:metadata": {
                                    "f:labels": {
                                        ".": {},
                                        "f:dws.cray.hpe.com/storage": {}
                                    }
                                }
                            },
                            "manager": "manager",
                            "operation": "Update",
                            "time": "2021-12-10T18:07:47Z"
                        }
                    ],
                    "name": "kind-worker",
                    "namespace": "default",
                    "resourceVersion": "9505656",
                    "uid": "b1ab3cb0-d8f5-4f19-b703-a5c47a01b934"
                }
            },
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "data": {
                    "access": {
                        "computes": [
                            {
                                "name": "Compute 0",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 1",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 2",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 3",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 4",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 5",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 6",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 7",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 8",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 9",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 10",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 11",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 12",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 13",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 14",
                                "status": "Ready"
                            },
                            {
                                "name": "Compute 15",
                                "status": "Ready"
                            }
                        ],
                        "protocol": "PCIe",
                        "servers": [
                            {
                                "name": "Rabbit",
                                "status": "Ready"
                            }
                        ]
                    },
                    "capacity": 39582418599936,
                    "status": "NotReady",
                    "type": "NVMe"
                },
                "kind": "Storage",
                "metadata": {
                    "creationTimestamp": "2021-12-10T18:07:47Z",
                    "generation": 1,
                    "labels": {
                        "dws.cray.hpe.com/storage": "Rabbit"
                    },
                    "managedFields": [
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:data": {
                                    ".": {},
                                    "f:access": {
                                        ".": {},
                                        "f:computes": {},
                                        "f:protocol": {},
                                        "f:servers": {}
                                    },
                                    "f:capacity": {},
                                    "f:status": {},
                                    "f:type": {}
                                },
                                "f:metadata": {
                                    "f:labels": {
                                        ".": {},
                                        "f:dws.cray.hpe.com/storage": {}
                                    }
                                }
                            },
                            "manager": "manager",
                            "operation": "Update",
                            "time": "2021-12-10T18:07:47Z"
                        }
                    ],
                    "name": "kind-worker2",
                    "namespace": "default",
                    "resourceVersion": "9505657",
                    "uid": "48c21cad-e69c-477a-9278-6c89ffba6ac2"
                }
            }
        ],
        "kind": "List",
        "metadata": {
            "resourceVersion": "",
            "selfLink": ""
        }
    }

    WFR_JSON = {
        "apiVersion": "dws.cray.hpe.com/v1alpha1",
        "kind": "Workflow",
        "metadata": {
            "creationTimestamp": "2021-12-10T22:41:25Z",
            "generation": 4,
            "name": "tst-wfr",
            "namespace": "default",
            "resourceVersion": "9588025",
            "uid": "95826066-8062-483c-bd84-bbe164a730bb",
            "managedFields": [
                {
                    "apiVersion": "dws.cray.hpe.com/v1alpha1"
                },
                {
                    "apiVersion": "dws.cray.hpe.com/v1alpha1"
                }
            ],
        },
        "spec": {
            "desiredState": "Proposal",
            "dwDirectives": [],
            "jobID": 0,
            "userID": 0,
            "groupID": 0,
            "wlmID": ""
        },
        "status": {
            "computes": {
                "name": "tst-wfr",
                "namespace": "default"
            },
            "directiveBreakdowns": [
                {
                    "name": "wfr-xf-01-0",
                    "namespace": "default"
                }
            ],
            "desiredStateChange": "2021-12-10T22:41:25.570049Z",
            "elapsedTimeLastState": "294.183ms",
            "message": "Workflow proposal completed successfully",
            "ready": True,
            "readyChange": "2021-12-10T22:41:25.864231Z",
            "reason": "Completed",
            "state": "Proposal"
        }
    }

    WFRLIST_JSON = {
        "apiVersion": "v1",
        "items": [
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "kind": "Workflow",
                "metadata": {
                    "creationTimestamp": "2021-12-10T22:41:25Z",
                    "generation": 4,
                    "managedFields": [
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:spec": {
                                    ".": {},
                                    "f:desiredState": {},
                                    "f:dwDirectives": {}
                                }
                            },
                            "manager": "OpenAPI-Generator",
                            "operation": "Update",
                            "time": "2021-12-10T22:41:24Z"
                        },
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:status": {
                                    "f:computes": {
                                        "f:name": {},
                                        "f:namespace": {}
                                    },
                                    "f:desiredStateChange": {},
                                    "f:elapsedTimeLastState": {},
                                    "f:message": {},
                                    "f:ready": {},
                                    "f:readyChange": {},
                                    "f:reason": {},
                                    "f:state": {}
                                }
                            },
                            "manager": "manager",
                            "operation": "Update",
                            "time": "2021-12-10T22:41:25Z"
                        }
                    ],
                    "name": "tst-wfr",
                    "namespace": "default",
                    "resourceVersion": "9588025",
                    "uid": "95826066-8062-483c-bd84-bbe164a730bb"
                },
                "spec": {
                    "desiredState": "Proposal",
                    "dwDirectives": [],
                    "jobID": 0,
                    "userID": 0,
                    "groupID": 0,
                    "wlmID": ""
                },
                "status": {
                    "computes": {
                        "name": "tst-wfr",
                        "namespace": "default"
                    },
                    "desiredStateChange": "2021-12-10T22:41:25.570049Z",
                    "elapsedTimeLastState": "294.183ms",
                    "message": "Workflow proposal completed successfully",
                    "ready": True,
                    "readyChange": "2021-12-10T22:41:25.864231Z",
                    "reason": "Completed",
                    "state": "Proposal"
                }
            },
            {
                "apiVersion": "dws.cray.hpe.com/v1alpha1",
                "kind": "Workflow",
                "metadata": {
                    "creationTimestamp": "2021-12-10T22:46:15Z",
                    "generation": 4,
                    "managedFields": [
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:spec": {
                                    ".": {},
                                    "f:desiredState": {},
                                    "f:dwDirectives": {}
                                }
                            },
                            "manager": "OpenAPI-Generator",
                            "operation": "Update",
                            "time": "2021-12-10T22:46:15Z"
                        },
                        {
                            "apiVersion": "dws.cray.hpe.com/v1alpha1",
                            "fieldsType": "FieldsV1",
                            "fieldsV1": {
                                "f:status": {
                                    "f:computes": {
                                        "f:name": {},
                                        "f:namespace": {}
                                    },
                                    "f:desiredStateChange": {},
                                    "f:elapsedTimeLastState": {},
                                    "f:message": {},
                                    "f:ready": {},
                                    "f:readyChange": {},
                                    "f:reason": {},
                                    "f:state": {}
                                }
                            },
                            "manager": "manager",
                            "operation": "Update",
                            "time": "2021-12-10T22:46:15Z"
                        }
                    ],
                    "name": "tst-wfr2",
                    "namespace": "default",
                    "resourceVersion": "9589486",
                    "uid": "b8ff72a7-9a3b-452b-9ea7-82ca162e94e7"
                },
                "spec": {
                    "desiredState": "Proposal",
                    "dwDirectives": [],
                    "jobID": 0,
                    "userID": 0,
                    "groupID": 0,
                    "wlmID": ""
                },
                "status": {
                    "computes": {
                        "name": "tst-wfr2",
                        "namespace": "default"
                    },
                    "desiredStateChange": "2021-12-10T22:46:15.628527Z",
                    "elapsedTimeLastState": "142.225ms",
                    "message": "Workflow proposal completed successfully",
                    "ready": True,
                    "readyChange": "2021-12-10T22:46:15.770752Z",
                    "reason": "Completed",
                    "state": "Proposal"
                }
            }
        ]
    }
