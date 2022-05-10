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
from .Allocation import Allocation


class DirectiveBreakdown:
    """Encapsulates the DirectiveBreakdown CR."""
    def __init__(self, raw_breakdown):
        with Console.trace_function():
            if not raw_breakdown:
                raise Exception("raw_breakdown cannot be None")
            self._raw_breakdown = copy.deepcopy(raw_breakdown)

    @property
    def name(self):
        """Returns the DirectiveBreakdown name."""
        return self._raw_breakdown['metadata']['name']

    @property
    def dw_name(self):
        """Returns the #dw name."""
        return self._raw_breakdown['spec']['name']

    @property
    def dw(self):
        """Returns the #dw directive."""
        return self._raw_breakdown['spec']['dwRecord']['dwDirective']

    @property
    def server_obj(self):
        """Returns tuple with Server CR name and namespace."""
        if 'servers' not in self._raw_breakdown['status']:
            return None
        return [self._raw_breakdown['status']['servers']['name'],
                self._raw_breakdown['status']['servers']['namespace']]

    @property
    def allocationSet(self):
        """Returns a list of Allocation objects for this breakdown."""
        allocations = []
        allocationset = self._raw_breakdown['status']['allocationSet']
        for allocobj in allocationset:
            obj = Allocation(allocobj)
            allocations.append(obj)
        return allocations
