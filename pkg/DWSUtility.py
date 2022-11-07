# -*- coding: utf-8 -*-
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
# DWS Utility main class

import sys
import yaml
import re
from functools import reduce
import queue
import texttable
import datetime

import kubernetes.config as k8s_config

from .Config import Config
from .Console import Console
from .Dws import DWS, DWSError
from .crd.Storage import Storage


class DWSUtility:
    """Contains the dwsutil base implementation."""

    HPE_DWS_CRDS = [
        "clientmounts.dws.cray.hpe.com",
        "computes.dws.cray.hpe.com",
        "directivebreakdowns.dws.cray.hpe.com",
        "dwdirectiverules.dws.cray.hpe.com",
        "persistentstorageinstances.dws.cray.hpe.com",
        "servers.dws.cray.hpe.com",
        "storagepools.dws.cray.hpe.com",
        "storages.dws.cray.hpe.com",
        "systemconfigurations.dws.cray.hpe.com",
        "workflows.dws.cray.hpe.com",
    ]

    HPE_NNF_CRDS = [
        "lustrefilesystems.cray.hpe.com",
        "nnfaccesses.nnf.cray.hpe.com",
        "nnfnodeecdata.nnf.cray.hpe.com",
        "nnfdatamovements.nnf.cray.hpe.com",
        "nnfnodes.nnf.cray.hpe.com",
        "nnfnodestorages.nnf.cray.hpe.com",
        "nnfstorageprofiles.nnf.cray.hpe.com",
        "nnfstorages.nnf.cray.hpe.com",

        "datamovementmanagers.dm.cray.hpe.com",
    ]

    HPE_CRDS = HPE_DWS_CRDS + HPE_NNF_CRDS

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
        Console.debug(Console.MAX, f"Configuration: {self.config.to_json()}")

    def object_str(self, objtype, name, created="n/a", owner="n/a", not_found=False):
        """Convenience method for formatting object information."""
        width = 50
        spacer = " " * width
        if not_found:
            return(f"{(objtype+spacer)[:20]} name : {(name+spacer)[:30]} ** OBJECT NOT FOUND **")
        else:
            return(f"{(objtype+spacer)[:20]} name : {(name+spacer)[:30]} owner: {(owner+spacer)[:45]} created: {(created+spacer)[:20]}")

    def investigate_system_configuration(self, facts):
        """Report current configuration and cluster info."""
        Console.output("\nConfiguration", output_timestamp=False)
        Console.output("-" * 20, output_timestamp=False)
        tsp = Console.timestamp

        Console.timestamp = False
        apic = k8s_config.kube_config.ApiClient()
        host = apic.configuration.host
        self.config.output_config_item("DWS API Endpoint", host)
        self.config.output_configuration(init_flags_only=True)
        Console.timestamp = tsp

    def investigate_nodes(self, facts):
        """Investigate Nodes in the system and report any issues."""
        node_count = 0
        rabbit_count = 0
        manager_count = 0
        notready_rabbit_count = 0
        notready_manager_count = 0
        rabbit_nodes = []
        manager_nodes = []
        other_nodes = []
        kind_env_detected = False
        try:
            nodes = self.dws.node_list()
            for node in nodes.items:
                if not kind_env_detected and node.metadata.name.lower().startswith("kind"):
                    kind_env_detected = True
                    facts.append(f"KIND environment detected (node: {node.metadata.name})")
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
                node_str = f"{(node.metadata.name + ' '*35)[:35]} {(status+' '*5)[:10]} labels: {labels} taints: {taints}"

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
            Console.output("-" * 20, output_timestamp=False)
            if len(manager_nodes) == 0:
                Console.output("None", output_timestamp=False)
                facts.append("WARNING: No HPE manager nodes are present")
            else:
                for node in manager_nodes:
                    Console.output(node, output_timestamp=False)

            Console.output("\nHPE Rabbit Nodes", output_timestamp=False)
            Console.output("-" * 20, output_timestamp=False)
            if len(rabbit_nodes) == 0:
                Console.output("None", output_timestamp=False)
                facts.append("WARNING: No HPE rabbit nodes are present")
            else:
                for node in rabbit_nodes:
                    Console.output(node, output_timestamp=False)

            Console.output("\nOther Nodes", output_timestamp=False)
            Console.output("-" * 20, output_timestamp=False)
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

    def investigate_pods(self, facts):
        """Investigate PODs in the system and report any issues."""
        Console.output("\nPods", output_timestamp=False)
        Console.output("-" * 20, output_timestamp=False)
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

    def investigate_crds(self, facts):
        """Investigate CRDs in the system and report missing ones."""
        Console.output("\nCustom Resource Definitions", output_timestamp=False)
        Console.output("-" * 50, output_timestamp=False)
        crd_count = 0
        # NOTE: Any added/deleted CRDs need to be reflected in this list
        unexpected_crd_list = []
        crds = self.dws.crd_list()
        hpe_crds = self.HPE_CRDS.copy()
        for crd in crds.items:
            if "hpe.com" in crd.metadata.name:
                crd_count += 1
                if crd.metadata.name in hpe_crds:
                    hpe_crds.remove(crd.metadata.name)
                    Console.output(crd.metadata.name, output_timestamp=False)
                else:
                    crd_str = f"Unexpected CRD: {crd.metadata.name}"
                    Console.output(f" *  {crd_str}", output_timestamp=False)
                    unexpected_crd_list.append(f"WARNING: {crd_str}")

        for crd in hpe_crds:
            facts.append(f"WARNING: HPE custom resource definition '{crd}' does not exist in the system")
        if (len(unexpected_crd_list) > 0):
            facts.extend(unexpected_crd_list)
            facts.append("WARNING: Any legitimate unexpected CRDs should be added to DWSUtility")
        facts.append(f"HPE custom resource definitions: {crd_count}")

    def investigate_storages(self, facts):
        """Investigate Storages in the system."""
        Console.output("\nStorages", output_timestamp=False)
        Console.output("-" * 50, output_timestamp=False)
        try:
            storages = self.dws.storage_get_all()

            if Console.level_enabled(Console.WORDY):
                Console.pretty_json(storages)

            if len(storages) == 0:
                Console.output("No Storage objects available", output_timestamp=False)
                facts.append("WARNING: No Storage objects in system")
            else:
                facts.append(f"Total Storage objects: {len(storages)}")
                Console.output(f"Total Storage objects: {len(storages)}", output_timestamp=False)
                ready_count = len(list(filter(lambda x: x.is_ready, storages)))
                if ready_count == 0:
                    facts.append("WARNING: No Storage objects in system are READY")

            for storage in storages:
                Console.output(f"{'-'*20} Object: Storage default.{storage.name}{'-'*20}", output_timestamp=False)
                storage_raw = storage.raw_storage
                storage_raw["metadata"].pop("managedFields")
                ready_count = len(list(filter(lambda x: x["status"] == "Ready", storage_raw['data']['devices'])))
                Console.pretty_json(storage_raw)
                Console.output(f"{len(storage_raw['data']['access']['computes'])} Computes defined", output_timestamp=False)
                Console.output(f"{len(storage_raw['data']['access']['servers'])} Servers defined", output_timestamp=False)
                Console.output(f"{len(storage_raw['data']['devices'])} Devices defined, {ready_count} are READY", output_timestamp=False)
                if ready_count == 0:
                    facts.append(f"WARNING: No devices in Storage {storage.name} are READY")
                if storage.is_ready:
                    Console.output("Storage IS ready", output_timestamp=False)
                else:
                    facts.append(f"WARNING: Storage {storage.name} IS NOT READY")
                    Console.output("Storage IS NOT ready", output_timestamp=False)

        except DWSError as ex:
            Console.output(ex.message, output_timestamp=False)
            return None, ex.code, False

    def _age_delta(self, now, timestamp):
        """Calculate the time delta.

        Params:
        now: a datetime value
        timestamp: a .metadata.creationTimestamp value.  Ex "2022-04-20T21:37:13Z"

        Returns:
        A string showing the delta.
        """
        date_format_str = '%Y-%m-%dT%H:%M:%S%z'
        then = datetime.datetime.strptime(timestamp, date_format_str)
        delta = now - then
        secs = int(delta.total_seconds())
        vals = []
        if secs >= (60 * 60 * 24):
            days = int(secs / (60 * 60 * 24))
            secs = int(secs % (60 * 60 * 24))
            vals.append(f"{days}d")
        if secs >= (60 * 60):
            hours = int(secs / (60 * 60))
            secs = int(secs % (60 * 60))
            vals.append(f"{hours}h")
        if secs >= 60:
            mins = int(secs / 60)
            secs = int(secs % 60)
            vals.append(f"{mins}m")
        if secs > 0:
            vals.append(f"{secs}s")
        # Just return the two highest-order values.
        return ''.join(vals[:2])

    def _walk_path(self, obj, path_ary):
        """Walk into an object, returning the leaf node.  The path_ary
           represents a json path, such as ".status.ready", minus the first
           empty element, so it'll be ['status', 'ready'].  If one component
           of the path is not present then an empty string is returned at
           that point.

        Params:
        obj: A dict that represents a k8s resource.
        path_ary: A list that has components from a json path.

        Returns:
        The value of the leaf, as specified in @path_ary.
        """
        if path_ary[0] in obj:
            next = obj[path_ary[0]]
        else:
            return ""
        if len(path_ary) == 1:
            return next
        return self._walk_path(next, path_ary[1:])

    def do_resource_list(self):
        """Brief list of resources from the DWS and NNF CRDs"""
        hpe_crds = self.HPE_CRDS.copy()

        for crd_elem in hpe_crds:
            if isinstance(crd_elem, list):
                crd = crd_elem[0]
                apiver = crd_elem[1]
            else:
                crd = crd_elem
                apiver = "v1alpha1"

            try:
                crd_obj = self.dws.get_custom_resource_definition(crd)
            except Exception:
                continue
            printer_cols = self.dws.get_crd_printer_columns(crd_obj)

            plural, _, group = crd.partition(".")
            try:
                resources = self.dws.list_cluster_custom_object(plural, group, apiver)
            except Exception:
                continue

            Console.output(f"=== {plural}", output_timestamp=False)
            if len(resources) == 0:
                Console.output("", output_timestamp=False)
                continue

            table = texttable.Texttable(0)
            table.set_deco(texttable.Texttable.HEADER)
            headers = ['NAMESPACE', 'NAME']
            if printer_cols is None:
                headers.append('AGE')
            else:
                # Add the custom printer column headers.
                for pcol in printer_cols:
                    if pcol.priority is None:
                        headers.append(pcol.name)
            table.add_row(headers)

            now = datetime.datetime.now(datetime.timezone.utc)
            for n in resources:
                row = [n['metadata']['namespace'], n['metadata']['name']]
                if printer_cols is None:
                    row.append(self._age_delta(now, n['metadata']['creationTimestamp']))
                else:
                    # Add the custom printer column values.
                    for pcol in printer_cols:
                        if pcol.priority is None:
                            # Split the path, dropping the leading empty dot element.
                            path = pcol.json_path.split('.')[1:]
                            val = self._walk_path(n, path)
                            if val == "":
                                pass
                            elif str(pcol.type) == 'boolean':
                                val = "true" if val else "false"
                            elif str(pcol.type) == 'integer':
                                val = int(val)
                            elif str(pcol.type) == 'date':
                                val = self._age_delta(now, val)
                            row.append(val)

                table.add_row(row)

            Console.output(table.draw(), output_timestamp=False)
            Console.output("", output_timestamp=False)

        return 0

    def do_resource_purge(self):
        """Purge all known custom resources"""
        hpe_crds = self.HPE_CRDS.copy()

        for crd_elem in hpe_crds:

            table = texttable.Texttable(0)
            table.set_deco(texttable.Texttable.HEADER)
            headers = ['NAMESPACE', 'NAME', 'RESULT']
            table.add_row(headers)

            rows = self.dws.remove_custom_resource_finalizers(crd_elem)
            if not rows:
                continue

            table.add_rows(rows)
            Console.output(table.draw(), output_timestamp=False)
            Console.output("", output_timestamp=False)

    def do_investigate_system(self):
        """Investigate the cluster configuration"""
        facts = []

        self.investigate_system_configuration(facts)

        self.investigate_nodes(facts)

        self.investigate_pods(facts)

        self.investigate_storages(facts)

        self.investigate_crds(facts)

        # Dump summary of investigation
        Console.output("\nSummary", output_timestamp=False)
        Console.output("-" * 20, output_timestamp=False)
        if len(facts) == 0:
            Console.output("Nothing to report", output_timestamp=False)
        else:
            for fact in list(filter(lambda x: not x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
            for fact in list(filter(lambda x: x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
        return 0

    def investigate_wfr(self, facts, objects):
        """Investigate the workflow and report any issues."""
        assign_expected = True

        try:
            wfr = self.dws.crd_get_raw("workflows", self.config.wfr_name)
            objects.append(self.object_str("Workflow", f"{wfr['metadata']['namespace']}.{wfr['metadata']['name']}", f"{wfr['metadata']['creationTimestamp']}"))
            wfr["metadata"].pop("managedFields")
            Console.output(f"{'-'*20} Object: Workflow default.{wfr['metadata']['name']}{'-'*20}", output_timestamp=False)
            Console.pretty_json(wfr)

            if "metadata" not in wfr:
                Console.error("Workflow does not contain a metadata section", output_timestamp=False)
                return None, -1, False

            if "spec" not in wfr:
                Console.error("Workflow does not contain a spec section", output_timestamp=False)
                return None, -1, False

            if "status" not in wfr:
                Console.error("Workflow does not contain a status section", output_timestamp=False)
                return None, -1, False

        except DWSError as ex:
            Console.output(ex.message, output_timestamp=False)
            return None, ex.code, False

        if wfr["spec"]["desiredState"] == "Proposal":
            assign_expected = False

        if wfr["spec"]["desiredState"] == wfr["status"]["state"]:
            if wfr["status"]["ready"]:
                facts.append(f"WORKFLOW: desiredState '{wfr['spec']['desiredState']}' has been achieved")
            else:
                facts.append(f"WARNING: state '{wfr['spec']['desiredState']}' matches desiredState HOWEVER ready field is FALSE")
        else:
            facts.append(f"WORKFLOW: desiredState '{wfr['spec']['desiredState']}' has NOT been achieved")
            if wfr["status"]["ready"]:
                facts.append("WARNING: Workflow ready field IS TRUE")
        if "dwDirectives" not in wfr["spec"]:
            facts.append("WARNING: No dwDirectives field in spec")
        elif len(wfr["spec"]["dwDirectives"]) < 1:
            facts.append("WARNING: No datawarp directives in this workflow")

        if "reason" in wfr["status"] and wfr["status"]["reason"] == "ERROR":
            facts.append(f"ERROR: Reason field indicates error: Message is '{wfr['status']['message']}'")
        return wfr, 0, assign_expected

    def investigate_computes(self, wfr, facts, objects, assign_expected, expected_but_missing):
        """Investigate computes and report any issues."""
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

    def investigate_breakdowns(self, wfr, facts, objects, assign_expected, expected_but_missing):
        """Investigate directivebreakdowns and report any issues."""
        if "status" not in wfr or "directiveBreakdowns" not in wfr["status"]:
            facts.append(f"WARNING: No directiveBreakdowns for Workflow {wfr['metadata']['name']}")
            return

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

                # Dump out storage for this breakdown
                if 'storage' not in breakdown['status']:
                    if assign_expected:
                        facts.append(f"WARNING: Workflow desiredState is '{wfr['spec']['desiredState']}' but no servers have been assigned")
                    else:
                        facts.append(f"DirectiveBreakdown: {bdname} does not have a storage element")
                else:
                    if 'reference' not in breakdown['status']['storage']:
                        if assign_expected:
                            facts.append(f"WARNING: Workflow desiredState is '{wfr['spec']['desiredState']}' but no servers have been assigned")
                        else:
                            facts.append(f"DirectiveBreakdown: {bdname} does not have a reference element")
                    else:
                        servers = breakdown['status']['storage']['reference']
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

    def do_investigate_wfr(self):
        """Investigate the named workflow"""
        facts = []
        objects = []
        expected_but_missing = []
        kind_env_detected = False
        try:
            nodes = self.dws.node_list()
            for node in nodes.items:
                if node.metadata.name.lower().startswith("kind"):
                    kind_env_detected = True
                    facts.append(f"WARNING: KIND environment detected (node named {node.metadata.name})")
                    break
        except Exception:
            pass

        wfr, retcode, assign_expected = self.investigate_wfr(facts, objects)

        if not wfr:
            return -1

        if kind_env_detected:
            facts.append("WARNING: Compute assignments NOT evaluated for KIND environment")
        else:
            self.investigate_computes(wfr, facts, objects, assign_expected, expected_but_missing)

        self.investigate_breakdowns(wfr, facts, objects, assign_expected, expected_but_missing)

        # Dump summary of investigation
        Console.output("\nObjects evaluated", output_timestamp=False)
        Console.output("-" * 20, output_timestamp=False)
        for obj in objects:
            Console.output(obj, output_timestamp=False)

        Console.output("\nMissing objects", output_timestamp=False)
        Console.output("-" * 20, output_timestamp=False)
        if len(expected_but_missing) < 1:
            Console.output("No missing objects", output_timestamp=False)
        else:
            for obj in expected_but_missing:
                Console.output(obj, output_timestamp=False)

        Console.output("\nSummary", output_timestamp=False)
        Console.output("-" * 20, output_timestamp=False)
        if len(facts) == 0:
            Console.output("Nothing to report", output_timestamp=False)
        else:
            for fact in list(filter(lambda x: not x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
            for fact in list(filter(lambda x: x.startswith("WARNING"), facts)):
                Console.output(fact, output_timestamp=False)
        return 0

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
            if self.config.wait:
                wfr = self.dws.wfr_get(wfr_name)
                if not wfr.is_ready:
                    Console.output(f"Waiting {self.config.timeout_seconds}s for Ready: WFR {wfr_name}")
                    _ = self.dws.wfr_wait_for_ready(wfr_name, self.config.timeout_seconds)
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

                if self.config.wait:
                    if not wfr.is_ready:
                        Console.output(f"Waiting {self.config.timeout_seconds}s for Ready: WFR {wfr_name}")
                        wfr = self.dws.wfr_wait_for_ready(wfr_name, self.config.timeout_seconds)

                desiredState = self.dws.wfr_get_next_state(wfr.state)
                if desiredState is None:
                    if wfr.state == "Teardown" and not fail_from_teardown:
                        if wfr.is_ready:
                            msg = f"Workflow '{wfr_name}'"\
                                  " has achieved 'Teardown'"
                        else:
                            msg = f"Workflow '{wfr_name}'"\
                                  " is in 'Teardown'"

                        results.append({"name": wfr_name,
                                        "result": "succeeded",
                                        "message": msg})
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
                desiredState = "Teardown"
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
                wfr_name = self.config.wfr_name + "-" + str(iteration)
            try:
                if not self.config.preview:
                    self.dws.wfr_create(wfr_name,
                                        self.config.dwdirectives,
                                        self.config.user_id,
                                        self.config.group_id,
                                        self.config.wlm_id,
                                        self.config.job_id)
                else:
                    Console.debug(Console.MIN, f"Preview mode: WFR {wfr_name} not created")
                results.append({"name": wfr_name,
                                "result": "succeeded",
                                "message": f"Workflow '{wfr_name}' created"})
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
                        node_obj = Storage(node)
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
        return self.dws.inventory_build_from_cluster(only_ready_nodes), source

    def do_assign_resources(self):
        """Assign server and compute resources to the specified Workflow CR."""
        computes = []  # Master list of compute nodes
        selected_computes = {}  # Computes are selected for the workflow

        Console.debug(Console.WORDY, "Retrieving inventory")
        rabbits, source = self.do_get_inventory(only_ready_nodes=True)
        kind_env_detected = False

        if len(rabbits) < 1:
            msg = f"Inventory from {source} does not contain any nnf nodes that can be assigned"
            raise DWSError(msg, DWSError.DWS_NO_INVENTORY)

        # Build a master dict of computes that could be assigned
        Console.debug(Console.WORDY, f"Building master list of nnf and compute nodes, {len(rabbits)} NNF nodes available")
        for node_name, node in rabbits.items():
            if not kind_env_detected and node.name.strip().lower().startswith("kind"):
                kind_env_detected = True
                Console.debug(Console.MIN, f"Node {node.name} indicates KIND environment, compute nodes WILL NOT be assigned")

            if node.name.strip().lower() in self.config.exclude_rabbits:
                Console.debug(Console.MIN, f"Excluding nnf node {node.name}")
                continue

            for c in node.computes:
                if c["status"] != "Ready":
                    Console.debug(Console.MIN,
                                  f"...compute {c['name']} is"
                                  " not ready and will be skipped")
                    continue

                if c['name'].strip().lower() in self.config.exclude_computes:
                    Console.debug(Console.MIN, f"...Excluding compute node {c['name']}")
                    continue

                compute = {"storageName": node.name,
                           "computeName": c['name'],
                           "computeStatus": c['status']}
                Console.debug(Console.WORDY, f"...adding {node.name}: {c['name']} to list")
                computes.append(compute)

        if len(computes) < self.config.nodes:
            msg = f"There are only {len(computes)} compute nodes available, however {self.config.nodes} computes has been specified."
            raise DWSError(msg, DWSError.DWS_INCOMPLETE)

        Console.debug(Console.WORDY, "Retrieving workflow"
                                     f" {self.config.wfr_name}")
        wfr = self.dws.wfr_get(self.config.wfr_name)
        Console.debug(Console.WORDY, "compute object name:"
                                     f" {wfr.compute_obj_name}")

        Console.debug(Console.WORDY, "Processing directive breakdowns")
        breakdowns = self.dws.wfr_get_directiveBreakdowns(wfr)
        if len(breakdowns) == 0:
            msg = f"Workflow Resource named '{wfr.name}' has no directive breakdowns"
            raise DWSError(msg, DWSError.DWS_INCOMPLETE)

        all_breakdown_allocations = []
        label_constrained_nodes = {}

        # Iterate each directive breakdown (1 per #dw)
        for breakdown in breakdowns:
            Console.debug(Console.WORDY, Console.FULL_BAR)
            Console.debug(Console.WORDY, f"Processing breakdown {breakdown.name}")
            allocations = breakdown.allocationSet
            breakdown_allocations = {"name": breakdown.name, "serverObj": breakdown.server_obj, "allocationSet": []}
            all_breakdown_allocations.append(breakdown_allocations)
            compute_nodes = []
            rabbits_in_breakdown = {}
            alloc_idx = 0
            across_servers = []
            single_server = []
            per_compute = []

            # Collect the allocations for this directive breakdown
            for alloc in allocations:

                alloc_idx += 1
                Console.debug(Console.WORDY, f"...collecting allocation {alloc_idx}, type {alloc.label} - {alloc.allocationStrategy}")
                if alloc.is_across_servers:
                    across_servers.append(alloc)

                elif alloc.is_single_server:
                    single_server.append(alloc)

                elif alloc.is_per_compute:
                    per_compute.append(alloc)

            # *****************************************************************
            # Address per compute allocations first, they have no constraints
            # *****************************************************************
            if len(per_compute) == 0:
                Console.debug(Console.WORDY, "No 'AllocatePerCompute' to process")
            else:
                Console.debug(Console.WORDY, "Processing 'AllocatePerCompute'")
                Console.debug(Console.WORDY, "-" * 40)
                selected_rabbits = {}  # Rabbits are selected per allocation
                for alloc in per_compute:
                    for c in computes:
                        rabbit_name = c["storageName"]
                        r = rabbits[rabbit_name]

                        Console.debug(Console.WORDY, f"   looking at compute {c['computeName']} on rabbit {rabbit_name}")

                        # If this rabbit has adequate capacity
                        if r.has_sufficient_capacity(alloc.minimumCapacity):
                            # Composite key protects against duplicates
                            compute_key = f"{rabbit_name}-{c['computeName']}"

                            selected_computes[compute_key] = c

                            # Increase the allocation count for this rabbit
                            if r.name in selected_rabbits:
                                rabbit = selected_rabbits[r.name]
                                rabbit['allocationCount'] += 1
                            else:
                                rabbit = {"name": r.name, "allocationCount": 1}
                            selected_rabbits[r.name] = rabbit
                            rabbits_in_breakdown[r.name] = rabbit
                            r.remaining_storage -= alloc.minimumCapacity
                            r.allocationCount += 1

                            Console.debug(Console.WORDY, f"   selecting compute node '{c['computeName']}' on '{rabbit_name}', {len(selected_computes)} of {self.config.nodes} selected")
                            Console.debug(Console.WORDY, f"   rabbit remaining storage: {r.remaining_storage}")
                        else:
                            Console.debug(Console.MIN, f"   rabbit {rabbit_name} has"
                                          " insufficient storage to be considered")

                        # If we selected the specified number of nodes....
                        if len(selected_computes) == self.config.nodes:
                            Console.debug(Console.MIN, f"{self.config.nodes}"
                                          " computes successfully selected")
                            break
                    # If we went through all of our rabbits and still didn't find
                    # enough compute nodes, the assign cannot be completed
                    if len(selected_computes) != self.config.nodes:
                        msg = "There are not enough compute nodes in a ready"\
                            f" state to meet the required node count of"\
                            f" {self.config.nodes}"
                        raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)

                    if kind_env_detected:
                        compute_nodes = [f"{selected_computes[c]['computeName']} "
                                         "(not set in KIND env)"
                                         for c in selected_computes]
                    else:
                        compute_nodes = [selected_computes[c]['computeName']
                                         for c in selected_computes]

                    Console.debug(Console.MAX, f"{self.config.nodes}"
                                  f" compute(s) to be assigned: {compute_nodes}")
                    Console.debug(Console.MIN, " nnfnode(s) to be assigned: "
                                  f"{[k[0] for k in selected_rabbits.items()]}")

                assignment = {"label": alloc.label, "allocationSize": alloc.minimumCapacity, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                breakdown_allocations["allocationSet"].append(assignment)
                if Console.level_enabled(Console.WORDY):
                    Console.debug(Console.WORDY, "AllocatePerCompute details:")
                    Console.pretty_json(assignment)

            # *****************************************************************
            # Address single server allocations (e.g. MGT/MDT)
            # *****************************************************************
            if len(single_server) == 0:
                Console.debug(Console.WORDY, "No 'AllocateSingleServer' to process")
            else:
                Console.debug(Console.WORDY, "Processing 'AllocateSingleServer'")
                Console.debug(Console.WORDY, "-" * 40)
                idx = 0
                all_selected_rabbits = {}
                for alloc in single_server:
                    idx += 1
                    selected_rabbits = {}  # Rabbits are selected per allocation
                    Console.debug(Console.MIN, f"   Processing allocation {idx}: {alloc.label}")
                    # Determine if this allocation type cannot coexist
                    if alloc.has_colocation_constraints:
                        Console.debug(Console.MIN, f"   Allocation {alloc.label} has colocation constraints")
                        if alloc.label not in label_constrained_nodes:
                            Console.debug(Console.MIN, f"   Added constraint label {alloc.label}")
                            label_constrained_nodes[alloc.label] = []

                    # Scan rabbits to see if we have a place for this allocation
                    idx = 0
                    for node_name, r in rabbits.items():
                        Console.debug(Console.MIN, f"   Looking at rabbit {node_name} for {alloc.label}")
                        rabbit_eligible = True
                        idx += 1

                        # Determine if this rabbit is eligible from a
                        # colocation constraint perspective
                        if alloc.has_colocation_constraints and node_name in label_constrained_nodes[alloc.label]:
                            rabbit_eligible = False
                            Console.debug(Console.MIN, f"     Rabbit is not eligible as it already has an {alloc.label}")
                            continue

                        # In the interest of distributing components across
                        # rabbits, see if the user wants to reuse or not reuse
                        # rabbits for Single Server allocations.  Controlled
                        # by the --noreuse flag
                        if rabbit_eligible and node_name in all_selected_rabbits and (not self.config.reuse_rabbit) and idx < len(rabbits):
                            rabbit_eligible = False
                            Console.debug(Console.MIN, "     Rabbit is eligible but has already been used and --noreuse specified")
                            continue

                        if rabbit_eligible:
                            Console.debug(Console.MIN, "     Rabbit is eligible")
                            # We found a rabbit to host this allocation

                            # If this rabbit has adequate capacity
                            if r.has_sufficient_capacity(alloc.minimumCapacity):
                                # Increase the allocation count for this rabbit
                                rabbit = {"name": r.name, "allocationCount": 1}
                                selected_rabbits[r.name] = rabbit
                                all_selected_rabbits[r.name] = rabbit
                                rabbits_in_breakdown[r.name] = rabbit

                                r.remaining_storage -= alloc.minimumCapacity
                                r.allocationCount += 1

                                Console.debug(Console.WORDY, f"   Selecting '{node_name}' for allocation type '{alloc.label}'")
                                Console.debug(Console.WORDY, f"   Rabbit remaining storage: {r.remaining_storage}")

                                # If we haven't filled out our computes yet,
                                # lets go after them from this Rabbit
                                if len(compute_nodes) < self.config.nodes:
                                    for c in r.computes:
                                        if c["status"] == "Ready" and\
                                           c['name'] not in compute_nodes:
                                            Console.debug(Console.WORDY, f"   Adding compute {c['name']} for assignment")
                                            compute_nodes.append(c['name'])
                                            if len(compute_nodes) >= self.config.nodes:
                                                break
                            else:
                                Console.debug(Console.MIN, f"   rabbit {node_name} has"
                                              " insufficient storage to be considered")

                        Console.debug(Console.MIN, "   nnfnode(s) to be assigned: "
                                      f"{[k[0] for k in selected_rabbits.items()]}")

                        assignment = {"label": alloc.label, "allocationSize": alloc.minimumCapacity, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                        breakdown_allocations["allocationSet"].append(assignment)
                        if Console.level_enabled(Console.WORDY):
                            Console.debug(Console.WORDY, f"   allocation {idx} details:")
                            Console.pretty_json(assignment)
                        break
                        Console.debug(Console.WORDY, "-" * 40)

                    if len(selected_rabbits) == 0:
                        msg = f"Unable to locate a rabbit to serve '{alloc.label}'"
                        raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)

            # *****************************************************************
            # Address allocations across servers (e.g. OST)
            # *****************************************************************
            if len(across_servers) == 0:
                Console.debug(Console.WORDY, "No 'AllocateAcrossServers' to process")
            else:
                Console.debug(Console.WORDY, "Processing 'AllocateAcrossServers'")
                Console.debug(Console.WORDY, "-" * 40)
                for alloc in across_servers:
                    selected_rabbits = {}  # Rabbits are selected per allocation

                    # Determine if selected rabbits can handle remaining capacity
                    min_capacity = reduce(lambda a, b: a if a < b else b, [rabbits[r].capacity for r in rabbits_in_breakdown])
                    Console.debug(Console.WORDY, f"Min capacity of selected rabbits: {min_capacity}")
                    max_capacity = reduce(lambda a, b: a if a > b else b, [rabbits[r].capacity for r in rabbits_in_breakdown])
                    Console.debug(Console.WORDY, f"Max capacity of selected rabbits: {max_capacity}")

                    # If the selected rabbits can handle the allocations
                    alloc_size = alloc.minimumCapacity / len(rabbits_in_breakdown)
                    if alloc_size < min_capacity:
                        for rname in rabbits_in_breakdown:
                            r = rabbits[rname]
                            rabbit = {"name": r.name, "allocationCount": 1}
                            selected_rabbits[r.name] = rabbit
                            rabbits_in_breakdown[r.name] = rabbit

                            r.remaining_storage -= alloc_size
                            r.allocationCount += 1

                            Console.debug(Console.WORDY, f"   Selecting '{r.name}' for allocation type '{alloc.label}'")
                            Console.debug(Console.WORDY, f"   Rabbit remaining storage: {r.remaining_storage}")

                        assignment = {"label": alloc.label, "allocationSize": round(alloc_size), "storage": [selected_rabbits[x] for x in selected_rabbits]}
                        breakdown_allocations["allocationSet"].append(assignment)
                        if Console.level_enabled(Console.WORDY):
                            Console.debug(Console.WORDY, "AllocateSingleServer details:")
                            Console.pretty_json(assignment)

                        continue

                    if len(selected_rabbits) == 0:
                        msg = f"Unable to locate enough rabbits to meet capacity {alloc.minimumCapacity} for '{alloc.label}'"
                        raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)

            # All allocations processed
            Console.debug(Console.MIN, f"All allocations processed for {breakdown.name}")
            if Console.level_enabled(Console.MIN):
                Console.pretty_json(all_breakdown_allocations)
                Console.output(Console.FULL_BAR)

            # If we haven't filled out our computes yet,
            # lets go after them from this Rabbit
            if len(compute_nodes) < self.config.nodes:
                for rabbit_name, r in rabbits.items():
                    if len(compute_nodes) >= self.config.nodes:
                        break
                    for c in r.computes:
                        if c["status"] == "Ready" and c['name'] not in compute_nodes:
                            Console.debug(Console.WORDY, f"   Adding compute {c['name']} for assignment")
                            compute_nodes.append(c['name'])
                            if len(compute_nodes) >= self.config.nodes:
                                break

            # See if we met our compute node requirement
            if len(compute_nodes) < self.config.nodes:
                msg = f"There are only {len(compute_nodes)} compute nodes available, however {self.config.nodes} computes has been specified."
                raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)

            alloc_idx = 0
            final_allocations = []
            for ba in all_breakdown_allocations:
                svr_results = {'name': breakdown.name, "alloc": alloc_idx, "result": "succeeded", "allocationSet": ba}
                if not self.config.preview:
                    try:
                        self.dws.wfr_update_servers(ba)
                    except DWSError as ex:
                        svr_results = {'name': breakdown.name, "alloc": alloc_idx, "result": "failed", "message": ex.message}
                else:
                    Console.debug(Console.MIN, f"Preview mode: nnf resources not actually assigned to WFR {wfr.name}")
                alloc_idx += 1

                final_allocations.append(svr_results)

        assign_results = {'name': wfr.name,
                          'result': 'succeeded',
                          'computes': compute_nodes,
                          'breakdowns': all_breakdown_allocations}

        if not self.config.preview:
            if not kind_env_detected:
                self.dws.wfr_update_computes(wfr, compute_nodes)
            else:
                Console.debug(Console.MIN, f"Kind environment: compute resources not actually assigned to WFR {wfr.name}")
        else:
            Console.debug(Console.MIN, f"Preview mode: compute resources not actually assigned to WFR {wfr.name}")

        Console.pretty_json({"action": "assignresources",
                             "preview": self.config.preview,
                             "results": assign_results})

        return 0

    def do_assign_computes(self):
        kind_env_detected = False
        rabbit_names = []
        rabbit_allocations = {}
        is_xfs = False

        Console.debug(Console.WORDY, "Retrieving workflow"
                                     f" {self.config.wfr_name}")
        wfr = self.dws.wfr_get(self.config.wfr_name)
        # Console.pretty_json(wfr.raw_wfr)

        # Collect any rabbits already assigned to this WFR
        for bd in wfr.directive_breakdown_names:
            bdname = bd['name']
            bdnamespace = bd['namespace']
            try:
                breakdown = self.dws.crd_get_raw("directivebreakdowns", bdname, bdnamespace)
                if 'servers' in breakdown['status']:
                    servers = breakdown['status']['servers']
                    svrname = servers['name']
                    svrnamespace = servers['namespace']
                    try:
                        server = self.dws.crd_get_raw("servers", svrname, svrnamespace)
                        server["metadata"].pop("managedFields")
                        # Console.output(f"{'-'*20} Object: Server {svrnamespace}.{svrname} {'-'*20}", output_timestamp=False)
                        # Console.pretty_json(server)
                        # TODO: Deal with times when servers haven't been assigned
                        if "allocationSets" in server["spec"]:
                            for alloc in server["spec"]["allocationSets"]:
                                for storage in alloc["storage"]:
                                    nnf_server = storage["name"]
                                    alloc_count = storage["allocationCount"]
                                    rabbit_names.append(nnf_server)
                                    rabbit_allocations[nnf_server] = alloc_count
                                    if alloc['label'] == "xfs":
                                        is_xfs = True
                                    Console.debug(Console.WORDY, f"Got nnf node {nnf_server} for {alloc['label']}")
                    except DWSError as ex:
                        print(ex)
                        pass
            except DWSError as ex:
                print(ex)
                pass

        Console.debug(Console.WORDY, "Retrieving inventory")
        rabbits, source = self.do_get_inventory(only_ready_nodes=True)
        for rabbit_name, r in rabbits.items():
            if not kind_env_detected and rabbit_name.strip().lower().startswith("kind"):
                kind_env_detected = True
                Console.debug(Console.MIN, f"Node {rabbit_name} indicates KIND environment, compute nodes WILL NOT be assigned")

            if rabbit_name.strip().lower() in self.config.exclude_rabbits:
                Console.debug(Console.MIN, f"Excluding nnf node {rabbit_name}")
                continue

            if rabbit_name not in rabbit_names:
                rabbit_names.append(rabbit_name)

        Console.debug(Console.WORDY, f"Rabbits in order of preference: {rabbit_names}")

        compute_count = 0
        computes_assigned = []
        for rabbit_name in rabbit_names:
            rabbit = rabbits[rabbit_name]
            Console.debug(Console.WORDY, f"Looking at rabbit {rabbit.name}")
            compute_limit = 16
            if is_xfs and rabbit_name in rabbit_allocations:
                compute_limit = rabbit_allocations[rabbit_name]
            Console.debug(Console.WORDY, f"..compute limit set to {compute_limit}")
            for c in rabbit.computes:
                compute_name = c['name']
                Console.debug(Console.WORDY, f"  Looking at compute '{compute_name}'")
                if compute_name.strip().lower() in self.config.exclude_computes:
                    Console.debug(Console.MIN, f"Compute node {compute_name} is in exclude list, excluding")
                    continue
                if compute_name not in computes_assigned:
                    if not self.config.ignore_ready:
                        if c['status'].lower() != "ready":
                            Console.debug(Console.MIN, f"Compute node {compute_name} is not ready, excluding")
                            continue
                    compute_count += 1
                    compute_limit -= 1
                    computes_assigned.append(compute_name)
                    if compute_count >= self.config.nodes:
                        break
                if compute_limit <= 0:
                    Console.debug(Console.WORDY, "  Compute limit reached for this rabbit")
                    break
            if compute_count >= self.config.nodes:
                break

        if compute_count < self.config.nodes:
            msg = f"Insufficient compute resources to meet node requirement of {self.config.nodes} nodes"
            raise DWSError(msg, DWSError.DWS_INCOMPLETE)

        Console.debug(Console.WORDY, f"Computes to be assigned: {computes_assigned}")
        if not self.config.preview:
            if not kind_env_detected:
                self.dws.wfr_update_computes(wfr, computes_assigned)

        assign_results = {'name': wfr.name,
                          'result': 'succeeded',
                          'computes': computes_assigned}

        Console.pretty_json({"action": "assigncomputes",
                             "preview": self.config.preview,
                             "results": assign_results})

    def do_assign_servers(self):
        """Assign server resources to the specified Workflow CR."""

        Console.debug(Console.MIN, f"Assigning servers, requested compute node count is {self.config.nodes}")

        Console.debug(Console.WORDY, "Retrieving inventory")
        rabbits, source = self.do_get_inventory(only_ready_nodes=True)

        if not self.config.ignore_ready:
            ready_rabbits = {}
            for rabbit_name, rabbit_obj in rabbits.items():
                if not rabbit_obj.is_ready:
                    Console.debug(Console.WORDY, f"nnf node {rabbit_name} is not ready, excluding")
                    continue
                Console.debug(Console.WORDY, f"nnf node {rabbit_name} is ready and will be included")
                ready_rabbits[rabbit_name] = rabbit_obj
            rabbits = ready_rabbits

        if len(rabbits) < 1:
            msg = f"Inventory from {source} does not contain any nnf nodes that can be assigned"
            raise DWSError(msg, DWSError.DWS_NO_INVENTORY)

        Console.debug(Console.WORDY, "Retrieving workflow"
                                     f" {self.config.wfr_name}")
        wfr = self.dws.wfr_get(self.config.wfr_name)

        Console.debug(Console.WORDY, "Processing directive breakdowns")
        breakdowns = self.dws.wfr_get_directiveBreakdowns(wfr)
        if len(breakdowns) == 0:
            msg = f"Workflow Resource named '{wfr.name}' has no directive breakdowns"
            raise DWSError(msg, DWSError.DWS_INCOMPLETE)

        all_breakdown_allocations = []
        label_constrained_nodes = {}

        # Iterate each directive breakdown (1 per #dw)
        for breakdown in breakdowns:
            Console.debug(Console.WORDY, Console.FULL_BAR)
            Console.debug(Console.WORDY, f"Processing breakdown {breakdown.name} for #dw {breakdown.dw_name}")
            allocations = breakdown.allocationSet
            breakdown_allocations = {"name": breakdown.name, "serverObj": breakdown.server_obj, "allocationSet": []}
            all_breakdown_allocations.append(breakdown_allocations)
            all_selected_rabbits = {}
            rabbits_in_breakdown = {}
            alloc_idx = 0
            across_servers = []
            single_server = []
            per_compute = []

            # Collect the allocations for this directive breakdown
            for alloc in allocations:

                alloc_idx += 1
                Console.debug(Console.WORDY, f"...collecting allocation {alloc_idx}, type {alloc.label} - {alloc.allocationStrategy}")
                if alloc.is_across_servers:
                    across_servers.append(alloc)

                elif alloc.is_single_server:
                    single_server.append(alloc)

                elif alloc.is_per_compute:
                    per_compute.append(alloc)

            recipe = None
            if breakdown.dw_name in self.config.alloc_recipe:
                recipe = self.config.alloc_recipe[breakdown.dw_name]
                Console.debug(Console.WORDY, "Breakdown has a PRESCRIPTIVE allocation")

            # *****************************************************************
            # Address per compute allocations first, they have no constraints
            # *****************************************************************
            if len(per_compute) == 0:
                Console.debug(Console.WORDY, "No 'AllocatePerCompute' to process")
            else:
                Console.debug(Console.WORDY, "Processing 'AllocatePerCompute'")
                Console.debug(Console.WORDY, "-" * 40)
                idx = 0
                for alloc in per_compute:
                    idx += 1
                    selected_rabbits = {}  # Rabbits are selected per allocation
                    computes_satisfied = 0
                    Console.debug(Console.WORDY, f"Processing allocation {idx}")
                    if recipe:
                        # Console.pretty_json(recipe)
                        if alloc.label not in recipe["allocs"]:
                            msg = f"Prescriptive alloc did not contain recipe for {alloc.label}"
                            raise DWSError(msg, DWSError.DWS_GENERAL)
                        else:
                            selected_rabbits = {}  # Rabbits are selected per allocation
                            alloc_obj = recipe["allocs"][alloc.label]
                            Console.debug(Console.MIN, f"   Processing element {alloc.label}")
                            allocation_count = 0
                            for server in alloc_obj["servers"]:
                                rabbit = {"name": server["name"], "allocationCount": server["allocations"]}
                                allocation_count += server["allocations"]
                                selected_rabbits[server["name"]] = rabbit
                                all_selected_rabbits[server["name"]] = rabbit
                                rabbits_in_breakdown[server["name"]] = rabbit

                                Console.debug(Console.MIN, "   nnfnode(s) to be assigned: "
                                              f"{[k[0] for k in selected_rabbits.items()]}")

                            assignment = {"label": alloc.label, "allocationSize": alloc.minimumCapacity, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                            breakdown_allocations["allocationSet"].append(assignment)
                            if Console.level_enabled(Console.WORDY):
                                Console.debug(Console.WORDY, f"   allocation {idx} details:")
                                Console.pretty_json(assignment)
                            Console.debug(Console.WORDY, "-" * 40)
                    else:
                        for rabbit_name, r in rabbits.items():
                            Console.debug(Console.WORDY, f"  Looking at rabbit '{rabbit_name}'")
                            alloc_count = 0
                            if rabbit_name.strip().lower() in self.config.exclude_rabbits:
                                Console.debug(Console.MIN, f"    Excluding rabbit node {rabbit_name}")
                                continue
                            for c in r.computes:
                                Console.debug(Console.WORDY, f"  Looking at compute '{c['name']}'")
                                if c['name'].strip().lower() in self.config.exclude_computes:
                                    Console.debug(Console.MIN, f"    Excluding compute node {c['name']}")
                                    continue

                                # Increase the allocation count for this rabbit
                                if rabbit_name in selected_rabbits:
                                    rabbit = selected_rabbits[rabbit_name]
                                    rabbit['allocationCount'] += 1
                                else:
                                    rabbit = {"name": rabbit_name, "allocationCount": 1}

                                selected_rabbits[rabbit_name] = rabbit
                                computes_satisfied += 1
                                alloc_count += 1

                                # Break out of the compute loop if we have enough computes
                                if computes_satisfied >= self.config.nodes:
                                    break

                            Console.debug(Console.MIN, f"    {alloc_count} allocations on '{rabbit_name}'")

                            # Break out of the rabbit loop
                            if computes_satisfied >= self.config.nodes:
                                break

                            # If we selected the specified number of nodes....
                            if computes_satisfied == self.config.nodes:
                                Console.debug(Console.MIN, f"{self.config.nodes}"
                                              " computes successfully selected")
                                break

                        # If we went through all of our rabbits and still didn't find
                        # enough compute nodes, the assign cannot be completed
                        if computes_satisfied < self.config.nodes:
                            msg = "There are not enough compute nodes to meet the required node count of"\
                                f" {self.config.nodes} for an allocation of type '{alloc.label}'."
                            raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)
                        else:
                            Console.debug(Console.MIN, f"{len(selected_rabbits)} rabbit(s) selected for {self.config.nodes} '{alloc.label}' allocations.")

                        Console.debug(Console.MIN, " nnfnode(s) to be assigned: "
                                      f"{[k[0] for k in selected_rabbits.items()]}")

                        assignment = {"label": alloc.label, "allocationSize": alloc.minimumCapacity, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                        breakdown_allocations["allocationSet"].append(assignment)
                        if Console.level_enabled(Console.WORDY):
                            Console.debug(Console.WORDY, "AllocatePerCompute details:")
                            Console.pretty_json(assignment)
                            Console.debug(Console.WORDY, Console.HALF_BAR)
                            Console.pretty_json(breakdown_allocations)

            # *****************************************************************
            # Address single server allocations (e.g. MGT/MDT)
            # *****************************************************************
            if len(single_server) == 0:
                Console.debug(Console.WORDY, "No 'AllocateSingleServer' to process")
            else:
                Console.debug(Console.WORDY, "Processing 'AllocateSingleServer'")
                Console.debug(Console.WORDY, "-" * 40)
                idx = 0
                for alloc in single_server:
                    idx += 1
                    selected_rabbits = {}  # Rabbits are selected per allocation
                    Console.debug(Console.MIN, f"   Processing allocation {idx}: {alloc.label}")

                    if recipe:
                        # Console.pretty_json(recipe)
                        if alloc.label not in recipe["allocs"]:
                            msg = f"Prescriptive alloc did not contain recipe for {alloc.label}"
                            raise DWSError(msg, DWSError.DWS_GENERAL)
                        else:
                            alloc_obj = recipe["allocs"][alloc.label]
                            Console.debug(Console.MIN, f"   Processing element {alloc.label}")
                            for server in alloc_obj["servers"]:
                                rabbit = {"name": server["name"], "allocationCount": server["allocations"]}
                                selected_rabbits[server["name"]] = rabbit
                                all_selected_rabbits[server["name"]] = rabbit
                                rabbits_in_breakdown[server["name"]] = rabbit

                                Console.debug(Console.MIN, "   nnfnode(s) to be assigned: "
                                              f"{[k[0] for k in selected_rabbits.items()]}")

                                allocation_size = round(alloc.minimumCapacity / server["allocations"])
                                assignment = {"label": alloc.label, "allocationSize": allocation_size, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                                breakdown_allocations["allocationSet"].append(assignment)
                                if Console.level_enabled(Console.WORDY):
                                    Console.debug(Console.WORDY, f"   allocation {idx} details:")
                                    Console.pretty_json(assignment)
                                break
                                Console.debug(Console.WORDY, "-" * 40)

                    else:
                        # Determine if this allocation type cannot coexist
                        if alloc.has_colocation_constraints:
                            Console.debug(Console.MIN, f"   Allocation {alloc.label} has colocation constraints")
                            if alloc.label not in label_constrained_nodes:
                                Console.debug(Console.MIN, f"   Added constraint label {alloc.label}")
                                label_constrained_nodes[alloc.label] = []

                        # Scan rabbits to see if we have a place for this allocation
                        idx = 0
                        for rabbit_name, r in rabbits.items():
                            Console.debug(Console.MIN, f"   Looking at rabbit {rabbit_name} for {alloc.label}")
                            rabbit_eligible = True
                            idx += 1

                            # Determine if this rabbit is eligible from a
                            # colocation constraint perspective
                            if alloc.has_colocation_constraints and rabbit_name in label_constrained_nodes[alloc.label]:
                                rabbit_eligible = False
                                Console.debug(Console.MIN, f"     Rabbit is not eligible as it already has an {alloc.label}")
                                continue

                            # In the interest of distributing components across
                            # rabbits, see if the user wants to reuse or not reuse
                            # rabbits for Single Server allocations.  Controlled
                            # by the --noreuse flag
                            if rabbit_eligible and rabbit_name in all_selected_rabbits and (not self.config.reuse_rabbit) and idx < len(rabbits):
                                rabbit_eligible = False
                                Console.debug(Console.MIN, "     Rabbit is eligible but has already been used and --noreuse specified")
                                continue

                            if rabbit_eligible:
                                Console.debug(Console.MIN, "     Rabbit is eligible")
                                # We found a rabbit to host this allocation

                                # If this rabbit has adequate capacity
                                if r.has_sufficient_capacity(alloc.minimumCapacity):
                                    # Increase the allocation count for this rabbit
                                    rabbit = {"name": r.name, "allocationCount": 1}
                                    selected_rabbits[r.name] = rabbit
                                    all_selected_rabbits[r.name] = rabbit
                                    rabbits_in_breakdown[r.name] = rabbit

                                    r.remaining_storage -= alloc.minimumCapacity
                                    r.allocationCount += 1

                                    Console.debug(Console.WORDY, f"   Selecting '{rabbit_name}' for allocation type '{alloc.label}'")
                                    Console.debug(Console.WORDY, f"   Rabbit remaining storage: {r.remaining_storage}")

                                else:
                                    Console.debug(Console.MIN, f"   rabbit {rabbit_name} has"
                                                  " insufficient storage to be considered")

                            Console.debug(Console.MIN, "   nnfnode(s) to be assigned: "
                                          f"{[k[0] for k in selected_rabbits.items()]}")

                            assignment = {"label": alloc.label, "allocationSize": alloc.minimumCapacity, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                            breakdown_allocations["allocationSet"].append(assignment)
                            if Console.level_enabled(Console.WORDY):
                                Console.debug(Console.WORDY, f"   allocation {idx} details:")
                                Console.pretty_json(assignment)
                            break
                            Console.debug(Console.WORDY, "-" * 40)

                        if len(selected_rabbits) == 0:
                            msg = f"Unable to locate a rabbit to serve '{alloc.label}'"
                            raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)

            # *****************************************************************
            # Address allocations across servers (e.g. OST)
            # *****************************************************************
            if len(across_servers) == 0:
                Console.debug(Console.WORDY, "No 'AllocateAcrossServers' to process")
            else:
                Console.debug(Console.WORDY, "Processing 'AllocateAcrossServers'")
                Console.debug(Console.WORDY, "-" * 40)

                for alloc in across_servers:
                    selected_rabbits = {}  # Rabbits are selected per allocation
                    if recipe:
                        # Console.pretty_json(recipe)
                        if alloc.label not in recipe["allocs"]:
                            msg = f"Prescriptive alloc did not contain recipe for {alloc.label}"
                            raise DWSError(msg, DWSError.DWS_GENERAL)
                        else:
                            alloc_obj = recipe["allocs"][alloc.label]
                            Console.debug(Console.MIN, f"   Processing element {alloc.label}")
                            allocation_count = 0
                            for server in alloc_obj["servers"]:
                                rabbit = {"name": server["name"], "allocationCount": server["allocations"]}
                                allocation_count += server["allocations"]
                                selected_rabbits[server["name"]] = rabbit
                                all_selected_rabbits[server["name"]] = rabbit
                                rabbits_in_breakdown[server["name"]] = rabbit

                                Console.debug(Console.MIN, "   nnfnode(s) to be assigned: "
                                              f"{[k[0] for k in selected_rabbits.items()]}")

                            allocation_size = round(alloc.minimumCapacity / allocation_count)
                            assignment = {"label": alloc.label, "allocationSize": allocation_size, "storage": [selected_rabbits[x] for x in selected_rabbits]}
                            breakdown_allocations["allocationSet"].append(assignment)
                            if Console.level_enabled(Console.WORDY):
                                Console.debug(Console.WORDY, f"   allocation {idx} details:")
                                Console.pretty_json(assignment)
                            Console.debug(Console.WORDY, "-" * 40)
                    else:
                        alloc_size = round(alloc.minimumCapacity / self.config.ost_count)
                        Console.debug(Console.MIN, f"type: {alloc.label}, min capacity: {alloc.minimumCapacity}, rabbits: {self.config.ost_count}, per rabbit: {self.config.ost_per_rabbit}, alloc size: {alloc_size}")

                        # Pass 1: Look for rabbits other than the MGT/MDT hosts
                        ost_rabbit_count = 0
                        for rabbit_name, r in rabbits.items():
                            if rabbit_name in all_selected_rabbits:
                                Console.debug(Console.WORDY, f"Rabbit {rabbit_name} has already been used, skipping for now")
                                continue

                            ost_rabbit_count += 1
                            r = rabbits[rabbit_name]
                            rabbit = {"name": r.name, "allocationCount": self.config.ost_per_rabbit}
                            selected_rabbits[r.name] = rabbit
                            rabbits_in_breakdown[r.name] = rabbit

                            Console.debug(Console.WORDY, f"   Selecting '{r.name}' for allocation type '{alloc.label}'")

                            if ost_rabbit_count >= self.config.ost_count:
                                break

                        # Pass 2: If we need more rabbits
                        if ost_rabbit_count < self.config.ost_count:
                            for rabbit_name, r in all_selected_rabbits.items():
                                ost_rabbit_count += 1
                                r = rabbits[rabbit_name]
                                rabbit = {"name": r.name, "allocationCount": self.config.ost_per_rabbit}
                                selected_rabbits[r.name] = rabbit
                                rabbits_in_breakdown[r.name] = rabbit

                                Console.debug(Console.WORDY, f"   Selecting '{r.name}' for allocation type '{alloc.label}'")

                                if ost_rabbit_count >= self.config.ost_count:
                                    break

                        # After Pass2, we have failed if we haven't found enough rabbits
                        if ost_rabbit_count < self.config.ost_count:
                            msg = f"Require {self.config.ost_count} rabbits for {alloc.label} but only found {ost_rabbit_count}'"
                            raise DWSError(msg, DWSError.DWS_INSUFFICIENT_RESOURCES)

                        assignment = {"label": alloc.label, "allocationSize": round(alloc_size), "storage": [selected_rabbits[x] for x in selected_rabbits]}
                        breakdown_allocations["allocationSet"].append(assignment)
                        if Console.level_enabled(Console.WORDY):
                            Console.debug(Console.WORDY, "AllocateSingleServer details:")
                            Console.pretty_json(assignment)

                        continue

            # All allocations processed
            Console.debug(Console.MIN, f"All allocations processed for {breakdown.name}")
            if Console.level_enabled(Console.MIN):
                Console.pretty_json(all_breakdown_allocations)
                Console.output(Console.FULL_BAR)

            alloc_idx = 0
            final_allocations = []
            for ba in all_breakdown_allocations:
                svr_results = {'name': breakdown.name, "alloc": alloc_idx, "result": "succeeded", "allocationSet": ba}
                if not self.config.preview:
                    try:
                        self.dws.wfr_update_servers(ba)
                    except DWSError as ex:
                        svr_results = {'name': breakdown.name, "alloc": alloc_idx, "result": "failed", "message": ex.message}
                else:
                    Console.debug(Console.MIN, f"Preview mode: nnf resources not actually assigned to WFR {wfr.name}")
                alloc_idx += 1

                final_allocations.append(svr_results)

        assign_results = {'name': wfr.name,
                          'result': 'succeeded',
                          'breakdowns': all_breakdown_allocations}

        Console.pretty_json({"action": "assignservers",
                             "preview": self.config.preview,
                             "results": assign_results})

        return 0

    def do_show_inventory(self):
        """Dump the loaded inventory to the console."""
        rabbits, source = self.do_get_inventory()
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
                self.config.usage("No contexts found and no k8s config specifed")

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
                elif self.config.operation == "ASSIGNSERVERS":
                    ret_code = self.do_assign_servers()
                elif self.config.operation == "ASSIGNCOMPUTES":
                    ret_code = self.do_assign_computes()
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
                elif self.config.operation == "RESOURCELIST":
                    ret_code = self.do_resource_list()
                elif self.config.operation == "RESOURCEPURGE":
                    ret_code = self.do_resource_purge()
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
