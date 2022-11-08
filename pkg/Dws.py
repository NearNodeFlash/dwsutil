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
# DWS Utility Configuration Class

import copy
import os
import sys

import kubernetes.client as k8s_client
import kubernetes.watch as k8s_watch

from .Console import Console
from .crd.Workflow import Workflow
from .crd.DirectiveBreakdown import DirectiveBreakdown
from .crd.Storage import Storage


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
    DWS_INSUFFICIENT_RESOURCES = 108

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
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)  # pragma: no cover

    # Inventory Routines
    def inventory_build_from_cluster(self, only_ready_storage=False, group="dws.cray.hpe.com", version="v1alpha1"):
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
                storage_list = crd_api.list_cluster_custom_object(group, version, "storages")

                if Console.level_enabled(Console.WORDY):
                    Console.pretty_json(storage_list)

                for storage in storage_list['items']:
                    storage_obj = Storage(storage)
                    if only_ready_storage and not storage_obj.is_ready:
                        Console.debug(Console.MIN, f"...storage-node {storage_obj.name}"
                                                   " is not ready, skipping")
                        continue
                    nnf_inventory[storage_obj.name] = storage_obj
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

    def list_cluster_custom_object(self, plural, group, version="v1alpha1"):
        """Retrieve a list of resource objects of a specified kind, across namespaces

        Parameters:
        plural: Kind of the CRD, in plural form
        group: Group of the CRD

        Returns:
        a list of resource objects of the given kind, across all namespaces
        """

        with Console.trace_function():
            resources = []
            crd_api = k8s_client.CustomObjectsApi()
            try:
                res_list = crd_api.list_cluster_custom_object(group, version, plural)
                for res in res_list['items']:
                    resources.append(copy.deepcopy(res))
                return resources
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def get_custom_resource_definition(self, crd_name):
        """Retrieve a Custom Resource Definition (CRD) object

        Parameters:
        crd_name: Name of the CRD.  Ex: workflows.dws.cray.hpe.com

        Returns:
        An object of type V1CustomResourceDefinition.
        """

        # The ApiextensionsV1Api.list_custom_resource_definition() is a
        # heavy hammer.  The following is more targeted.
        with Console.trace_function():
            api = k8s_client.ApiClient()
            try:
                crd_obj, _, _ = api.call_api(
                    f"/apis/apiextensions.k8s.io/v1/customresourcedefinitions/{crd_name}",
                    'GET',
                    response_type='V1CustomResourceDefinition')
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

            return crd_obj

    def remove_custom_resource_finalizers(self, crd_name):
        """Remove Custom Resources Finalizers identified by CRD Name

        Parameters:
        crd_name: Name of the CRD.  Ex: workflows.dws.cray.hpe.com

        Returns:
        list: List of results, each entry a list of [namespace, name, result]
        """

        if isinstance(crd_name, list):
            crd_name = crd_name[0]

        plural, _, group = crd_name.partition(".")

        try:
            crd_obj = self.get_custom_resource_definition(crd_name)
        except Exception:
            return None

        version = crd_obj.spec.versions[0].name

        resources = self.list_cluster_custom_object(plural, group)

        results = []
        for r in resources:
            name = r['metadata']['name']
            namespace = r['metadata']['namespace']
            result = "PASS"

            try:
                with Console.trace_function():
                    print(group, version, namespace, plural, name)
                    body = {"metadata": {"finalizers": []}}
                    self.k8sapi.patch_namespaced_custom_object(group, version, namespace, plural, name, body)
            except Exception as e:
                result = str(e)

            results.append([namespace, name, result])
        return results

    def get_crd_printer_columns(self, crd_obj):
        """ Retrieve the additionalPrinterColumns from a given CRD.

        Parameters:
        crd_obj: An object of type V1CustomResourceDefinition.

        Returns:
        An list-like object of type V1CustomResourceDefinitionVersion, containing elements of type V1CustomResourceColumnDefinition.
        """

        if not isinstance(crd_obj, k8s_client.V1CustomResourceDefinition):
            raise DWSError("Expected V1CustomResourceDefinition", 0, "")
        spec = crd_obj.spec
        versions = spec.versions
        cols = versions[0].additional_printer_columns
        return cols

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

    def wfr_wait_for_ready(self, wfrname, timeout_seconds, group="dws.cray.hpe.com", version="v1alpha1"):
        """Waits a number of seconds for a named Workflow CR to have a Ready status

        Parameters:
        wfrname : Name of the Workflow CR
        timeout_seconds: Number of seconds to wait

        Returns:
        Workflow as JSON if Workflow resource is Ready or deleted, None otherwise
        """

        with Console.trace_function():
            crd_api = k8s_client.CustomObjectsApi()
            try:
                watch = k8s_watch.Watch()
                for event in watch.stream(crd_api.list_cluster_custom_object, group, version, "workflows", timeout_seconds=timeout_seconds):
                    if event['type'] == 'ADDED':
                        continue
                    workflow = Workflow(event['object'])
                    if workflow.name == wfrname:
                        if event['type'] == 'DELETED':
                            raise DWSError(f"Workflow {wfrname} deleted", DWSError.DWS_GENERAL)
                        if workflow.is_ready:
                            return workflow
            except k8s_client.exceptions.ApiException as err:  # pragma: no cover
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)
            raise DWSError(f"Timeout waiting for Workflow {wfrname}", DWSError.DWS_GENERAL)

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
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)  # pragma: no cover

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
                raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)  # pragma: no cover

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
            if wfr.is_ready and wfr.state == "Teardown":
                api_response = self.k8sapi.delete_namespaced_custom_object(group, version, "default", "workflows", wfrname)
                Console.debug(Console.WORDY, api_response)
            else:
                msg = f"Workflow Resource named '{wfrname}' must be in a state of 'Teardown' to be deleted, current state is '{wfr.state}'"
                raise DWSError(msg, DWSError.DWS_IMPROPERSTATE, None)
        except k8s_client.exceptions.ApiException as err:  # pragma: no cover
            if err.status == 404:
                msg = f"Workflow Resource named '{wfrname}' was not found"
                raise DWSError(msg, DWSError.DWS_NOTFOUND, err)
            raise DWSError(err.body, DWSError.DWS_K8S_ERROR, err)

    def wfr_create(self, wfrname, dwdirectives, userId, groupId, wlmId, jobId, new_client=None, group="dws.cray.hpe.com", version="v1alpha1"):
        """Create a new Workflow CR.

        Parameters:
        name : Name of the Workflow CR
        dwdirectives : Any array of #dw strings
        userId : User ID
        groupId : Group ID
        wlmId: Valid WLM id
        jobId: Valid job id
        new_client - DEPRECATED, will be refactored

        Returns:
        Created Workflow object
        """

        with Console.trace_function():
            body = Workflow.body_template(wfrname, wlmId, jobId, userId, groupId, dwdirectives, "Proposal", group, version)
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
        states = ['Proposal', 'Setup', 'DataIn', 'PreRun', 'PostRun', 'DataOut', 'Teardown']
        try:
            idx = states.index(state)
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
            if err.status == 404:  # pragma: no cover
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

    def wfr_update_servers(self, breakdown, group="dws.cray.hpe.com", version="v1alpha1"):
        """Update servers(nnfnodes) for a given Workflow.

        Parameters:
        wfr : Workflow to update computes for
        nnfnodes : List of servers nnfnodes for the Workflow

        Returns:
        Nothing
        """

        with Console.trace_function():
            serverName, serverNamespace = breakdown['serverObj']

            bodyJson = {
                "spec": {"allocationSets": breakdown["allocationSet"]}
            }

            if Console.level_enabled(Console.WORDY):
                Console.pretty_json(bodyJson)
                Console.output(Console.HALF_BAR)

            api_response = self.k8sapi.patch_namespaced_custom_object(group, version, serverNamespace, "servers", serverName, bodyJson)

            Console.debug(Console.WORDY, api_response)

    # TODO: Remove
    def wfr_update_servers_orig(self, breakdown, minimumAlloc, nnfnodes, group="dws.cray.hpe.com", version="v1alpha1"):
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
                        }]
                }
            }

            api_response = self.k8sapi.patch_namespaced_custom_object(group, version, serverNamespace, "servers", serverName, bodyJson)
            # print(f"api_response: {api_response}")

            Console.debug(Console.WORDY, api_response)
