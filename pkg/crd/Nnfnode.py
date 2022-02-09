# -----------------------------------------------------------------
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------
import re
import copy

from ..Console import Console


class Nnfnode:
    """Encapsulates the Nnfnode CR."""
    def __init__(self, raw_nnfnode, allow_compute_name_munge=True):
        """init initializes the object json from k8s.

        Parameters:
        raw_nnfnode : CR JSON from k8s
        allow_compute_name_munge : Fixup bad Compute names if True (Compute X)
        """
        with Console.trace_function():
            if not raw_nnfnode:
                raise(Exception("raw_nnfnode cannot be None"))
            if not all(key in raw_nnfnode for key in ('metadata', 'status')):
                raise(Exception(
                    "raw_nnfnode is missing required 'metadata'/'status' fields for nnf-node"))
            if 'namespace' not in raw_nnfnode['metadata']:
                raise(
                    Exception("raw_nnfnode is missing required 'namespace' field for nnf-node"))
            if 'name' not in raw_nnfnode['spec']:
                raise(
                    Exception("raw_nnfnode is missing required 'name' field for nnf-node"))
            if not all(key in raw_nnfnode['status'] for key in ('capacity', 'status', 'servers')):
                raise(Exception(
                    "raw_nnfnode is missing required ''status' sub-fields for nnf-node"))
            self._raw_nnfnode = copy.deepcopy(raw_nnfnode)

            # If we still have garbage compute node names, this will
            # clean them up and make them unique by prefixing them with
            # the nnf node name
            if allow_compute_name_munge:
                regex = "^Compute [0-9]"
                for idx in range(len(self._raw_nnfnode['status']['servers'])):
                    server_name = self._raw_nnfnode['status']['servers'][idx]["name"]
                    if re.match(regex, server_name):
                        server_name = self.name+"-"+server_name.replace(" ", "-")
                        self._raw_nnfnode['status']['servers'][idx]["name"] = server_name

    @property
    def raw_nnfnode(self):
        """Returns the internal json for the Nnfnode."""
        return self._raw_nnfnode

    @raw_nnfnode.setter
    def raw_nnfnode(self, raw_nnfnode):
        """Setter for the internal Nnfnode json."""
        self._raw_nnfnode = copy.deepcopy(raw_nnfnode)

    @property
    def namespace(self):
        """Returns the Nnfnode namespace."""
        return self._raw_nnfnode['metadata']['namespace']

    @property
    def name(self):
        """Returns the Nnfnode name."""
        return self._raw_nnfnode['spec']['name']

    @property
    def status(self):
        """Returns the Nnfnode status."""
        return self._raw_nnfnode['status']['status']

    @property
    def is_ready(self):
        """Returns True if the Nnfnode is Ready."""
        return self._raw_nnfnode['status']['status'] == "Ready"

    @property
    def capacity(self):
        """Returns the Nnfnode capacity."""
        return self._raw_nnfnode['status']['capacity']

    @property
    def computes(self):
        """Returns the Nnfnode servers list filtered for computes."""
        return list(filter(lambda obj: obj['name'] != self.name and obj['name'].lower() != "rabbit", self._raw_nnfnode['status']['servers']))

    @property
    def servers(self):
        """Returns the Nnfnode server list without filtering."""
        return self._raw_nnfnode['status']['servers']

    def to_json(self):
        """Return a simplified json for this Nnfnode."""
        return {"name": self.name, "status": self.status, "capacity": self.capacity, "computes": self.servers}

    def dump_summary(self):
        """Dump object summary to console"""
        Console.output("-------------------------------------")
        Console.output("Storage: "+self._raw_nnfnode['metadata']['name'])
        Console.output(f"    Status: {self._raw_nnfnode['status']['status']}")
        Console.output(f"    is_ready: {self.is_ready}")
        Console.output(f"    Capacity: {self._raw_nnfnode['status']['capacity']}")
