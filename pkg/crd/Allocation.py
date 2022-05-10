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

import copy

from ..Console import Console


class Allocation:
    """Encapsulates the Allocation component of a DirectiveBreakdown."""
    def __init__(self, alloc_dict):
        """init cherry picks the fields of the Allocation we care about."""
        with Console.trace_function():
            if not alloc_dict:
                raise Exception("alloc_dict cannot be None")
            self.dict = copy.deepcopy(alloc_dict)
            self.label = alloc_dict['label']
            self.allocationStrategy = alloc_dict['allocationStrategy'].lower()
            self.minimumCapacity = alloc_dict['minimumCapacity']

    @property
    def colocation_constraints(self):
        """Returns any colocation constraints specified in the Allocation."""
        constraints = None
        if 'constraints' in self.dict:
            if 'colocation' in self.dict['constraints']:
                constraints = self.dict['constraints']['colocation']
        return constraints

    @property
    def has_colocation_constraints(self):
        """True if any colocation constraints exist."""
        if 'constraints' in self.dict:
            if 'colocation' in self.dict['constraints']:
                if len(self.dict['constraints']['colocation']) > 0:
                    return True
        return False

    @property
    def is_across_servers(self):
        """True if the allocation strategy is 'allocateacrossservers'"""
        return self.allocationStrategy == "allocateacrossservers"

    @property
    def is_single_server(self):
        """True if the allocation strategy is 'allocatesingleserver'"""
        return self.allocationStrategy == "allocatesingleserver"

    @property
    def is_per_compute(self):
        """True if the allocation strategy is 'allocatepercompute'"""
        return self.allocationStrategy == "allocatepercompute"

    def dump_summary(self, raw_output=False):
        """Dump object summary to console"""
        Console.output(Console.HALF_BAR)
        Console.output("Allocation")
        if raw_output:  # pragma: no cover
            Console.output(self.raw_json)
        else:
            Console.output(f"     label: {self.label}")
            Console.output(f"     allocationStrategy: {self.allocationStrategy}")
            Console.output(f"     minimumCapacity: {self.minimumCapacity}")
            Console.output(f"     has colocation constraints: {self.has_colocation_constraints}")
            Console.output(f"     colocation constraints: {self.colocation_constraints}")
