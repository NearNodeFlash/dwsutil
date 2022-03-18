# -----------------------------------------------------------------
# DWS unit tests
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
import copy
import unittest
import math
from unittest.mock import patch

from tests.TestUtil import TestUtil
from pkg.crd.Workflow import Workflow
from pkg.crd.Nnfnode import Nnfnode
from pkg.crd.Allocation import Allocation
from pkg.crd.DirectiveBreakdown import DirectiveBreakdown
from pkg.crd.Storage import Storage


class TestCRDs(unittest.TestCase, TestUtil):
    # *********************************************
    # * Class methods
    # *********************************************
    @classmethod
    def setUpClass(cls):
        TestUtil.setUpClass()

    @classmethod
    def tearDownClass(cls):
        pass

    # *********************************************
    # * Instance methods
    # *********************************************
    def setUp(self):
        json = Workflow.body_template("wfrtest", "wlm01", 999, 0, 1001, [])
        self.general_wfr = Workflow(json)

    def tearDown(self):
        pass

    async def on_cleanup(self):
        pass

    def create_general_nnfnode(self, allow_compute_name_munge=False):
        self.general_nnfnode = Nnfnode(TestUtil.NNFNODE_JSON, allow_compute_name_munge)

    # *********************************************
    # * Test methods
    # *********************************************
    def test_workflow_constructor_null_json(self):
        with self.assertRaises(RuntimeError) as ex:
            Workflow(None)
        self.assertTrue("cannot be None" in str(ex.exception))

    def test_workflow_constructor(self):
        json = Workflow.body_template("wfrtest", "wlm01", 999, 0, 1001, [])
        wfr = Workflow(json)
        self.assertEqual(wfr.name, "wfrtest")

    def test_workflow_constructor_deepcopy_1(self):
        json = Workflow.body_template("wfrtest-01", "wlm01", 999, 0, 1001, [])
        wfr1 = Workflow(json)
        wfr2 = Workflow(json)
        wfr2.name = "wfrtest-02"
        self.assertNotEqual(wfr1.name, wfr2.name)

    def test_workflow_constructor_deepcopy_2(self):
        json = Workflow.body_template("wfrtest-01", "wlm01", 999, 0, 1001, [])
        wfr1 = Workflow(json)
        wfr2 = Workflow(json)
        wfr2.raw_json = wfr1.raw_wfr
        wfr2.name = "wfrtest-02"
        self.assertNotEqual(wfr1.name, wfr2.name)

    def test_workflow_field_name(self):
        self.assertEqual(self.general_wfr.name, "wfrtest")

    def test_workflow_field_reason(self):
        wfr = Workflow(TestUtil.WFR_JSON)
        self.assertEqual(wfr.reason, "Completed")

    def test_workflow_field_reason_not_set(self):
        WFR = Workflow({"status": {}})
        self.assertEqual(WFR.reason, "")

    def test_workflow_field_message(self):
        wfr = Workflow(TestUtil.WFR_JSON)
        self.assertEqual(wfr.message, "Workflow proposal completed successfully")

    def test_workflow_field_message_not_set(self):
        WFR = Workflow({"status": {}})
        self.assertEqual(WFR.message, "")

    def test_workflow_field_breakdown_names(self):
        wfr = Workflow(TestUtil.WFR_JSON)
        self.assertEqual(len(wfr.directive_breakdown_names), 1)

    def test_workflow_field_breakdown_names_not_set(self):
        WFR = Workflow({"status": {}})
        self.assertEqual(len(WFR.directive_breakdown_names), 0)

    def test_workflow_field_compute_obj_name_not_set(self):
        WFR = Workflow({"status": {}})
        self.assertIsNone(WFR.compute_obj_name)

    def test_workflow_dump_summary(self):
        with patch("pkg.Console.Console.output"):
            self.general_wfr.dump_summary(raw_output=False)

    def test_nnfnode_constructor(self):
        self.create_general_nnfnode()
        self.assertEqual(self.general_nnfnode.status.lower(), "ready")

    def test_nnfnode_constructor_deepcopy(self):
        nnf1 = Nnfnode(TestUtil.NNFNODEBOGUSSERVERS_JSON)
        nnf2 = Nnfnode(TestUtil.NNFNODEBOGUSSERVERS_JSON)
        nnf1.servers.append({"name": "bogus"})
        self.assertTrue(len(nnf1.servers) != len(nnf2.servers))

    def test_nnfnode_constructor_with_munge(self):
        nnf_nomunge = Nnfnode(TestUtil.NNFNODEBOGUSSERVERS_JSON, allow_compute_name_munge=False)
        nnf_munge = Nnfnode(TestUtil.NNFNODEBOGUSSERVERS_JSON, allow_compute_name_munge=True)
        self.assertTrue(len(nnf_nomunge.servers) == len(nnf_munge.servers))
        self.assertNotEqual(nnf_munge.servers[0]['name'], nnf_nomunge.servers[0]['name'])

    def test_nnfnode_constructor_null_json(self):
        with self.assertRaises(BaseException) as ex:
            Nnfnode(None)
        self.assertTrue("cannot be None" in str(ex.exception))

    def test_nnfnode_constructor_missing_metadata(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"apiVersion": "na"})
        self.assertTrue("metadata" in str(ex.exception))

    def test_nnfnode_constructor_missing_status(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"metadata": {}})
        self.assertTrue("status" in str(ex.exception))

    def test_nnfnode_constructor_missing_namespace(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"metadata": {}, "status": {}})
        self.assertTrue("namespace" in str(ex.exception))

    def test_nnfnode_constructor_missing_name(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"metadata": {'namespace': 'default'}, "status": {}, "spec": {}})
        self.assertTrue("'name'" in str(ex.exception))

    def test_nnfnode_constructor_missing_capacity(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"metadata": {'namespace': 'default'}, "status": {}, "spec": {"name": "test"}})
        self.assertTrue("sub-fields" in str(ex.exception))

    def test_nnfnode_constructor_missing_substatus(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"metadata": {'namespace': 'default'}, "status": {"capacity": 1000000}, "spec": {"name": "test"}})
        self.assertTrue("sub-fields" in str(ex.exception))

    def test_nnfnode_constructor_missing_servers(self):
        with self.assertRaises(Exception) as ex:
            Nnfnode({"metadata": {'namespace': 'default'}, "status": {"capacity": 1000000, "servers": []}, "spec": {"name": "test"}})
        self.assertTrue("sub-fields" in str(ex.exception))

    def test_nnfnode_raw_getset(self):
        new_name = "new test name"
        node = Nnfnode(TestUtil.NNFNODE_JSON)
        raw_json = node.raw_nnfnode
        raw_json['spec']['name'] = new_name
        node.raw_nnfnode = raw_json
        self.assertEqual(new_name, node.name)

    def test_nnfnode_field_namespace(self):
        self.create_general_nnfnode()
        self.assertEqual(self.general_nnfnode.namespace.lower(), "default")

    def test_nnfnode_field_servers(self):
        self.create_general_nnfnode()
        self.assertEqual(len(self.general_nnfnode.computes), 1)

    def test_nnfnode_to_json(self):
        self.create_general_nnfnode()
        json = self.general_nnfnode.to_json()
        self.assertEqual(json["name"], self.general_nnfnode.name)

    def test_nnfnode_dump_summary(self):
        self.create_general_nnfnode()
        with patch("pkg.Console.Console.output"):
            self.general_nnfnode.dump_summary()

    def test_allocation_constructor(self):
        alloc = Allocation(TestUtil.ALLOC_JSON)
        self.assertEqual(alloc.label, "myalloc")

    def test_allocation_constructor_no_dict(self):
        with self.assertRaises(Exception) as ex:
            Allocation(None)
        self.assertTrue("cannot be None" in str(ex.exception))

    def test_allocation_field_colocation_constraints(self):
        alloc = Allocation(TestUtil.ALLOC_JSON)
        constraints = alloc.colocation_constraints
        self.assertTrue(len(constraints) > 0)

    def test_allocation_field_colocation_constraints_without_colocation(self):
        alloc = Allocation({"label": "myalloc", "allocationStrategy": "allocateacrossservers", "minimumCapacity": 1000000, "constraints": {}})
        constraints = alloc.colocation_constraints
        self.assertIsNone(constraints)
        self.assertFalse(alloc.has_colocation_constraints)

    def test_allocation_field_colocation_constraints_empty_colocation(self):
        alloc = Allocation({"label": "myalloc", "allocationStrategy": "allocateacrossservers", "minimumCapacity": 1000000, "constraints": {"colocation": []}})
        self.assertFalse(alloc.has_colocation_constraints)

    def test_allocation_field_colocation_constraints_without_constraints(self):
        alloc = Allocation({"label": "myalloc", "allocationStrategy": "allocateacrossservers", "minimumCapacity": 1000000})
        constraints = alloc.colocation_constraints
        self.assertIsNone(constraints)
        self.assertFalse(alloc.has_colocation_constraints)

    def test_allocation_field_has_colocation_constraints(self):
        alloc = Allocation(TestUtil.ALLOC_JSON)
        self.assertTrue(alloc.has_colocation_constraints)

    def test_allocation_field_is_across_servers(self):
        json = copy.deepcopy(TestUtil.ALLOC_JSON)
        json["allocationStrategy"] = "allocateacrossservers"
        alloc = Allocation(json)
        self.assertTrue(alloc.is_across_servers)

    def test_allocation_field_is_single_server(self):
        json = copy.deepcopy(TestUtil.ALLOC_JSON)
        json["allocationStrategy"] = "allocatesingleserver"
        alloc = Allocation(json)
        self.assertTrue(alloc.is_single_server)

    def test_allocation_field_is_per_compute(self):
        json = copy.deepcopy(TestUtil.ALLOC_JSON)
        json["allocationStrategy"] = "allocatepercompute"
        alloc = Allocation(json)
        self.assertTrue(alloc.is_per_compute)

    def test_allocation_dump_summary(self):
        with patch("pkg.Console.Console.output"):
            alloc = Allocation(TestUtil.ALLOC_JSON)
            alloc.dump_summary(raw_output=False)

    def test_directivebreakdown_constructor(self):
        breakdown = DirectiveBreakdown(TestUtil.BREAKDOWN_JSON)
        self.assertEqual(breakdown.name, "mybreakdown")

    def test_directivebreakdown_constructor_no_dict(self):
        with self.assertRaises(Exception) as ex:
            DirectiveBreakdown(None)
        self.assertTrue("cannot be None" in str(ex.exception))

    def test_directivebreakdown_field_server_obj(self):
        breakdown = DirectiveBreakdown(TestUtil.BREAKDOWN_JSON)
        server_obj = breakdown.server_obj
        self.assertEqual(server_obj[0], "w-0")
        self.assertEqual(server_obj[1], "default")

    def test_directivebreakdown_field_server_obj_server_missing(self):
        breakdown = DirectiveBreakdown(TestUtil.BREAKDOWNNOSERVERS_JSON)
        server_obj = breakdown.server_obj
        self.assertIsNone(server_obj)

    def test_directivebreakdown_field_allocation_set(self):
        breakdown = DirectiveBreakdown(TestUtil.BREAKDOWN_JSON)
        allocationSet = breakdown.allocationSet
        self.assertTrue(len(allocationSet) == 1)

    def test_storage_constructor(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        self.assertEqual(storage.name, TestUtil.STORAGE_JSON["metadata"]["name"])

    def test_storage_constructor_no_json(self):
        with self.assertRaises(Exception) as ex:
            Storage(None)
        self.assertTrue("is required" in str(ex.exception))

    def test_storage_field_raw_storage(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        json = storage.raw_storage
        json["metadata"]["name"] = "SetterTest"
        storage.raw_storage = json
        self.assertEqual(storage.name, "SetterTest")

    def test_storage_field_is_ready(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        self.assertTrue(storage.is_ready)

    def test_storage_field_status(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        self.assertEqual(storage.status, "Ready")

    def test_storage_field_capacity(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        self.assertEqual(storage.capacity, TestUtil.STORAGE_JSON['data']['capacity'])

    def test_storage_field_comuptes(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        self.assertEqual(len(storage.computes), 16)

    def test_storage_has_sufficient_capacity(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        self.assertTrue(storage.has_sufficient_capacity(1000000))

    def test_storage_allocs_remaining(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        allocsize = 1000000000
        remaining = math.floor(storage.remaining_storage / allocsize)

        allocsremaining = storage.allocs_remaining(allocsize)
        self.assertEqual(allocsremaining, remaining)

    def test_storage_to_json(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        json = storage.to_json()
        self.assertEqual(storage.name, json["name"])
        self.assertEqual(storage.status, json["status"])
        self.assertEqual(storage.capacity, json["capacity"])
        self.assertEqual(len(storage.computes), len(json["computes"]))

    def test_storage_dump_summary(self):
        storage = Storage(TestUtil.STORAGE_JSON)
        with patch("pkg.Console.Console.output"):
            storage.dump_summary()


if __name__ == '__main__':
    unittest.main()
