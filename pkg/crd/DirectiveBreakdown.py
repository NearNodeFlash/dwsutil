# -----------------------------------------------------------------
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
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
