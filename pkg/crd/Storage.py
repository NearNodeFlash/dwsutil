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
import math

from ..Console import Console


class Storage:
    """Encapsulates the Storage CR."""
    def __init__(self, raw_storage):
        with Console.trace_function():
            if not raw_storage:
                raise Exception("raw_storage is required")
            self._raw_storage = copy.deepcopy(raw_storage)
            self.remaining_storage = self.capacity
            self.allocationCount = 0

    @property
    def raw_storage(self):
        """Returns the internal json for the Storage."""
        return self._raw_storage

    @raw_storage.setter
    def raw_storage(self, raw_storage):
        """Setter for the internal Storage json."""
        self._raw_storage = copy.deepcopy(raw_storage)

    @property
    def name(self):
        """Returns the Storage name."""
        return self.raw_storage['metadata']['name']

    @property
    def status(self):
        """Returns the storage status."""
        return self.raw_storage['data']['status']

    @property
    def is_ready(self):
        """Returns True if the Nnfnode is Ready."""
        return self.raw_storage['data']['status'] == "Ready"

    @property
    def capacity(self):
        """Returns the Storage capacity."""
        return self.raw_storage['data']['capacity']

    @property
    def computes(self):
        """Returns the Nnfnode servers list filtered for computes."""
        # Some test environments, such as craystack-lop, may not have computes
        # listed for every rabbit.
        return list(filter(lambda obj: obj['name'] != self.name, self.raw_storage['data']['access'].get('computes', [])))

    def has_sufficient_capacity(self, requestedCapacity):
        """Returns True if Nnfnode can meet the requested capacity."""
        return requestedCapacity < self.remaining_storage

    def allocs_remaining(self, alloc_size):
        """Computes the remaining allocations based on current capacity."""
        return math.floor(self.remaining_storage / alloc_size)

    def to_json(self):
        """Return a simplified json for this Nnfnode."""
        return {"name": self.name, "status": self.status, "capacity": self.capacity, "computes": self.computes}

    def dump_summary(self):
        """Dump object summary to console."""
        Console.output("-------------------------------------")
        Console.output("Storage: "+self.raw_storage['metadata']['name'])
        Console.output(f"    Status: {self.raw_storage['data']['status']}")
        Console.output(f"    is_ready: {self.is_ready}")
        Console.output(f"    Capacity: {self.raw_storage['data']['capacity']} ({type(self.raw_storage['data']['capacity'])}")
