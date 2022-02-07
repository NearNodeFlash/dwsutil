# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# DWS Utility Configuration Class
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------

import os
import sys

import kubernetes.client as k8s_client

from .Console import Console
from .crd.Workflow import Workflow
from .crd.DirectiveBreakdown import DirectiveBreakdown
from .crd.Storage import Storage
from .crd.Nnfnode import Nnfnode


class DWSError(Exception):
    """Encapsulates DWS related exceptions."""
    DWS_GENERAL = 100
    DWS_NOTFOUND = 101
    DWS_ALREADY_EXISTS = 102
    DWS_NOTREADY = 103
    DWS_IMPROPERSTATE = 104
    DWS_INCOMPLETE = 105
    DWS_NO_INVENTORY = 106
    DWS_SOME_OPERATION_FAILED = 107

    DWS_K8S_ERROR = 500

    def __init__(self, message, code, raw=None):
        """Initialize a DWSError exception.

        Parameters:
        message : Error message
        code : DWS specific error code (defined here)
        raw : The raw exception message if available

        Returns:
        Nothing
        """
        self.message = message
        self.code = code
        self.raw = raw
        fcn = "(unknown)"
        try:
            f_code = sys._getframe().f_back.f_code
            co_name = f_code.co_name
            filename = os.path.basename(f_code.co_filename)
            fcn = f"{filename}:{co_name}"
        except Exception:  # pragma: no cover
            pass
        self.fcn = fcn

    def to_json(self):
        """DWSError deserialization to json.

        Parameters:
        None

        Returns:
        JSON dictionary of DWSError properties
        """
        return {"error": True, "message": self.message, "dwserrorcode": self.code, "function": self.fcn}


class DWS:
    """Wrapper class for interfacing with Data Workflow Services (DWS)."""

    @property
    def k8sapi(self):
        """Returns the internal _k8sapi interface."""
        return self._k8sapi

    def __init__(self, config):
        """Initialize dws, creates an instance of the k8s CustomObjectsApi."""
        with Console.trace_function():
            self.config = config
            self._k8sapi = k8s_client.CustomObjectsApi()

    def pods_list(self):
        with Console.trace_function():
            try:
                v1 = k8s_client.CoreV1Api()
                pods = v1.list_pod_for_all_namespaces(watch=False)
                return pods
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def node_list(self):
        with Console.trace_function():
            try:
                # Monkey patch this to get past a bug in the k8s library
                # https://github.com/kubernetes-client/python/issues/895
                from kubernetes.client.models.v1_container_image import V1ContainerImage   # pragma: no cover

                def names(self, names):  # pragma: no cover
                    self._names = names

                V1ContainerImage.names = V1ContainerImage.names.setter(names)

                api = k8s_client.CoreV1Api()
                response = api.list_node()
                return response
            except k8s_client.exceptions.ApiException as err:   # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def crd_list(self):
        with Console.trace_function():
            crd_api = k8s_client.ApiextensionsV1Api()
            try:
                crds = crd_api.list_custom_resource_definition()
                return crds
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def crd_get_raw(self, crdkind, name, namespace="default", group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve CR jSON by name for the given namespace.

        Parameters:
        crdkind : Kubernetes kind of the CR
        name : Name of the CR
        namespace : Namespace of the CR

        Returns:
        JSON of the CR
        """

        with Console.trace_function():
            crd_api = k8s_client.CustomObjectsApi()
            try:
                crd = crd_api.get_namespaced_custom_object(group, version, namespace, crdkind, name)
                return crd
            except k8s_client.exceptions.ApiException as err:
                if err.status == 404:
                    msg = f"{crdkind} named '{namespace}.{name}'' was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    # Inventory Routines
    def inventory_build_from_cluster(self, only_ready_nodes=False, allow_compute_name_munge=True, group="nnf.cray.hpe.com", version="v1alpha1"):
        """Retrieve and build the inventory tree from the cluster.

        Parameters:
        only_ready_nodes : If True, ignore any nnf nodes that are not ready
        allow_compute_name_munge : Munge compute names that match "Compute X"

        Returns:
        Dictionary keyed by nnf node name
        """

        with Console.trace_function():
            nnf_inventory = {}
            crd_api = k8s_client.CustomObjectsApi()
            try:
                nnfnode_list = crd_api.list_cluster_custom_object(group, version, "nnfnodes")
                # Console.pretty_json(nnfnode_list)
                for nnf_node in nnfnode_list['items']:
                    node_obj = Nnfnode(nnf_node, allow_compute_name_munge=allow_compute_name_munge)
                    if only_ready_nodes and not node_obj.is_ready:
                        Console.debug(Console.MIN, f"...nnf-node {node_obj.name}"
                                                   " is not ready, skipping")
                        continue
                    nnf_inventory[node_obj.name] = node_obj
                return nnf_inventory
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    # Storages Routines
    def storage_list_names(self, group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve a list of Storage CR names.

        Parameters:
        None

        Returns:
        List of Storage CR names
        """

        with Console.trace_function():
            names = []
            crd_api = k8s_client.CustomObjectsApi()
            try:
                storage_list = crd_api.list_cluster_custom_object(group, version, "storages")
                for storage in storage_list['items']:
                    names.append(storage['metadata']['name'])
                return names
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def storage_get(self, name, group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve a named Storage CR as a Storage object.

        Parameters:
        name : Name of the Storage CR

        Returns:
        a Storage object
        """

        with Console.trace_function():
            try:
                crd = self.crd_get_raw("storages", name)
                return Storage(crd)
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                if err.status == 404:
                    msg = f"Storage named {name} was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def storage_get_all(self, group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve an array of all storage objects.

        Parameters:
        None

        Returns:
        a list of Storage objects
        """

        with Console.trace_function():
            storages = []
            crd_api = k8s_client.CustomObjectsApi()
            try:
                storage_list = crd_api.list_cluster_custom_object("dws.cray.hpe.com", "v1alpha1", "storages")
                for storage_raw in storage_list['items']:
                    storages.append(Storage(storage_raw))
                return storages
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    # Workflow Resource Routines
    def wfr_list_names(self, group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve a list of Workflow objects.

        Parameters:
        None

        Returns:
        a list of Workflow names
        """

        with Console.trace_function():
            wfr_names = []
            crd_api = k8s_client.CustomObjectsApi()
            try:
                wfr_list = crd_api.list_cluster_custom_object(group, version, "workflows")
                for wfr in wfr_list['items']:
                    wfr_names.append(wfr['metadata']['name'])
                return wfr_names
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_get_raw(self, wfrname, group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve a named Workflow CR in JSON form.

        Parameters:
        wfrname : Name of the Workflow CR

        Returns:
        Workflow as JSON
        """
        with Console.trace_function():
            try:
                workflow = self.k8sapi.get_namespaced_custom_object(group, version, "default", "workflows", wfrname)
                return workflow
            except k8s_client.exceptions.ApiException as err:
                if err.status == 404:
                    msg = f"Workflow Resource named '{wfrname}' was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_get(self, wfrname, group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve a named Workflow CR as a Workflow object.

        Parameters:
        wfrname : Name of the Workflow CR

        Returns:
        a Workflow object
        """

        with Console.trace_function():
            try:
                workflow = self.k8sapi.get_namespaced_custom_object(group, version, "default", "workflows", wfrname)
                Console.debug(Console.WORDY, f"workflow: {workflow}")
                return Workflow(workflow)
            except k8s_client.exceptions.ApiException as err:
                if err.status == 404:
                    msg = f"Workflow Resource named '{wfrname}' was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_delete(self, wfrname, group="dws.cray.hpe.com", version="v1alpha1"):
        """Delete a named Workflow CR.

        Parameters:
        wfrname : Name of the Workflow CR

        Returns:
        Nothing
        """

        try:
            Console.debug(Console.MIN, f"Deleting object: {wfrname}")
            wfr = self.wfr_get(wfrname)
            if wfr.is_ready and wfr.state == "teardown":
                api_response = self.k8sapi.delete_namespaced_custom_object(group, version, "default", "workflows", wfrname)
                Console.debug(Console.WORDY, api_response)
            else:
                msg = f"Workflow Resource named '{wfrname}' must be in a state of 'teardown' to be deleted, current state is '{wfr.state}'"
                raise DWSError(msg, DWSError.DWS_IMPROPERSTATE, None)
        except k8s_client.exceptions.ApiException as err:  # pragma: no cover
            if err.status == 404:
                msg = f"Workflow Resource named '{wfrname}' was not found"
                raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
            raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_create(self, wfrname, dwdirectives, userId, wlmId, jobId, new_client=None, group="dws.cray.hpe.com", version="v1alpha1"):
        """Create a new Workflow CR.

        Parameters:
        name : Name of the Workflow CR
        dwdirectives : Any array of #dw strings
        userId : Any array of #dw strings
        wlmId: Valid WLM id
        jobId: Valid job id
        new_client - DEPRECATED, will be refactored

        Returns:
        Created Workflow object
        """

        with Console.trace_function():
            body = Workflow.body_template(wfrname, wlmId, jobId, userId, dwdirectives, "proposal", group, version)
            Console.debug(Console.WORDY, body)
            # Console.pretty_json(body)
            # TODO: Get rid of the new_client stuff
            with k8s_client.ApiClient() if not new_client else new_client as api_client:
                try:
                    api_instance = k8s_client.CustomObjectsApi(api_client)
                    # print(f"BODY: {body}")
                    api_response = api_instance.create_namespaced_custom_object("dws.cray.hpe.com", "v1alpha1", "default", "workflows", body)
                    Console.debug(Console.WORDY, api_response)
                    return Workflow(api_response)
                except k8s_client.exceptions.ApiException as err:
                    if err.status == 409:  # Conflict
                        msg = f"Unable to create Workflow Resource named {wfrname}, it already exists"
                        Console.debug(Console.WORDY, msg)
                        raise DWSError(msg, DWSError.DWS_ALREADY_EXISTS, err)
                    raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_get_next_state(self, state):
        """Determine the next desired state based on the specified state.

        Parameters:
        state : State to determine next desired state off of

        Returns:
        Next desired state if not teardown, otherwise returns None
        """

        # TODO: Move to class obj
        states = ['proposal', 'setup', 'data_in', 'pre_run', 'post_run', 'data_out', 'teardown']
        try:
            idx = states.index(state.lower())
            if idx >= len(states)-1 or idx < 0:
                return None
            return states[idx+1]
        except ValueError:
            raise DWSError(f"Invalid state {state} specified", DWSError.DWS_GENERAL)

    def wfr_update_desired_state(self, wfrname, desiredState, force_update=False, group="dws.cray.hpe.com", version="v1alpha1"):
        """Update the desired state of the named Workflow CR.

        Parameters:
        wfrname : Name of the Workflow CR to be updated
        desiredState : The value of the desiredState to be set
        force_update : Update even if Workflow isn't in ready state

        Returns:
        Nothing
        """

        try:
            Console.debug(Console.MIN, f"Progressing object: {wfrname}")
            wfr = self.wfr_get(wfrname)
            if force_update or wfr.is_ready:
                body_json = {"spec": {"desiredState": desiredState}}
                api_response = self.k8sapi.patch_namespaced_custom_object(group, version, wfr.namespace, "workflows", wfr.name, body_json)
                Console.debug(Console.WORDY, api_response)
            else:
                msg = f"Workflow Resource named '{wfrname}' must be 'ready' to be progressed, current ready state is '{wfr.ready}'"
                raise DWSError(msg, DWSError.DWS_IMPROPERSTATE, None)
        except k8s_client.exceptions.ApiException as err:
            if err.status == 404:
                msg = f"Workflow Resource named '{wfrname}' was not found"
                raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
            raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_refresh(self, wfr):
        """Refresh the given Workflow.

        Parameters:
        wfr : Workflow to be refreshed

        Returns:
        Nothing
        """

        with Console.trace_function():

            raw_wfr = self.wfr_get_raw(wfr.name, wfr.apiGroup, wfr.apiVersion)
            wfr.raw_wfr = raw_wfr

    def directivebreakdown_get_raw(self, name, namespace="default", group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve the named directive breakdown as JSON.

        Parameters:
        name : Name of the directive breakdown to retrieve

        Returns:
        directive breakdown as JSON
        """

        with Console.trace_function():
            try:
                breakdown = self.k8sapi.get_namespaced_custom_object(group, version, namespace, "directivebreakdowns", name)
                return breakdown
            except k8s_client.exceptions.ApiException as err:
                if err.status == 404:
                    msg = f"DirectiveBreakdown named {namespace}.{name} was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def directivebreakdown_get(self, name, namespace="default", group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve the named directive breakdown as DirectiveBreakdown object.

        Parameters:
        name : Name of the directive breakdown to retrieve

        Returns:
        DirectiveBreakdown object
        """

        with Console.trace_function():
            try:
                breakdown = self.k8sapi.get_namespaced_custom_object(group, version, namespace, "directivebreakdowns", name)
                return DirectiveBreakdown(breakdown)
            except k8s_client.exceptions.ApiException as err:
                if err.status == 404:
                    msg = f"DirectiveBreakdown named '{namespace}.{name}' was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_get_directiveBreakdowns(self, wfr, namespace="default", group="dws.cray.hpe.com", version="v1alpha1"):
        """Retrieve a list of DirectiveBreakdown objects tied to the given Workflow.

        Parameters:
        wfr : Workflow to return Breakdowns for

        Returns:
        list of DirectiveBreakdown objects
        """

        with Console.trace_function():
            breakdowns = []
            try:
                for n in wfr.directive_breakdown_names:
                    name = n['name']
                    Console.debug(Console.WORDY, f"retrieving breakdown name: {name}")
                    breakdown = self.directivebreakdown_get(name, namespace=namespace)
                    breakdowns.append(breakdown)
                return breakdowns
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                if err.status == 404:
                    msg = f"DirectiveBreakdown named '{namespace}.{name}' was not found"
                    raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_update_computes(self, wfr, computes, group="dws.cray.hpe.com", version="v1alpha1"):
        """Update computes for a given Workflow.

        Parameters:
        wfr : Workflow to update computes for
        computes : List of compute names for the Workflow

        Returns:
        Nothing
        """

        with Console.trace_function():
            compute_name = wfr.compute_obj_name[0]
            compute_namespace = wfr.compute_obj_name[1]
            compute_list = [{'name': c} for c in computes]
            body_json = {"data": compute_list}

            api_response = self.k8sapi.patch_namespaced_custom_object(group, version, compute_namespace, "computes", compute_name, body_json)
            Console.debug(Console.WORDY, api_response)

    def wfr_update_servers(self, breakdown, minimumAlloc, nnfnodes, group="dws.cray.hpe.com", version="v1alpha1"):
        """Update servers(nnfnodes) for a given Workflow.

        Parameters:
        wfr : Workflow to update computes for
        nnfnodes : List of servers nnfnodes for the Workflow

        Returns:
        Nothing
        """

        with Console.trace_function():
            serverName, serverNamespace = breakdown.server_obj

            serverList = [{'name': r.name, 'allocationCount': r.allocationCount} for k, r in nnfnodes.items() if r.allocationCount > 0]
            bodyJson = {
                "spec": {"allocationSets": [
                        {
                            "label": "xfs",
                            "allocationSize": minimumAlloc,
                            "storage": serverList
                        }
                    ]
                }
            }

            api_response = self.k8sapi.patch_namespaced_custom_object(group, version, serverNamespace, "servers", serverName, bodyJson)
            # print(f"api_response: {api_response}")

            Console.debug(Console.WORDY, api_response)
