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

import unittest
from unittest.mock import patch

from tests.TestUtil import TestUtil
from pkg.Config import Config


class TestArgs(unittest.TestCase, TestUtil):
    # *********************************************
    # * Class methods
    # *********************************************
    @classmethod
    def setUpClass(cls):
        TestUtil.setUpClass()
        pass

    # *********************************************
    # * Test methods
    # *********************************************
    def test_arg_workflow_name(self):
        wfr_name = "myname"
        args = ["dwsutil", "-n", wfr_name, "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.wfr_name, wfr_name)

    def test_arg_munge_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.munge, False)

    def test_arg_munge(self):
        args = ["dwsutil", "--munge", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.munge, True)

    def test_arg_quiet_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.quiet, False)

    def test_arg_quiet(self):
        args = ["dwsutil", "-q", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.quiet, True)

    def test_arg_preview_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.preview, False)

    def test_arg_preview(self):
        args = ["dwsutil", "--preview", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.preview, True)

    def test_arg_verbosity_0(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.verbosity, 0)

    def test_arg_verbosity_1(self):
        with patch("pkg.Console.Console.output"):
            args = ["dwsutil", "-v", "-c", "tests/empty.cfg"]
            config = Config(args)
            self.assertEqual(config.verbosity, 1)

    def test_arg_verbosity_2(self):
        with patch("pkg.Console.Console.output"):
            args = ["dwsutil", "-v", "-v", "-c", "tests/empty.cfg"]
            config = Config(args)
            self.assertEqual(config.verbosity, 2)

    def test_arg_configfile(self):
        config_file = "tests/sample.cfg"
        args = ["dwsutil", "-c", config_file]
        config = Config(args)
        self.assertEqual(config.config_file, config_file)

    def test_arg_k8sconfigfile(self):
        config_file = "tests/sample.kube"
        args = ["dwsutil", "-k", config_file, "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.k8s_config, config_file)

    def test_arg_jobid_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.job_id, 5555)

    def test_arg_jobid(self):
        args = ["dwsutil", "--jobid", "777", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.job_id, 777)

    def test_arg_userid_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.user_id, 1001)

    def test_arg_userid(self):
        args = ["dwsutil", "--userid", "99", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.user_id, 99)

    def test_arg_groupid_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.group_id, 0)

    def test_arg_groupid(self):
        args = ["dwsutil", "--groupid", "99", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.group_id, 99)

    def test_arg_wlmid(self):
        args = ["dwsutil", "--wlmid", "wlmXX", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.wlm_id, "wlmXX")

    def test_arg_context_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.context, "WFR")

    def test_arg_context(self):
        args = ["dwsutil", "--context", "INVENTORY", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.context, "INVENTORY")

    def test_arg_operation_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.operation, "")

    def test_arg_operation(self):
        args = ["dwsutil", "--operation", "LIST", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.operation, "LIST")

    def test_arg_dw(self):
        args = ["dwsutil", "-c", "tests/empty.cfg", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(len(config.dwdirectives), 0)

    def test_arg_dw_multiple(self):
        args = ["dwsutil", "-c", "tests/empty.cfg", "--dw", "dw 1", "--dw", "dw 2"]
        config = Config(args)
        self.assertEqual(len(config.dwdirectives), 2)
        self.assertTrue("dw 1" in config.dwdirectives)

    def test_arg_exr_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(len(config.exclude_rabbits), 0)

    def test_arg_exr(self):
        args = ["dwsutil", "-c", "tests/empty.cfg", "--exr", "r1,r2,r3"]
        config = Config(args)
#        config.output_configuration()
        self.assertEqual(len(config.exclude_rabbits), 3)
        self.assertTrue("r1" in config.exclude_rabbits)
        self.assertTrue("r2" in config.exclude_rabbits)
        self.assertTrue("r3" in config.exclude_rabbits)

    def test_arg_exc_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(len(config.exclude_rabbits), 0)

    def test_arg_dw_exc(self):
        args = ["dwsutil", "-c", "tests/empty.cfg", "--exc", "c1,c2,c3"]
        config = Config(args)
        self.assertEqual(len(config.exclude_computes), 3)
        self.assertTrue("c1" in config.exclude_computes)
        self.assertTrue("c2" in config.exclude_computes)
        self.assertTrue("c3" in config.exclude_computes)

    def test_arg_inventory_file(self):
        filename = "tests/empty.inv"
        args = ["dwsutil", "-i", filename, "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.inventory_file, filename)

    def test_arg_nodes_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.nodes, 1)

    def test_arg_nodecount(self):
        args = ["dwsutil", "--nodes", "5", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.nodes, 5)

    def test_arg_regex_default(self):
        args = ["dwsutil", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.regexEnabled, False)

    def test_arg_regex(self):
        args = ["dwsutil", "--regex", "-c", "tests/empty.cfg"]
        config = Config(args)
        self.assertEqual(config.regexEnabled, True)

    def test_config_load(self):
        args = ["dwsutil", "-c", "tests/sample.cfg"]
        config = Config(args)
#        config.output_configuration()
        self.assertEqual(config.user_id, 1234)
        self.assertEqual(config.job_id, 987)
        self.assertEqual(config.wlm_id, "flux01")
        self.assertEqual(config.wfr_name, "mywfr")
        self.assertEqual(config.nodes, 2)
        self.assertTrue("compute 0" in config.exclude_computes)
        self.assertTrue("rabbit-node-123" in config.exclude_rabbits)
        self.assertTrue(len(config.dwdirectives) == 1)


if __name__ == '__main__':
    unittest.main()
