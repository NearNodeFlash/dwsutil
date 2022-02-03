# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# DWS Utility main class
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
import sys
import yaml
import re
from functools import reduce
import queue

import kubernetes.config as k8s_config

from .Config import Config
from .Console import Console
from .Dws import DWS, DWSError
from .crd.Nnfnode import Nnfnode


class DWSUtility:
    """Contains the dwsutil base implementation."""

    def preamble(self, stage):
        """Outputs basic DWS Utility information to the console.

        Parameters
        ----------
        stage : stage in DWS Utility initialization
                   1 is pre-config
                   2 is post-config

        """
        if stage == 1:
            if self.config.show_version:
                Console.output(self.config.version_string,
                               output_timestamp=False)
                exit(0)

        if stage == 2:
            if self.config.showconfigonly \
               or Console.level_enabled(Console.WORDY):
                apic = k8s_config.kube_config.ApiClient()
                host = apic.configuration.host
                self.config.output_config_item("DWS API Endpoint", host)
                self.config.output_configuration()

    def command_line_args():
        return sys.argv

    def __init__(self, sim_folder):
        self.config = Config(DWSUtility.command_line_args())
        self.wfr_queue = queue.Queue()

    def dump_config_as_json(self):
        """Dump the current configuration to the console as json."""
        Console.debug(Console.WORDY, f"Configuration: {self.config.to_json()}")

    def do_list_storage(self):
        """Retrieve list of Storage CRs and dump to console."""
        storage_list = self.dws.storage_list_names()
        Console.pretty_json({"rabbits": storage_list})
        return 0

    def do_list_wfr(self):
        """Retrieve list of Workflow CRs and dump to console."""
        wfr_list = self.dws.wfr_list_names()
        Console.pretty_json({"wfrs": wfr_list})
        return 0

    def object_str(self, objtype, name, created="n/a", owner="n/a", not_found=False):
        width = 50
        spacer = " " * width
        if not_found:
            return(f"{(objtype+spacer)[:20]} name : {(name+spacer)[:30]} ** OBJECT NOT FOUND **")
        else:
            return(f"{(objtype+spacer)[:20]} name : {(name+spacer)[:30]} owner: {(owner+spacer)[:45]} created: {(created+spacer)[:20]}")

    def do_investigate_system(self):
        """Investigate the named workflow"""
        facts = []

        Console.output("\nConfiguration", output_timestamp=False)
        Console.output("-"*20, output_timestamp=False)
        tsp = Console.timestamp

        Console.timestamp = False
        apic = k8s_config.kube_config.ApiClient()
        host = apic.configuration.host
        self.config.output_config_item("DWS API Endpoint", host)
        self.config.output_configuration(init_flags_only=True)
        Console.timestamp = tsp

        # Evaluate nodes
        tsp = Console.timestamp
        node_count = 0
        rabbit_count = 0
        manager_count = 0
        notready_rabbit_count = 0
        notready_manager_count = 0
        rabbit_nodes = []
        manager_nodes = []
        other_nodes = []
        try:
            nodes = self.dws.node_list()
            for node in nodes.items:
                node_count += 1
                status = "unknown"
                for condition in node.status.conditions:
                    if condition.type == "Ready":
                        status = "Ready" if condition.status == 'True' else 'Not Ready'
                if status != "Ready":
                    facts.append(f"WARNING: Node '{node.metadata.name}'' is not ready")
                if node.metadata.labels and len(node.metadata.labels) > 0:
                    labels = str([f"{label}:{node.metadata.labels[label]}" for label in node.metadata.labels if label.startswith('cray')])
                    if labels == "[]":
                        labels = "None"
                else:
                    labels = "None"
                if node.spec.taints and len(node.spec.taints) > 0:
                    taints = str([f"{label.key} {label.effect}:{label.value}" for label in node.spec.taints])
                    if taints == "[]":
                        taints = "None"
                else:
                    taints = "None"

                is_manager = True if node.metadata.labels and 'cray.nnf.manager' in node.metadata.labels and node.metadata.labels['cray.nnf.manager'] == 'true' else False
                is_cray_node = True if node.metadata.labels and 'cray.nnf.node' in node.metadata.labels and node.metadata.labels['cray.nnf.node'] == 'true' else False
                is_no_schedule = node.spec.taints and len([t for t in node.spec.taints if t.key.startswith('cray') and t.effect == 'NoSchedule' and t.value == 'true']) > 0
                node_str = f"{(node.metadata.name + ' '*20)[:20]} {(status+' '*5)[:10]} labels: {labels} taints: {taints}"

                if is_manager:
                    manager_count += 1
                    manager_nodes.append(node_str)
                    if status != "Ready":
                        notready_manager_count += 1
                elif is_cray_node:
                    rabbit_count += 1
                    rabbit_nodes.append(node_str)
                    if not is_no_schedule:
                        facts.append(f"WARNING: Rabbit node {node.metadata.name} does not have the NoSchedule taint")
                    if status != "Ready":
                        notready_rabbit_count += 1
                else:
                    other_nodes.append(node_str)

            Console.output("\nHPE Manager Nodes", output_timestamp=False)
            Console.output("-"*20, output_timestamp=False)
            if len(manager_nodes) == 0:
                Console.output("None", output_timestamp=False)
                facts.append("WARNING: No HPE manager nodes are present")
            else:
                for node in manager_nodes:
                    Console.output(node, output_timestamp=False)

            Console.output("\nHPE Rabbit Nodes", output_timestamp=False)
            Console.output("-"*20, output_timestamp=False)
            if len(rabbit_nodes) == 0:
                Console.output("None", output_timestamp=False)
                facts.append("WARNING: No HPE rabbit nodes are present")
            else:
                for node in rabbit_nodes:
                    Console.output(node, output_timestamp=False)

            Console.output("\nOther Nodes", output_timestamp=False)
            Console.output("-"*20, output_timestamp=False)
            if len(other_nodes) == 0:
                Console.output("None", output_timestamp=False)
                # Not sure if this should be a warning.
                facts.append("WARNING: No other nodes are present")
            else:
                for node in other_nodes:
                    Console.output(node, output_timestamp=False)

            if node_count == 0:
                facts.append("WARNING: There are no nodes in the system")
            if manager_count == 0:
                facts.append("WARNING: There are no Manager nodes in the system")
            if rabbit_count == 0:
                facts.append("WARNING: There are no Rabbit nodes in the system")
            if notready_manager_count > 0:
                facts.append(f"WARNING: There are {notready_manager_count} Manager nodes that are not ready")
            if notready_rabbit_count > 0:
                facts.append(f"WARNING: There are {notready_rabbit_count} Rabbit nodes that are not ready")

            facts.append(f"Total nodes: {node_count}")
            facts.append(f"Total Rabbit nodes: {rabbit_count}")
            facts.append(f"Total Manager nodes: {manager_count}")

        except DWSError as ex:
            Console.output(ex.message, output_timestamp=False)
            return ex.code

        # Evaluate pods
        Console.output("\nPods", output_timestamp=False)
        Console.output("-"*20, output_timestamp=False)
        dws_operator_count = 0
        nnf_controller_manager_count = 0
        nnf_node_manager_count = 0
        cert_manager_count = 0
        cert_manager_webhook_count = 0
        notready_dws_operator_count = 0
        notready_nnf_controller_manager_count = 0
        notready_nnf_node_manager_count = 0
        notready_cert_manager_count = 0
        notready_cert_manager_webhook_count = 0

        pods = self.dws.pods_list()
        for pod in pods.items:
            report_pod = False
            if pod.metadata.name.startswith("dws-operator-controller-manager"):
                dws_operator_count += 1
                report_pod = True
                if pod.status.phase != "Running":
                    notready_dws_operator_count += 1
            if pod.metadata.name.startswith("nnf-controller-manager"):
                nnf_controller_manager_count += 1
                report_pod = True
                if pod.status.phase != "Running":
                    notready_nnf_controller_manager_count += 1
            if pod.metadata.name.startswith("nnf-node-manager"):
                nnf_node_manager_count += 1
                report_pod = True
                if pod.status.phase != "Running":
                    notready_nnf_node_manager_count += 1

            if pod.metadata.namespace == 'cert-manager':
                if 'app' in pod.metadata.labels:
                    if pod.metadata.labels['app'] == 'cert-manager':
                        cert_manager_count += 1
                        report_pod = True
                        if pod.status.phase != "Running":
                            notready_cert_manager_count += 1
                    if pod.metadata.labels['app'] == 'webhook':
                        cert_manager_webhook_count += 1
                        report_pod = True
                        if pod.status.phase != "Running":
                            notready_cert_manager_webhook_count += 1
            if report_pod:
                Console.output(f"{(pod.metadata.namespace+' '*20)[:20]} {(pod.metadata.name+' '*50)[:60]} {(pod.status.phase+' '*10)[:15]} {pod.status.pod_ip}", output_timestamp=False)

        # Evaluate pods
        Console.output("\nCustom Resource Definitions", output_timestamp=False)
        Console.output("-"*50, output_timestamp=False)
        crd_count = 0
        # NOTE: Any added/deleted CRDs need to be reflect in this list
        hpe_crds = [
            "computes.dws.cray.hpe.com",
            "directivebreakdowns.dws.cray.hpe.com",
            "dwdirectiverules.dws.cray.hpe.com",
            "servers.dws.cray.hpe.com",
            "storagepools.dws.cray.hpe.com",
            "storages.dws.cray.hpe.com",
            "workflows.dws.cray.hpe.com",
            "nnfjobstorageinstances.nnf.cray.hpe.com",
            "nnfnodes.nnf.cray.hpe.com",
            "nnfnodestorages.nnf.cray.hpe.com",
            "nnfstorages.nnf.cray.hpe.com"
        ]
        crds = self.dws.crd_list()
        for crd in crds.items:
            if "hpe.com" in crd.metadata.name:
                hpe_crds.remove(crd.metadata.name)
                crd_count += 1
                Console.output(crd.metadata.name, output_timestamp=False)

        for crd in hpe_crds:
            facts.append(f"WARNING: HPE custom resource definition '{crd}' does not exist in the system")

        facts.append(f"HPE custom resource definitions: {crd_count}")
        # Dump summary of investigation
        Console.output("\nSummary", output_timestamp=False)
        Console.output("-"*20, output_timestamp=False)
        if len(facts) == 0:
            Console.output("Nothing to report", output_timestamp=False)
        else:
            for fact in list(filter(lambda x: not x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
            for fact in list(filter(lambda x: x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
        return 0

    def do_investigate_wfr(self):
        """Investigate the named workflow"""
        facts = []
        objects = []
        expected_but_missing = []
        assign_expected = True

        # Dump out the workflow
        try:
            wfr = self.dws.crd_get_raw("workflows", self.config.wfr_name)
            objects.append(self.object_str("Workflow", f"{wfr['metadata']['namespace']}.{wfr['metadata']['name']}", f"{wfr['metadata']['creationTimestamp']}"))
            wfr["metadata"].pop("managedFields")
            Console.output(f"{'-'*20} Object: Workflow default.{wfr['metadata']['name']}{'-'*20}", output_timestamp=False)
            Console.pretty_json(wfr)

            if "metadata" not in wfr:
                Console.error("Workflow does not contain a metadata section", output_timestamp=False)
                return -1

            if "spec" not in wfr:
                Console.error("Workflow does not contain a spec section", output_timestamp=False)
                return -1

            if "status" not in wfr:
                Console.error("Workflow does not contain a status section", output_timestamp=False)
                return -1

        except DWSError as ex:
            Console.output(ex.message, output_timestamp=False)
            return ex.code

        if wfr["spec"]["desiredState"] == "proposal":
            assign_expected = False

        if wfr["spec"]["desiredState"] == wfr["status"]["state"]:
            facts.append(f"WORKFLOW: desiredState '{wfr['spec']['desiredState']}' has been achieved")
            if not wfr["status"]["ready"]:
                facts.append("WARNING: Workflow ready field IS FALSE")
        else:
            facts.append(f"WORKFLOW: desiredState '{wfr['spec']['desiredState']}' has NOT been achieved")
            if wfr["status"]["ready"]:
                facts.append("WARNING: Workflow ready field IS TRUE")
        if "dwDirectives" not in wfr["spec"]:
            facts.append("WARNING: No dwDirectives field in spec")
        elif len(wfr["spec"]["dwDirectives"]) < 1:
            facts.append("WARNING: No datawarp directives in this workflow")

        # Collect and dump the computes
        try:
            computes = self.dws.crd_get_raw("computes", self.config.wfr_name, "default")
            if len(computes['metadata']['ownerReferences']) > 0:
                objects.append(self.object_str("Computes", f"{computes['metadata']['namespace']}.{computes['metadata']['name']}", f"{computes['metadata']['creationTimestamp']}", f"{computes['metadata']['ownerReferences'][0]['kind']} {computes['metadata']['ownerReferences'][0]['name']}"))
            else:
                objects.append(self.object_str("Computes", f"{computes['metadata']['namespace']}.{computes['metadata']['name']}", f"{computes['metadata']['creationTimestamp']}", "<absent>"))
            computes["metadata"].pop("managedFields")
            Console.output(f"{'-'*20} Object: computes default.{computes['metadata']['name']} {'-'*20}", output_timestamp=False)
            Console.pretty_json(computes)
            if 'data' in computes and len(computes['data']) > 0:
                facts.append("WORKFLOW: Computes have been assigned")
            elif assign_expected:
                facts.append(f"WARNING: Workflow desiredState is '{wfr['spec']['desiredState']}' but no computes have been assigned")
        except DWSError as ex:
            objects.append(self.object_str("Computes", f"default.{self.config.wfr_name}", not_found=True))
            expected_but_missing.append(f"default.computes.{self.config.wfr_name}")
            facts.append(f"WARNING: {ex.message}")

        # Collect and dump the breakdowns
        for bd in wfr["status"]["directiveBreakdowns"]:
            bdname = bd['name']
            bdnamespace = bd['namespace']
            try:
                breakdown = self.dws.crd_get_raw("directivebreakdowns", bdname, bdnamespace)
                if len(breakdown['metadata']['ownerReferences']) > 0:
                    objects.append(self.object_str("DirectiveBreakdowns", f"{bdnamespace}.{bdname}", f"{breakdown['metadata']['creationTimestamp']}", f"{breakdown['metadata']['ownerReferences'][0]['kind']} {breakdown['metadata']['ownerReferences'][0]['name']}"))
                else:
                    objects.append(self.object_str("DirectiveBreakdowns", f"{bdnamespace}.{bdname}", f"{breakdown['metadata']['creationTimestamp']}"))
                breakdown["metadata"].pop("managedFields")
                Console.output(f"{'-'*20} Object: directiveBreakdown {bdnamespace}.{bdname} {'-'*20}", output_timestamp=False)
                Console.pretty_json(breakdown)

                # Dump out servers for this breakdown
                if 'servers' not in breakdown['status']:
                    if assign_expected:
                        facts.append(f"WARNING: Workflow desiredState is '{wfr['spec']['desiredState']}' but no servers have been assigned")
                    else:
                        facts.append(f"DirectiveBreakdown: {bdname} does not have a servers element")
                else:
                    servers = breakdown['status']['servers']
                    svrname = servers['name']
                    svrnamespace = servers['namespace']
                    try:
                        server = self.dws.crd_get_raw("servers", svrname, svrnamespace)
                        if len(server['metadata']['ownerReferences']) > 0:
                            objects.append(self.object_str("Server", f"{svrnamespace}.{svrname}", f"{server['metadata']['creationTimestamp']}", f"{server['metadata']['ownerReferences'][0]['kind']} {server['metadata']['ownerReferences'][0]['name']}"))
                        else:
                            objects.append(self.object_str("Server", f"{svrnamespace}.{svrname}", f"{server['metadata']['creationTimestamp']}"))
                        if 'allocationSets' in server['status']:
                            facts.append(f"WORKFLOW: Servers have been assigned to '{bdname}'")
                        elif assign_expected:
                            facts.append(f"WARNING: Workflow desiredState is '{wfr['spec']['desiredState']}' but no servers have been assigned to '{bdname}'")
                        server["metadata"].pop("managedFields")
                        Console.output(f"{'-'*20} Object: Server {svrnamespace}.{svrname} {'-'*20}", output_timestamp=False)
                        Console.pretty_json(server)
                    except DWSError as ex:
                        objects.append(self.object_str("Servers", f"{svrnamespace}.{svrname}", not_found=True))
                        expected_but_missing.append(f"{svrnamespace}.directivebreakdowns.{svrname}")
                        objects.append(f"Servers: {svrnamespace}.{svrname} - NOT FOUND")
                        facts.append(f"WARNING: {ex.message}")
            except DWSError as ex:
                objects.append(self.object_str("DirectiveBreakdowns", f"{bdnamespace}.{bdname}", not_found=True))
                expected_but_missing.append(f"{bdnamespace}.directivebreakdowns.{bdname}")
                facts.append(f"WARNING: {ex.message}")

        # Dump summary of investigation
        Console.output("\nObjects evaluated", output_timestamp=False)
        Console.output("-"*20, output_timestamp=False)
        for obj in objects:
            Console.output(obj, output_timestamp=False)

        Console.output("\nMissing objects", output_timestamp=False)
        Console.output("-"*20, output_timestamp=False)
        if len(expected_but_missing) < 1:
            Console.output("No missing objects", output_timestamp=False)
        else:
            for obj in expected_but_missing:
                Console.output(obj, output_timestamp=False)

        Console.output("\nSummary", output_timestamp=False)
        Console.output("-"*20, output_timestamp=False)
        if len(facts) == 0:
            Console.output("Nothing to report", output_timestamp=False)
        else:
            for fact in list(filter(lambda x: not x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
            for fact in list(filter(lambda x: x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
        return 0

    def do_get_wfr(self, name):
        """Retrieve specified Workflow CR and dump to console."""
        wfr = self.dws.wfr_get(name)
        Console.pretty_json({"name": wfr.name,
                             "state": wfr.state,
                             "desiredState": wfr.desiredState,
                             "ready": wfr.ready})
        return 0

    def do_delete_wfr(self, name):
        """Delete specified CRs."""
        wfr_list = []
        delete_results = []
        dws_error_code = 0
        if self.config.regexEnabled:
            Console.debug(Console.MIN, f"Deleting wfrs matching '{name}'")

            regex = f"^{name}$"
            for wfr_name in self.dws.wfr_list_names():
                if re.match(regex, wfr_name):
                    wfr_list.append(wfr_name)
        else:
            Console.debug(Console.MIN, f"Deleting wfr with name '{name}")
            wfr_list.append(name)

        for wfr_name in wfr_list:
            try:
                if not self.config.preview:
                    self.dws.wfr_delete(wfr_name)
                else:
                    Console.debug(Console.MIN, f"Preview mode: WFR {wfr_name} not deleted")

                delete_results.append({"name": wfr_name,
                                       "result": "succeeded"})
            except DWSError as ex:
                delete_results.append({"name": wfr_name,
                                       "result": "failed",
                                       "message": ex.message})
                dws_error_code = ex.code
        Console.pretty_json({"action": "delete",
                             "preview": self.config.preview,
                             "results": delete_results})

        if len(wfr_list) > 1 and dws_error_code != 0:
            dws_error_code = DWSError.DWS_SOME_OPERATION_FAILED

        return dws_error_code

    def do_progress_wfr(self, fail_from_teardown=False):
        """Progress specified Workflow CRs."""
        wfr_list = []
        results = []
        dws_error_code = 0
        if self.config.regexEnabled:
            Console.debug(Console.MIN, f"Progressing wfrs matching"
                                       f" '{self.config.wfr_name}' regex")

            regex = f"^{self.config.wfr_name}$"
            for wfr_name in self.dws.wfr_list_names():
                if re.match(regex, wfr_name):
                    wfr_list.append(wfr_name)
        else:
            Console.debug(Console.MIN, f"Progressing '{self.config.wfr_name}")
            wfr_list.append(self.config.wfr_name)

        for wfr_name in wfr_list:
            try:
                if wfr_name is None or wfr_name.strip() == '':
                    results.append({"name": "",
                                    "result": "failed",
                                    "message": "Workflow name missing"})
                    continue
                wfr = self.dws.wfr_get(wfr_name)
                desiredState = self.dws.wfr_get_next_state(wfr.state)
                if desiredState is None:
                    if wfr.state == "teardown" and not fail_from_teardown:
                        results.append({"name": wfr_name,
                                        "result": "succeeded",
                                        "message": f"Workflow '{wfr_name}'"
                                        " has achieved 'teardown'"})
                    else:
                        results.append({"name": wfr_name,
                                        "result": "failed",
                                        "message": f"Workflow '{wfr_name}'"
                                        " cannot be progressed from"
                                        f" '{wfr.state}'"})
                else:
                    Console.debug(Console.MIN, f"Progressing WFR {wfr.name}"
                                  f" from {wfr.state} to {desiredState}")
                    if not self.config.preview:
                        self.dws.wfr_update_desired_state(wfr_name, desiredState)
                    else:
                        Console.debug(Console.MIN, f"Preview mode: WFR {wfr_name} not progressed")

                    results.append({"name": wfr_name,
                                    "result": "succeeded",
                                    "message": f"Workflow '{wfr_name}'"
                                    f" progressed from '{wfr.state}' to"
                                    f" '{desiredState}'"})
            except DWSError as ex:
                results.append({"name": wfr_name,
                                "result": "failed",
                                "message": ex.message})
                dws_error_code = ex.code

        Console.pretty_json({"action": "progress", "preview": self.config.preview, "results": results})

        if len(wfr_list) > 1 and dws_error_code != 0:
            dws_error_code = DWSError.DWS_SOME_OPERATION_FAILED

        return dws_error_code

    def do_progressteardown_wfr(self, fail_from_teardown=False):
        """Progress specified Workflow CRs to teardown desiredState."""
        wfr_list = []
        results = []
        dws_error_code = 0
        if self.config.regexEnabled:
            Console.debug(Console.MIN, f"Progressing wfrs matching"
                                       f" '{self.config.wfr_name}' regex")

            regex = f"^{self.config.wfr_name}$"
            for wfr_name in self.dws.wfr_list_names():
                if re.match(regex, wfr_name):
                    wfr_list.append(wfr_name)
        else:
            Console.debug(Console.MIN, f"Progressing '{self.config.wfr_name}")
            wfr_list.append(self.config.wfr_name)

        for wfr_name in wfr_list:
            try:
                wfr = self.dws.wfr_get(wfr_name)
                desiredState = "teardown"
                Console.debug(Console.MIN, f"Progressing WFR {wfr.name}"
                              f" from {wfr.state} to {desiredState}")
                if not self.config.preview:
                    self.dws.wfr_update_desired_state(wfr_name, desiredState, force_update=True)
                else:
                    Console.debug(Console.MIN, f"Preview mode: WFR {wfr_name} not progressed to teardown")
                results.append({"name": wfr_name,
                                "result": "succeeded",
                                "message": f"Workflow '{wfr_name}'"
                                f" progressed from '{wfr.state}' to"
                                f" '{desiredState}'"})
            except DWSError as ex:
                results.append({"name": wfr_name,
                                "result": "failed",
                                "message": ex.message})
                dws_error_code = ex.code
        Console.pretty_json({"action": "progressteardown", "preview": self.config.preview, "results": results})

        if len(wfr_list) > 1 and dws_error_code != 0:
            dws_error_code = DWSError.DWS_SOME_OPERATION_FAILED

        return dws_error_code

    def do_create_wfr(self):
        """Create a Workflow CR."""
        results = []
        wfr_name = ""
        dws_error_code = 0
        for iteration in range(self.config.operation_count):
            if self.config.operation_count == 1:
                wfr_name = self.config.wfr_name
            else:
                wfr_name = self.config.wfr_name+"-"+str(iteration)
            try:
                if not self.config.preview:
                    self.dws.wfr_create(wfr_name,
                                        self.config.dwdirectives,
                                        self.config.user_id,
                                        self.config.wlm_id,
                                        self.config.job_id)
                else:
                    Console.debug(Console.MIN, f"Preview mode: WFR {wfr_name} not created")
                results.append({"name": wfr_name,
                                "result": "succeeded",
                                "message": f"Workflow '{wfr_name} created"})
            except DWSError as ex:
                results.append({"name": wfr_name, "result": "failed", "message": ex.message})
                dws_error_code = ex.code

        Console.pretty_json({"action": "create", "preview": self.config.preview, "results": results})

        if len(results) > 1 and dws_error_code != 0:
            dws_error_code = DWSError.DWS_SOME_OPERATION_FAILED

        return dws_error_code

    def do_load_inventory_file(self, only_ready_nodes=False):
        """Load system inventory from YAML file.
           Parameters:
           only_ready_nodes : When True, ignore nodes that are not Ready

           Returns:
           Inventory dictionary
        """
        Console.debug(Console.MIN, "Loading inventory file"
                                   f" {self.config.inventory_file}")
        with open(self.config.inventory_file, "r") as stream:
            nnf_inventory = {}
            inventory_data = yaml.safe_load(stream)
            if 'system' not in inventory_data:
                raise Exception("'system' is missing from the file")
            else:
                if 'nnf-nodes' not in inventory_data['system']:
                    Console.output("'nnf-nodes:' array missing from file")
                else:
                    for node in inventory_data['system']['nnf-nodes']:
                        node_obj = Nnfnode(node, allow_compute_name_munge=self.config.compute_munge)
                        Console.debug(Console.MIN, "...Processing nnf-node"
                                                   f" '{node_obj.name}'")
                        Console.debug(Console.WORDY, "......computes:"
                                                     f" {node_obj.computes}")
                        if only_ready_nodes and not node_obj.is_ready:
                            Console.debug(Console.MIN, "...nnf-node is not"
                                                       " ready, skipping")
                            continue

                        if node_obj.name in nnf_inventory:
                            raise Exception(f"Duplicate nnf name "
                                            f"'{node_obj.name} found in file")
                        nnf_inventory[node_obj.name] = node_obj
            return nnf_inventory

    def do_get_inventory(self, only_ready_nodes=False):
        """Returns inventory dictionary from file if inventory file has been
           specified, otherwise pulls the inventory from the cluster.

           Parameters:
           only_ready_nodes : When True, ignore nodes that are not Ready

           Returns:
           Inventory dictionary
        """
        if self.config.inventory_file is not None:
            return self.do_load_inventory_file(only_ready_nodes), f"File-{self.config.inventory_file}"
        source = "Cluster"
        try:
            apic = k8s_config.kube_config.ApiClient()
            source = f"Cluster-{apic.configuration.host}"
        except Exception:
            pass
        return self.dws.inventory_build_from_cluster(only_ready_nodes, self.config.compute_munge), source

    def do_assign_resources(self):
        """Assign server and compute resources to the specified Workflow CR."""
        assign_results = []
        computes = []
        selected_computes = {}
        selected_rabbits = {}
        rabbits, source = self.do_get_inventory(only_ready_nodes=True)
        if len(rabbits) < 1:
            msg = f"Inventory from {source} does not contain any nnf nodes that can be assigned"
            raise DWSError(msg, DWSError.DWS_NO_INVENTORY)

        # Build a master dict of computes that could be assigned
        for node_name, node in rabbits.items():
            if node.name.strip().lower() in self.config.exclude_rabbits:
                Console.debug(Console.MIN, f"Excluding nnf node {node.name}")
                continue

            for c in node.computes:
                if c['name'].strip().lower() in self.config.exclude_computes:
                    Console.debug(Console.MIN, f"Excluding compute node {c['name']}")
                    continue

                compute = {"storageName": node.name,
                           "computeName": c['name'],
                           "computeStatus": c['status']}
                computes.append(compute)

        if len(computes) < self.config.nodes:
            msg = f"There are only {len(computes)} compute nodes available, however {self.config.nodes} computes has been specified."
            raise DWSError(msg, DWSError.DWS_INCOMPLETE)

        Console.debug(Console.WORDY, "Retrieving workflow"
                                     f" {self.config.wfr_name}")
        wfr = self.dws.wfr_get(self.config.wfr_name)

        breakdowns = self.dws.wfr_get_directiveBreakdowns(wfr)
        if len(breakdowns) == 0:
            msg = f"Workflow Resource named '{wfr.name}' has no directive breakdowns"
            raise DWSError(msg, DWSError.DWS_INCOMPLETE)

        for breakdown in breakdowns:
            Console.debug(Console.WORDY, Console.FULL_BAR)
            Console.debug(Console.WORDY, f"Breakdown {breakdown.name}")
            allocations = breakdown.allocationSet
            for alloc in allocations:
                if alloc.is_across_servers:
                    pass
                elif alloc.is_single_server:
                    pass
                elif alloc.is_per_compute:

                    # Check to make sure that we have enough remaining capacity for these allocations
                    allocs_available = reduce(lambda x, y: x+y,
                                              [r.allocs_remaining(alloc.minimumCapacity) for k, r in rabbits.items()]
                                              )
                    if allocs_available < self.config.nodes:
                        msg = f"Insufficient space remains across rabbits.  " \
                              f"Only {allocs_available} allocations "  \
                              f"exist, however {self.config.nodes} are " \
                              "required."
                        raise DWSError(msg, DWSError.DWS_GENERAL)

                    # Choose computes and rabbits
                    for c in computes:
                        rabbit_name = c["storageName"]
                        r = rabbits[rabbit_name]

                        if c["computeStatus"] != "Ready":
                            Console.debug(Console.MIN,
                                          f"...compute {c['computeName']} is"
                                          " not ready and will be skipped")
                            continue

                        # Composite key protects against duplicates
                        if r.has_sufficient_capacity(alloc.minimumCapacity):
                            compute_key = f"{rabbit_name}-{c['computeName']}"
                            selected_computes[compute_key] = c
                            selected_rabbits[r.name] = r
                            r.remaining_storage -= alloc.minimumCapacity
                            r.allocationCount += 1
                        else:
                            Console.debug(Console.MIN,
                                          f"...rabbit {rabbit_name} has"
                                          " insufficient storage")

                        if len(selected_computes) == self.config.nodes:
                            Console.debug(Console.MIN, f"{self.config.nodes}"
                                          " computes successfully selected")
                            break

                    if len(selected_computes) != self.config.nodes:
                        raise(Exception(
                            "There are not enough compute nodes in a ready"
                            f" state to meet the required node count of"
                            f" {self.config.nodes}"))

                    Console.debug(Console.WORDY, "compute object name:"
                                                 f" {wfr.compute_obj_name}")

                    node_list = [selected_computes[c]['computeName']
                                 for c in selected_computes]

                    Console.debug(Console.MIN, f"{self.config.nodes}"
                                  f" compute(s) to be assigned: {node_list}")
                    Console.debug(Console.MIN, f"{self.config.nodes}"
                                  " nnfnode(s) to be assigned: "
                                  f"{[k[0] for k in selected_rabbits.items()]}")

                    if not self.config.preview:
                        self.dws.wfr_update_computes(wfr, node_list)
                        self.dws.wfr_update_servers(breakdown,
                                                    alloc.minimumCapacity,
                                                    selected_rabbits)
                    else:
                        Console.debug(Console.MIN, f"Preview mode: resources not actually assigned to WFR {wfr.name}")

                    assign_results.append({"name": wfr.name,
                                           "result": "succeeded",
                                           "computes": node_list,
                                           "servers": [k[0] for k in selected_rabbits.items()]})
            Console.pretty_json({"action": "assignresources",
                                 "preview": self.config.preview,
                                 "results": assign_results})
            return 0

    def do_show_inventory(self):
        """Dump the loaded inventory to the console."""
        rabbits, source = self.do_get_inventory()
        json = {
                "source": source,
                "nnfnodes": [{"name": r, "capacity": rabbits[r].capacity, "status": rabbits[r].status, "servers": []} for r in rabbits]
        }
        json = {
                "source": source,
                "nnfnodes": []
        }
        for nnf_name, nnf_obj in rabbits.items():
            nnf_json = nnf_obj.to_json()
            json["nnfnodes"].append(nnf_json)
        Console.pretty_json(json)
        return 0

    def initialize_dws(self):
        self.dws = DWS(self.config)

    def initialize_run(self):
        # Initialization
        self.preamble(1)
        # k8s config file specified on CLI or by dwsutility config
        if self.config.k8s_config != "":
            k8s_config.load_kube_config(self.config.k8s_config)
        # No k8s config file specified, resolve by contexts
        else:
            Console.debug(Console.WORDY, "No k8s config, inspecting contexts")
            contexts, active_context = k8s_config.list_kube_config_contexts()
            Console.debug(Console.WORDY, f"Contexts: {contexts}")
            if not contexts:
                self.config.usage("No contexts found an no k8s config specifed")

            contexts = [context['name'] for context in contexts]
            active_index = contexts.index(active_context['name'])
            active_context = contexts[active_index]
            Console.debug(Console.WORDY, f"Contexts: {contexts}")
            self.config.k8s_default = k8s_config.KUBE_CONFIG_DEFAULT_LOCATION
            self.config.k8s_contexts = contexts

            # If user has not specified a context, go after the default
            if self.config.k8s_active_context == "":
                self.config.k8s_active_context = active_context
                self.config.k8s_active_context_source = "Default context"
                Console.debug(Console.WORDY, f"Using active context: {active_context}")
            # User specified a context, check it and use it
            else:
                if self.config.k8s_active_context not in contexts:
                    self.config.usage(
                        f"Specified context '{self.config.k8s_active_context}'"
                        " not found.  Available contexts are "
                        f"{contexts}.")

                Console.debug(Console.WORDY, "Using specified context:"
                              " {self.config.k8s_active_context}")

            k8s_config.load_kube_config(
                context=self.config.k8s_active_context)

        self.preamble(2)

    def run(self):
        """Entrypoint for the DWSUtility class."""
        ret_code = 0

        try:
            self.initialize_run()

            # If user specified flag to only display the config, stop now
            if self.config.showconfigonly:
                return

            self.initialize_dws()

            # Process Workflow operations
            error_msg = None
            if self.config.context == "WFR":

                if self.config.operation == "LIST":
                    ret_code = self.do_list_wfr()
                elif self.config.operation == "DELETE":
                    ret_code = self.do_delete_wfr(self.config.wfr_name)
                elif self.config.operation == "GET":
                    ret_code = self.do_get_wfr(self.config.wfr_name)
                elif self.config.operation == "CREATE":
                    ret_code = self.do_create_wfr()
                elif self.config.operation == "ASSIGNRESOURCES":
                    ret_code = self.do_assign_resources()
                elif self.config.operation == "PROGRESS":
                    ret_code = self.do_progress_wfr()
                elif self.config.operation == "PROGRESSTEARDOWN":
                    ret_code = self.do_progressteardown_wfr()
                elif self.config.operation == "INVESTIGATE":
                    ret_code = self.do_investigate_wfr()
                else:
                    self.config.usage(f"Unrecognized operation {self.config.operation} specified for {self.config.context}")

            # Process Inventory operations
            elif self.config.context == "INVENTORY":
                if self.config.operation == "SHOW":
                    ret_code = self.do_show_inventory()
                else:
                    self.config.usage(f"Unrecognized operation {self.config.operation} specified for {self.config.context}")

            # Process Storage operations
            elif self.config.context == "STORAGE":
                if self.config.operation == "LIST":
                    ret_code = self.do_list_storage()
                else:
                    self.config.usage(f"Unrecognized operation {self.config.operation} specified for {self.config.context}")

            # Process System operations
            elif self.config.context == "SYSTEM":
                if self.config.operation == "INVESTIGATE":
                    ret_code = self.do_investigate_system()
                else:
                    self.config.usage(f"Unrecognized operation {self.config.operation} specified for {self.config.context}")

            else:
                self.config.usage(f"Unrecognized context {self.config.context}")

            if error_msg:
                Console.error(error_msg)
        except DWSError as ex:
            Console.pretty_json(ex.to_json())
            return ex.code

        return ret_code
