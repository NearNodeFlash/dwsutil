# -----------------------------------------------------------------
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
from ..Console import Console


class Storage:
    """Encapsulates the Storage CR."""
    def __init__(self, raw_storage):
        with Console.trace_function():
            if not raw_storage:
                raise "raw_storage is required"
            self._raw_storage = raw_storage

    @property
    def raw_storage(self):
        """Returns the internal json for the Storage."""
        return self._raw_storage

    @raw_storage.setter
    def raw_storage(self, raw_storage):
        """Setter for the internal Storage json."""
        self._raw_storage = raw_storage

    @property
    def name(self):
        """Returns the Storage name."""
        return self.raw_storage['metadata']['name']

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
        """Returns the Storage computes list."""
        return self.raw_storage['data']['access']['computes']

    def has_sufficient_capacity(self, requestedCapacity):
        """Returns True if Nnfnode can meet the requested capacity."""
        return True

    def dump_summary(self):
        """Dump object summary to console."""
        Console.output("-------------------------------------")
        print("Storage: "+self.raw_storage['metadata']['name'])
        print(f"    Status: {self.raw_storage['data']['status']}")
        print(f"    is_ready: {self.is_ready}")
        print(f"    Capacity: {self.raw_storage['data']['capacity']} ({type(self.raw_storage['data']['capacity'])}")
