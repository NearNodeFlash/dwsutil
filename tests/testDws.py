# -----------------------------------------------------------------
# DWS unit tests
#
# Author: Bill Johnson (billj@hpe.com)
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
import unittest
from unittest.mock import patch

import kubernetes.client

from tests.TestUtil import TestUtil
# from pkg.Console import Console
from pkg.Config import Config
from pkg.Dws import DWS, DWSError
from pkg.crd.Storage import Storage
from pkg.crd.Workflow import Workflow


class TestDWS(unittest.TestCase, TestUtil):
    # *********************************************
    # * Class methods
    # *********************************************
    @classmethod
    def setUpClass(cls):
        TestUtil.setUpClass()
        pass

    @classmethod
    def tearDownClass(cls):
        pass

    # *********************************************
    # * Instance methods
    # *********************************************
    def setUp(self):
        self.args = ["dwsutil", "-c", "tests/sample.cfg"]
        self.config = Config(self.args)
        self.dws = DWS(self.config)

    def tearDown(self):
        pass

    async def on_cleanup(self):
        pass

    # *********************************************
    # * side effect methods
    # * Used by mock to control return values
    # *********************************************
    def side_effect_wfr_get(self, *args, **kwargs):
        # print(f"{args}")
        if args[4] == "notfound":
            raise kubernetes.client.exceptions.ApiException(status=404, reason="Not Found")

        the_json = TestUtil.WFR_JSON
        the_json["metadata"]["name"] = args[4]

        if args[4] in ["wfr-refresh"]:
            the_json["spec"]["jobID"] = next(TestUtil.number_gen)
            # the_json["spec"]["jobID"] = TestDWS.get_counter()

        if args[4] in ["delete-badstate"]:
            the_json["status"]["state"] = "proposal"

        if args[4] == "notready":
            the_json["status"]["state"] = "proposal"
            the_json["spec"]["desiredState"] = "setup"
            the_json["status"]["ready"] = False

        if args[4] == "delete-teardownstate":
            the_json["status"]["state"] = "teardown"
            the_json["spec"]["desiredState"] = "teardown"
            the_json["status"]["ready"] = True

        return the_json

    def side_effect_wfr_create(self, *args, **kwargs):
        if args[4] == "dupe":
            raise kubernetes.client.exceptions.ApiException(status=409, reason="Conflict")

        the_json = args[4]

        return the_json

    def side_effect_wfr_desiredstate_notfound(self, *args, **kwargs):
        raise kubernetes.client.exceptions.ApiException(status=404, reason="Not Found")

    def side_effect_breakdown_get(self, *args, **kwargs):
        if args[4] == "notfound":
            raise kubernetes.client.exceptions.ApiException(status=404, reason="Not Found")

        the_json = TestUtil.BREAKDOWN_JSON
        the_json["metadata"]["name"] = args[4]

        return the_json

    # *********************************************
    # * Test methods
    # *********************************************
    def test_dws_error_constructor(self):
        err = DWSError("test message", 99, "raw string")
        self.assertEqual(err.code, 99)
        self.assertEqual(err.message, "test message")
        self.assertEqual(err.raw, "raw string")

    def test_dws_error_json(self):
        err = DWSError("test message", 99, "raw string")
        json = err.to_json()
        self.assertEqual(json["dwserrorcode"], 99)
        self.assertEqual(json["message"], "test message")

    def test_dws_crd_get_raw(self):
        test_wfr_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            val = self.dws.crd_get_raw("workflows", test_wfr_name)
            self.assertEqual(val["metadata"]["name"], test_wfr_name)

    def test_dws_crd_get_raw_notfound(self):
        test_wfr_name = "notfound"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            with self.assertRaises(DWSError) as ex:
                self.dws.crd_get_raw("workflows", test_wfr_name)
            self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_wfr_list_names(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.list_cluster_custom_object") as function_mock:
            function_mock.return_value = TestUtil.WFRLIST_JSON
            wfrlist = self.dws.wfr_list_names()
            self.assertEqual(len(wfrlist), 2)

    def test_dws_wfr_get_raw(self):
        test_wfr_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            val = self.dws.wfr_get_raw(test_wfr_name)
            self.assertEqual(val["metadata"]["name"], test_wfr_name)

    def test_dws_wfr_get_raw_notfound(self):
        test_wfr_name = "notfound"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            with self.assertRaises(DWSError) as ex:
                self.dws.wfr_get_raw(test_wfr_name)
            self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_wfr_get(self):
        test_wfr_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            val = self.dws.wfr_get(test_wfr_name)
            self.assertEqual(val.name, test_wfr_name)

    def test_dws_wfr_get_notfound(self):
        test_wfr_name = "notfound"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            with self.assertRaises(DWSError) as ex:
                self.dws.wfr_get(test_wfr_name)
            self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_wfr_delete_notfound(self):
        test_wfr_name = "notfound"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.delete_namespaced_custom_object") as function_mock_delete:
                function_mock_delete.side_effect = self.side_effect_wfr_get
                function_mock_delete.return_value = TestUtil.WFR_JSON
                with self.assertRaises(DWSError) as ex:
                    self.dws.wfr_delete(test_wfr_name)
                self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_wfr_delete_badstate(self):
        test_wfr_name = "delete-badstate"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.delete_namespaced_custom_object") as function_mock_delete:
                function_mock_delete.side_effect = self.side_effect_wfr_get
                function_mock_delete.return_value = TestUtil.WFR_JSON
                with self.assertRaises(DWSError) as ex:
                    self.dws.wfr_delete(test_wfr_name)
                self.assertEqual(ex.exception.code, DWSError.DWS_IMPROPERSTATE)

    def test_dws_wfr_delete_teardownstate(self):
        test_wfr_name = "delete-teardownstate"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.delete_namespaced_custom_object") as function_mock_delete:
                function_mock_delete.side_effect = self.side_effect_wfr_get
                function_mock_delete.return_value = TestUtil.WFR_JSON
                self.dws.wfr_delete(test_wfr_name)

    def test_dws_wfr_create(self):
        test_wfr_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.create_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_create
            function_mock_get.return_value = TestUtil.WFR_JSON
            wfr = self.dws.wfr_create(test_wfr_name, ["#dw01"], 111, "Flux01", 333)
            self.assertEqual(wfr.name, test_wfr_name)
            self.assertEqual(wfr.userID, 111)
            self.assertEqual(wfr.jobID, 333)
            self.assertEqual(wfr.wlmID, "Flux01")
            self.assertTrue("#dw01" in wfr.dwDirectives)

    def test_dws_wfr_get_next_state(self):
        # Normal transition tests
        self.assertEqual(self.dws.wfr_get_next_state("proposal"), "setup")
        self.assertEqual(self.dws.wfr_get_next_state("setup"), "data_in")
        self.assertEqual(self.dws.wfr_get_next_state("data_in"), "pre_run")
        self.assertEqual(self.dws.wfr_get_next_state("pre_run"), "post_run")
        self.assertEqual(self.dws.wfr_get_next_state("post_run"), "data_out")
        self.assertEqual(self.dws.wfr_get_next_state("data_out"), "teardown")

        # Case insensitivity tests
        self.assertEqual(self.dws.wfr_get_next_state("DaTa_Out"), "teardown")

        # Invalid state tests
        self.assertIsNone(self.dws.wfr_get_next_state("teardown"))

        # Bogus state tests
        with self.assertRaises(DWSError) as ex:
            self.assertIsNone(self.dws.wfr_get_next_state("bogusState"))
        self.assertEqual(ex.exception.code, DWSError.DWS_GENERAL)

    def test_dws_wfr_update_desiredstate(self):
        test_wfr_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.patch_namespaced_custom_object") as function_mock_patch:
                function_mock_patch.side_effect = self.side_effect_wfr_get
                function_mock_patch.return_value = TestUtil.WFR_JSON
                self.dws.wfr_update_desired_state(test_wfr_name, "setup")

    def test_dws_wfr_update_desiredstate_notfound(self):
        test_wfr_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.patch_namespaced_custom_object") as function_mock_patch:
                function_mock_patch.side_effect = self.side_effect_wfr_desiredstate_notfound
                function_mock_patch.return_value = TestUtil.WFR_JSON
                with self.assertRaises(DWSError) as ex:
                    self.dws.wfr_update_desired_state(test_wfr_name, "setup")
                self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_wfr_update_desiredstate_notready(self):
        test_wfr_name = "notready"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.patch_namespaced_custom_object") as function_mock_patch:
                function_mock_patch.side_effect = self.side_effect_wfr_get
                function_mock_patch.return_value = TestUtil.WFR_JSON
                with self.assertRaises(DWSError) as ex:
                    self.dws.wfr_update_desired_state(test_wfr_name, "setup")
                self.assertEqual(ex.exception.code, DWSError.DWS_IMPROPERSTATE)

    def test_dws_wfr_update_desiredstate_notready_force(self):
        test_wfr_name = "notready"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.patch_namespaced_custom_object") as function_mock_patch:
                function_mock_patch.side_effect = self.side_effect_wfr_get
                function_mock_patch.return_value = TestUtil.WFR_JSON
                self.dws.wfr_update_desired_state(test_wfr_name, "setup", force_update=True)

    def test_dws_wfr_refresh(self):
        test_wfr_name = "wfr-refresh"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_wfr_get
            function_mock.return_value = TestUtil.WFR_JSON
            wfr = self.dws.wfr_get(test_wfr_name)
            orig_jobid = wfr.jobID
            self.dws.wfr_refresh(wfr)
            self.assertNotEqual(wfr.jobID, orig_jobid)

    def test_dws_breakdown_get_raw(self):
        test_breakdown_name = "mybreakdown"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_breakdown_get
            function_mock.return_value = TestUtil.WFR_JSON
            json = self.dws.directivebreakdown_get_raw(test_breakdown_name)
            self.assertEqual(json["metadata"]["name"], test_breakdown_name)

    def test_dws_breakdown_get_raw_notfound(self):
        test_breakdown_name = "notfound"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_breakdown_get
            function_mock.return_value = TestUtil.WFR_JSON
            with self.assertRaises(DWSError) as ex:
                self.dws.directivebreakdown_get_raw(test_breakdown_name)
            self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_breakdown_get(self):
        test_breakdown_name = "mybreakdown"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_breakdown_get
            function_mock.return_value = TestUtil.WFR_JSON
            breakdown = self.dws.directivebreakdown_get(test_breakdown_name)
            self.assertEqual(breakdown.name, test_breakdown_name)

    def test_dws_breakdown_get_notfound(self):
        test_breakdown_name = "notfound"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_breakdown_get
            function_mock.return_value = TestUtil.WFR_JSON
            with self.assertRaises(DWSError) as ex:
                self.dws.directivebreakdown_get(test_breakdown_name)
            self.assertEqual(ex.exception.code, DWSError.DWS_NOTFOUND)

    def test_dws_wfr_getbreakdowns(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_breakdown_get
            function_mock.return_value = TestUtil.WFR_JSON
            wfr = Workflow(TestUtil.WFR_JSON)
            breakdowns = self.dws.wfr_get_directiveBreakdowns(wfr)
            self.assertEqual(len(breakdowns), 1)

    def test_dws_update_computes(self):
        test_breakdown_name = TestUtil.random_wfr()
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock_get:
            function_mock_get.side_effect = self.side_effect_wfr_get
            function_mock_get.return_value = TestUtil.WFR_JSON
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.patch_namespaced_custom_object") as function_mock:
                function_mock.side_effect = self.side_effect_breakdown_get
                function_mock.return_value = TestUtil.WFR_JSON
                wfr = self.dws.wfr_get(test_breakdown_name)
                self.dws.wfr_update_computes(wfr, ['c1', 'c2'])

    def test_dws_update_servers(self):
        test_breakdown_name = "mybreakdown"
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.side_effect = self.side_effect_breakdown_get
            function_mock.return_value = TestUtil.WFR_JSON
            breakdown = self.dws.directivebreakdown_get(test_breakdown_name)
            self.assertEqual(breakdown.name, test_breakdown_name)
            with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.patch_namespaced_custom_object") as function_mock:
                function_mock.side_effect = self.side_effect_breakdown_get
                function_mock.return_value = TestUtil.WFR_JSON
                node = Storage(TestUtil.STORAGE_JSON)
                nodes = {node.name: node}
                self.dws.wfr_update_servers(breakdown, 1000, nodes)

    def test_dws_inventory_build_from_cluster(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.list_cluster_custom_object") as function_mock:
            function_mock.return_value = TestUtil.STORAGELIST_JSON
            nnfnodelist = self.dws.inventory_build_from_cluster(only_ready_storage=False)
            self.assertEqual(len(nnfnodelist), 2)
            for nodename, node in nnfnodelist.items():
                self.assertEqual(len(node.computes), 16)

    def test_dws_inventory_build_from_cluster_only_ready(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.list_cluster_custom_object") as function_mock:
            function_mock.return_value = TestUtil.STORAGELIST_JSON
            nnfnodelist = self.dws.inventory_build_from_cluster(only_ready_storage=True)
            self.assertEqual(len(nnfnodelist), 1)

    def test_dws_storage_list_names(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.list_cluster_custom_object") as function_mock:
            function_mock.return_value = TestUtil.STORAGELIST_JSON
            nnfnodelist = self.dws.storage_list_names()
            self.assertEqual(len(nnfnodelist), 2)

    def test_dws_storage_get(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.get_namespaced_custom_object") as function_mock:
            function_mock.return_value = TestDWS.STORAGE_JSON
            storage = self.dws.storage_get("test")
            self.assertEqual(storage.name, "kind-worker")

    def test_dws_storage_get_all(self):
        with patch("kubernetes.client.api.custom_objects_api.CustomObjectsApi.list_cluster_custom_object") as function_mock:
            function_mock.return_value = TestUtil.STORAGELIST_JSON
            nnfnodelist = self.dws.storage_get_all()
            self.assertEqual(len(nnfnodelist), 2)

    def test_dws_pods_list(self):
        with patch("kubernetes.client.api.core_v1_api.CoreV1Api.list_pod_for_all_namespaces") as function_mock:
            function_mock.return_value = []
            pods = self.dws.pods_list()
            self.assertTrue(len(pods) == 0)

    def test_dws_node_list(self):
        with patch("kubernetes.client.api.core_v1_api.CoreV1Api.list_node") as function_mock:
            function_mock.return_value = []
            nodes = self.dws.node_list()
            self.assertTrue(len(nodes) == 0)

    def test_dws_crd_list(self):
        with patch("kubernetes.client.api.apiextensions_v1_api.ApiextensionsV1Api.list_custom_resource_definition") as function_mock:
            function_mock.return_value = []
            crds = self.dws.crd_list()
            self.assertTrue(len(crds) == 0)


if __name__ == '__main__':
    unittest.main()
