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

# import kubernetes.client

from tests.TestUtil import TestUtil
from pkg.DWSUtility import DWSUtility


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

    def tearDown(self):
        pass

    async def on_cleanup(self):
        pass

    # *********************************************
    # * side effect methods
    # * Used by mock to control return values
    # *********************************************
    def side_effect_arguments(self, *args, **kwargs):
        return self.args

    # *********************************************
    # * Test methods
    # *********************************************
    def test_dwsutility_get_commandline_args(self):
        args = DWSUtility.command_line_args()
        # print(args)
        self.assertTrue(len(args) > 0)

    def test_dwsutility_constructor(self):
        with patch("pkg.DWSUtility.DWSUtility.command_line_args") as function_mock:
            function_mock.return_value = self.args
            dwsu = DWSUtility(".")
            self.assertTrue(dwsu.config is not None)

    def util_get_fake_inventory(self):
        return None

    def test_dwsutility_assign_resources_xfs(self):
        with patch("pkg.DWSUtility.DWSUtility.command_line_args") as function_mock:
            function_mock.return_value = self.args
            with patch("pkg.Dws.DWS.inventory_build_from_cluster") as inv_mock:
                inv_mock.side_effect = self.util_get_fake_inventory
                dwsu = DWSUtility(".")

                # dwsu.config.output_configuration()
                # inv = dwsu.do_get_inventory()
                # print(inv)
                # dwsu.do_assign_resources()

            self.assertTrue(dwsu.config is not None)
