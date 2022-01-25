# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# DWS Utility main class
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------

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

    def __init__(self, sim_folder):
        self.config = Config()
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

    def run(self):
        """Entrypoint for the DWSUtility class."""
        ret_code = 0

        try:
            # Initialization
            self.preamble(1)
            if self.config.k8s_config != "":
                k8s_config.load_kube_config(self.config.k8s_config)
            else:
                k8s_config.load_kube_config()
            self.preamble(2)

            # If user specified flag to only display the config, stop now
            if self.config.showconfigonly:
                return

            self.dws = DWS(self.config)

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
            else:
                self.config.usage(f"Unrecognized context {self.config.context}")

            if error_msg:
                Console.error(error_msg)
        except DWSError as ex:
            Console.pretty_json(ex.to_json())
            return ex.code

        return ret_code
