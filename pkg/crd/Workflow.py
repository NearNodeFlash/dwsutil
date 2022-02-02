# -----------------------------------------------------------------
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
import copy
from ..Console import Console


class Workflow:
    """Encapsulates the Workflow CR."""
    def body_template(wfrname, wlmId, jobId, userId, dwdirectives, desiredState="proposal", group="dws.cray.hpe.com", version="v1alpha1"):
        body = {
            "kind": "Workflow",
            "apiVersion": f"{group}/{version}",
            "metadata": {
                "name": wfrname
            },
            "spec": {
                "wlmID": wlmId,
                "jobID": jobId,
                "userID": userId,
                "desiredState": "proposal",
                "dwDirectives": dwdirectives
            }
        }

        return body

    def body_template_INVALID(wfrname, wlmId, jobId, userId, dwdirectives, desiredState="proposal", group="dws.cray.hpe.com", version="v1alpha1"):
        server_obj = f"{wfrname}-0"
        body = {
            "kind": "Workflow",
            "apiVersion": f"{group}/{version}",
            "metadata": {
                "name": wfrname
            },
            "spec": {
                "wlmID": wlmId,
                "jobID": jobId,
                "userID": userId,
                "desiredState": "proposal",
                "dwDirectives": dwdirectives
            },
            "status": {
                "computes": {
                    "name": wfrname,
                    "namespace": "default"
                },
                "desiredStateChange": "2022-01-26T22:27:57.080655Z",
                "directiveBreakdowns": [
                    {
                        "name": server_obj,
                        "namespace": "default"
                    }
                ],
                "drivers": [
                    {
                        "completeTime": "2022-01-26T22:27:31.389788Z",
                        "completed": True,
                        "driverID": "nnf",
                        "dwdIndex": 0,
                        "lastHB": 0,
                        "taskID": "",
                        "watchState": "proposal"
                    },
                    {
                        "completeTime": "2022-01-26T22:42:23.824622Z",
                        "completed": True,
                        "driverID": "nnf",
                        "dwdIndex": 0,
                        "lastHB": 0,
                        "taskID": "",
                        "watchState": "setup"
                    },
                    {
                        "completed": False,
                        "driverID": "nnf",
                        "dwdIndex": 0,
                        "lastHB": 0,
                        "taskID": "",
                        "watchState": "pre_run"
                    },
                    {
                        "completed": False,
                        "driverID": "nnf",
                        "dwdIndex": 0,
                        "lastHB": 0,
                        "taskID": "",
                        "watchState": "post_run"
                    },
                    {
                        "completed": False,
                        "driverID": "nnf",
                        "dwdIndex": 0,
                        "lastHB": 0,
                        "taskID": "",
                        "watchState": "teardown"
                    }
                ],
                "elapsedTimeLastState": "14m26.873268s",
                "message": "Workflow setup completed successfully",
                "ready": True,
                "readyChange": "2022-01-26T22:42:23.953923Z",
                "reason": "Completed",
                "state": "setup"
            }
        }

        return body

    def __init__(self, raw_wfr):
        with Console.trace_function():
            if not raw_wfr:
                raise RuntimeError("raw_wfr cannot be None")
            self._raw_wfr = copy.deepcopy(raw_wfr)

    @property
    def raw_wfr(self):
        """Returns the internal json for the Workflow."""
        return self._raw_wfr

    @raw_wfr.setter
    def raw_wfr(self, raw_wfr):
        """Setter for the internal Workflow json."""
        self._raw_wfr = copy.deepcopy(raw_wfr)

    @property
    def name(self):
        """Returns the Workflow name."""
        return self.raw_wfr['metadata']['name']

    @name.setter
    def name(self, name):
        """Returns the Workflow name."""
        self.raw_wfr['metadata']['name'] = name

    @property
    def namespace(self):
        """Returns the Workflow namespace."""
        return self.raw_wfr['metadata']['namespace']

    @property
    def desiredState(self):
        """Returns the Workflow desiredState."""
        return self.raw_wfr['spec']['desiredState']

    @property
    def state(self):
        """Returns the Workflow state."""
        if 'status' not in self.raw_wfr:
            return ""
        return self.raw_wfr['status']['state']

    @property
    def ready(self):
        """Returns the Workflow ready field."""
        if 'status' not in self.raw_wfr:
            return ""
        return self.raw_wfr['status']['ready']

    @property
    def reason(self):
        """Returns the Workflow reason field."""
        if 'status' not in self.raw_wfr or \
           'reason' not in self.raw_wfr['status']:
            return ""
        return self.raw_wfr['status']['reason']

    @property
    def message(self):
        """Returns the Workflow message field."""
        if 'status' not in self.raw_wfr:
            return ""
        if 'message' not in self.raw_wfr['status']:
            return ""

        return self.raw_wfr['status']['message']

    @property
    def dwDirectives(self):
        """Returns the Workflow dwDirective list."""
        return self.raw_wfr['spec']['dwDirectives']

    @property
    def jobID(self):
        """Returns the Workflow jobID field."""
        return self.raw_wfr['spec']['jobID']

    @property
    def wlmID(self):
        """Returns the Workflow wlmID field."""
        return self.raw_wfr['spec']['wlmID']

    @property
    def userID(self):
        return self.raw_wfr['spec']['userID']

    @property
    def directive_breakdown_names(self):
        """Returns the Workflow directiveBreakdowns list (of names)."""
        if 'status' not in self.raw_wfr or \
           'directiveBreakdowns' not in self.raw_wfr['status']:
            return []
        # print(self.raw_wfr['status']['directiveBreakdowns'])
        return self.raw_wfr['status']['directiveBreakdowns']

    @property
    def compute_obj_name(self):
        """Returns tuple containing Compute CR name and namespace."""
        if 'computes' not in self.raw_wfr['status']:
            return None
        # print(self.raw_wfr['status']['computes'])
        return [self.raw_wfr['status']['computes']['name'], self.raw_wfr['status']['computes']['namespace']]

    @property
    def apiVersion(self):
        """Returns the Workflow apiVersion."""
        versionString = self.raw_wfr['metadata']['managedFields'][0]['apiVersion']
        parts = versionString.split("/")
        return parts[1]

    @property
    def apiGroup(self):
        """Returns the Workflow apiGroup."""
        versionString = self.raw_wfr['metadata']['managedFields'][0]['apiVersion']
        parts = versionString.split("/")
        return parts[0]

    @property
    def is_ready(self):
        """True if ready='Ready' and desiredState=State."""
        return self.ready and (self.desiredState == self.state)

    def dump_summary(self, raw_output=False):
        """Dump object summary to console."""
        Console.output("-"*40)
        Console.output(f"WFR: {self.name}")
        if raw_output:  # pragma: no cover
            Console.output(self.raw_wfr)
        else:
            Console.output(f"     state: {self.state}")
            Console.output(f"     desiredState: {self.desiredState}")
            Console.output(f"     ready: {self.ready}")
            Console.output(f"     reason: {self.reason}")
            Console.output(f"     message: {self.message}")
            Console.output(f"     dwDirectives: {self.dwDirectives}")
            Console.output(f"     jobID: {self.jobID}")
            Console.output(f"     wlmID: {self.wlmID}")
            Console.output(f"     userID: {self.userID}")
            Console.output(
                f"     directiveBreakdownNames: {self.directive_breakdown_names}")
