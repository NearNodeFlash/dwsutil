# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# DWS Utility Configuration Class
# All the magic of DWS Utility configuration happens here!
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------

import os
import sys
import datetime
import random
import json
import yaml

from .Console import Console


class Config:
    """Holds the configuration information for the DWS Utility."""
    K8S_GROUP = "dws.cray.hpe.com"
    K8S_VERSION = "v1alpha1"
    DWSUTIL_VERSION = "0.2"

    def infinite_sequence():
        num = random.randint(0, 9)
        while True:
            yield num
            num += 1

    def __init__(self, argv):
        self.version_number = "0.2"
        self.version_string = f"DWS Utility - Version {Config.DWSUTIL_VERSION}"
        self.argv = argv
        self.munge = False
        self.force = False
        self.ignore_ready = False
        self.quiet = False
        self.preview = False
        self.show_version = False
        self.seq_gen = Config.infinite_sequence()

        self.var_startime = "$(starttime)"
        self.var_time = "$(time)"
        self.var_randint = "$(randint)"
        self.var_randintid = "$(randintid)"
        self.starttime = '{0:%Y%m%d%H%M%S}'.format(datetime.datetime.now())

        self.short_name = "dwsutil"
        self.long_name = "DWS Utility"
        self.verbosity = 0                   # -v
        self.config_file = ""       # -c
        self.config_file_source = None
        self.k8s_config = ""
        self.k8s_config_source = None
        self.k8s_default = ""
        self.k8s_active_context = ""
        self.k8s_active_context_source = None
        self.k8s_contexts = []
        self.wfr_name = ""
        self.wfr_name_source = "default"
        self.job_id = 5555
        self.job_id_source = "default"
        self.wlm_id = "5f239bd8-30db-450b-8c2c-a1a7c8631a1a"
        self.wlm_id_source = "default"
        self.user_id = 1001
        self.user_id_source = "default"
        self.showconfigonly = False
        self.context = "WFR"
        self.operation = ""
        self.dwdirectives = []
        self.dwdirectives_source = "default"
        self.exclude_rabbits = []
        self.exclude_computes = []
        self.dwshost = ""
        self.dwsport = ""
        self.inventory_file = None
        self.inventory_file_source = None
        self.nodes = 1
        self.nodelist = None
        self.pretty = True
        self.reuse_rabbit = False
        self.ost_count = 2
        self.ost_per_rabbit = 1
        self.alloc_recipe = {}
        self.alloc_raw = []

        self.operation_count = 1
        self.singlethread = False
        self.regexEnabled = False

        self.process_commandline(init_flags_only=True)
        Console.verbosity = self.verbosity

        self.load_config()
        self.process_commandline(init_flags_only=False)

        self.evaluate_configuration()

    def replace_vars(self, str):
        str = str.replace(self.var_startime, self.starttime)
        str = str.replace(self.var_time, ('{0:%Y%m%d%H%M%S}'.format(datetime.datetime.now()))+f"{next(self.seq_gen)}")
        val = random.randint(10000, sys.maxsize)
        str = str.replace(self.var_randint, f"{val}")
        val = 1000 + random.randint(1, 8999) % 10000
        str = str.replace(self.var_randintid, f"{val}")
        return str

    def output_usage_item(self, item, desc):
        """Output a formatted CLI parameter with it's description.

        Parameters:
        item : The command line flag / arg
        desc : Description of the flag / arg

        Returns:
        Nothing
        """

        width = 30
        spacer = " " * width
        itemplus = item+spacer
        Console.outputnotsp(f"    {itemplus[:30]}: {desc}")

    def output_usage_item_detail(self, indent, desc):
        """Output additional usage item information with additional indent.

        Parameters:
        indent : The number of 'indents' to expand
        desc : Additional descriptive information

        Returns:
        Nothing
        """

        width = 30 + (2 * indent)
        spacer = " " * width
        Console.outputnotsp(f"    {spacer} {desc}")

    def usage(self, msg, die=True, retval=-1):
        """Output usage information for DWS Utility.

        Parameters:
        msg : Any message to precede the usage
        die : If True, application will die after usage display
        retval : Value to be returned to OS when die is True

        Returns:
        Nothing
        """

        Console.outputnotsp(f"{msg}")
        Console.outputnotsp("usage: dwsutil.py <options>")
        self.output_usage_item("-?", "Display this usage")
        self.output_usage_item("--alloc specification", "Specify the allocation format for Lustre")
        self.output_usage_item_detail(1, "specification format: fs-name;mgt=somerabbit;mdt=somerabbit;ost=somerabbit")
        self.output_usage_item_detail(1, "   where fs-name is the name in a given #dw")
        self.output_usage_item_detail(1, "   Note: You must specify all components, mgt, mdt, and ost")
        self.output_usage_item("-c/--config <configfile>", "Specify simulator configuration file")
        self.output_usage_item("--dw '#DW ....'", "Add a DataWarp directive, may occur multiple times")
        self.output_usage_item("--exr rabbit1,rabbit2,...rabbitN", "Exclude the listed rabbits when assigning resources")
        self.output_usage_item("--exc compute1,compute2,...computeN", "Exclude the listed computes when assigning resources")
#        self.output_usage_item("--force", "Force an operation that would ordinarily be prevented")
        self.output_usage_item("-i/--inventory <inventoryfile>", "Override cluster inventory for the simulator using the file provided")
        self.output_usage_item("--ignoreready", "Ignore ready status of computes and rabbits")
        self.output_usage_item("-j/--jobid <job_id>", "Specify the job id to be used in the Workflow Resource")
        self.output_usage_item("-k/--kcfg <configfile>", "Specify kubernetes configuration file")
        self.output_usage_item("--kctx <context>", "Kubernetes context to use")
        self.output_usage_item("--munge", "Automatically add process id to the workflow resource name, default is not to munge")
        self.output_usage_item("--mungecompute", "Munge compute names if they are named 'Compute x', default is not to munge")
        self.output_usage_item("-n/--name <wfr_name>", "Specify the name of the Workflow Resource")
        self.output_usage_item("--node <number>", "Specify the number of compute nodes, default=1")
#        self.output_usage_item("--nodelist compute1,compute2,compute3,...computeN", "Specify the list of compute nodes to be used")
        self.output_usage_item("--notimestamp", "Remove timestamping from the output")
        self.output_usage_item("--opcount <number>", "Perform the requested operation <number> times, default=1")
        self.output_usage_item("--ostcount <number>", "Number of OST HOSTS for Lustre, default=2")
        self.output_usage_item("--ostperrabbit <number>", "Number of OSTs per Rabbit for Lustre, default=1")
        self.output_usage_item("--pretty", "Format JSON output")
        self.output_usage_item("-q", "Suppress non-operational output")
        self.output_usage_item("--regex", "Enable regex pattern matching for operations that allow regexes")
        self.output_usage_item("--noreuse", "Do not use the same rabbit for lustre components if possible")
        self.output_usage_item("--showconfig", "Show configuration and quit without doing anything")
#        self.output_usage_item("--singlethread", "Do not multithread bulk operations")
        self.output_usage_item("-u/--userid <user_id>", "Specify the user id to be used in the Workflow Resource")
        self.output_usage_item("-v", "Incrementally increase verbosity with each flag provided")
        self.output_usage_item("--version", "Show version and exit")
        self.output_usage_item("-w/--wlmid <wlm_id>", "Specify the WLM id to be used in the Workflow Resource")
        Console.outputnotsp("")
        self.output_usage_item("--context <context>", "Provide the 'context' for the operation.  Default is 'WFR'")
        self.output_usage_item("--operation <operation>", "Provide the 'operation' to be performed.  Valid operations are:")
        self.output_usage_item_detail(1, "Note: 'context' and 'operation' ARE NOT CASE SENSITIVE")
        self.output_usage_item_detail(1, "When context = WFR")
        self.output_usage_item_detail(3, "ASSIGNCOMPUTES - Choose computes based on the directivebreakdown")
        self.output_usage_item_detail(3, "ASSIGNSERVERS - Choose rabbits based on the directivebreakdown")
        self.output_usage_item_detail(3, "CREATE - Create the specified WFR")
        self.output_usage_item_detail(3, "DELETE - Delete the WFR matching the specified name (regex allowed)")
        self.output_usage_item_detail(3, "GET - Get the named workflow resource")
        self.output_usage_item_detail(3, "INVESTIGATE - Analyze the named WFR and associated objects")
        self.output_usage_item_detail(3, "LIST - List all workflows the system knows about")
        self.output_usage_item_detail(3, "PROGRESS - Progress to the next normal desired state in the lifecycle (regex allowed)")
        self.output_usage_item_detail(3, "PROGRESSTEARDOWN - Progress directly to 'teardown' desired state regardless of current state (regex allowed)")
        self.output_usage_item_detail(1, "When context = INVENTORY")
        self.output_usage_item_detail(3, "SHOW - Displays the nnf nodes and inventory from the cluster or inventory file")
        self.output_usage_item_detail(1, "When context = STORAGE")
        self.output_usage_item_detail(3, "LIST - List all Storage CRs the system knows about")
        self.output_usage_item_detail(1, "When context = SYSTEM")
        self.output_usage_item_detail(3, "INVESTIGATE - Analyze the current system configuration including nodes, pods, and CRDs")

        Console.outputnotsp("\nReturn values:")
        Console.outputnotsp("   0  Operation succeeded")
        Console.outputnotsp("   ! 0  Operation failed")

        Console.outputnotsp("")
        Console.outputnotsp("Examples:")
        Console.outputnotsp("  Show configuration information")
        Console.outputnotsp("     dwsutil.py --showconfig")
        Console.outputnotsp("     dwsutil.py -c dwsutil-mymachine.cfg --showconfig")
        Console.outputnotsp("-" * 60)
        Console.outputnotsp("  Show cluster inventory")
        Console.outputnotsp("     dwsutil.py --context INVENTORY --operation SHOW")
        Console.outputnotsp("-" * 60)
        Console.outputnotsp("  Create a WFR named 'my-wfr-01'")
        Console.outputnotsp("     dwsutil.py -n my-wfr-01 --operation CREATE")
        Console.outputnotsp("-" * 60)
        Console.outputnotsp("  Assign servers(rabbits) to a WFR named 'my-wfr-01'")
        Console.outputnotsp("     dwsutil.py -n my-wfr-01 --operation ASSIGNSERVERS")
        Console.outputnotsp("-" * 60)
        Console.outputnotsp("  Progress a WFR named 'my-wfr-01'")
        Console.outputnotsp("     dwsutil.py -n my-wfr-01 --operation PROGRESS")
        Console.outputnotsp("-" * 60)
        Console.outputnotsp("  Delete a WFR named 'my-wfr-01'")
        Console.outputnotsp("     dwsutil.py -n my-wfr-01 --operation DELETE")
        if die:
            exit(retval)

    def evaluate_configuration(self):
        """Validates current configuration.  If configuration is
           invalid, error message and usage information are displayed and
           application terminates.

        Parameters:
        None

        Returns:
        Nothing
        """

        if self.k8s_config != "":
            if not os.path.exists(self.k8s_config):
                self.usage(f"Kubernetes configuration file '{self.k8s_config}' does not exist")

        if self.context == "WFR" and self.operation in ["CREATE", "GET", "ASSIGNCOMPUTES", "ASSIGNSERVERS", "DELETE", "PROGRESS", "PROGRESSTEARDOWN", "INVESTIGATE"]:
            if self.wfr_name is None or self.wfr_name.strip() == '':
                self.usage(f"Workflow name is required for operation {self.operation}")

        if self.munge and self.wfr_name != "":
            self.wfr_name = f"{self.wfr_name}-{os.getpid()}"

        self.wfr_name = self.replace_vars(self.wfr_name)

        if self.inventory_file is not None:
            if not os.path.exists(self.inventory_file):
                self.usage(f"Inventory '{self.inventory_file}' does not exist")

        if len(self.alloc_raw) > 0 and len(self.exclude_rabbits) > 0:
            self.usage("--alloc flag/config cannot be used with --exr flag/config")

        # Strip spaces off of exclude list elements
        self.exclude_rabbits = [r.strip().lower() for r in self.exclude_rabbits]
        self.exclude_computes = [c.strip().lower() for c in self.exclude_computes]

    def output_config_item(self, item, value, source=None):
        """Used to output formatted configuration information to the console.

        Parameters:
        item : The configuration item
        value : Value of the configuration item
        source : Where the 'value' came from (only used in limited cases)

        Returns:
        Nothing
        """

        itemplus = item + "." * 30
        if source:
            valueplus = value + " " * 30
            Console.output(f"{itemplus[:20]}: {valueplus[:30]} ( {source} )")
        else:
            Console.output(f"{itemplus[:20]}: {value}")

    def output_configuration(self, init_flags_only=False):
        """Output the current DWS Utility configuration to the console.

        Parameters:
        init_flags_only : Only display config initialization items if True

        Returns:
        Nothing
        """

        self.output_config_item("config file", self.config_file, self.config_file_source)
        if self.k8s_config != "":
            self.output_config_item("k8s config file", self.k8s_config, self.k8s_config_source)
        if self.k8s_active_context != "":
            self.output_config_item("K8S default", self.k8s_default)
            self.output_config_item("Available contexts", self.k8s_contexts)
            self.output_config_item("Using K8S context", self.k8s_active_context, self.k8s_active_context_source)

        if init_flags_only:
            return
        self.output_config_item("Preview", self.preview)
        self.output_config_item("Context", self.context)
        self.output_config_item("Operation", self.operation)
        self.output_config_item("...Count", self.operation_count)
        self.output_config_item("WFR name", self.wfr_name)
        self.output_config_item("WLM id", self.wlm_id)
        self.output_config_item("Job id", self.job_id)
        self.output_config_item("User id", self.user_id)
        self.output_config_item("# of nodes", self.nodes)
        self.output_config_item("Exclude computes", self.exclude_computes)
        self.output_config_item("Exclude rabbits", self.exclude_rabbits)
        self.output_config_item("Inventory file", self.inventory_file)
#        self.output_config_item("nodes", self.nodelist)
        if len(self.dwdirectives) == 0:
            self.output_config_item("dw directives", "None")
        else:
            for dw in self.dwdirectives:
                self.output_config_item("dw directive", dw)

        if len(self.alloc_raw) == 0:
            self.output_config_item("alloc", "None")
        else:
            for alloc in self.alloc_raw:
                self.output_config_item("alloc", alloc)

#        self.output_config_item("SingleThreaded", self.singlethread)
        self.output_config_item("ShowConfig", self.showconfigonly)
        self.output_config_item("Munge WFR names", self.munge)
        self.output_config_item("Allow regexes", self.regexEnabled)

    def get_arg(self, index):
        """Get the CLI argument by index.

        Parameters:
        index : Index of arg value to be returned

        Returns:
        Tuple: argvalue, next index value

        When out of arguments:
        Tuple: None, 0

        """

        if index >= len(self.argv):
            return None, 0
        return self.argv[index], index+1

    def process_alloc(self, alloc_str):
        """Process the the argument to the --alloc flag

        Parameters:
        alloc_str : The argument following --alloc

        Returns:
        Nothing
        """
        if alloc_str is None:
            self.usage("An alloc recipe must be specified with --allow   e.g. -alloc \"fs-name;mgt=somerabbit;mdt=somerabbit;ost=somerabbit\"")

        self.alloc_raw.append(alloc_str)
        alloc = alloc_str.split(";")
        # print(f"Alloc name: {alloc[0]}")
        # print(f"Alloc split: {alloc[1:]}")
        alloc_obj = {"name": alloc[0], "allocs": {}}
        for obj in alloc[1:]:
            # print(f"...processing {obj}")
            obj_parts = obj.split("=")
            alloc_part = {"label": obj_parts[0], "servers": []}
            for server_obj in obj_parts[1].split(","):
                server_obj_parts = server_obj.split(":")
                allocations = 1
                if len(server_obj_parts) > 1:
                    allocations = int(server_obj_parts[1])
                else:
                    allocations = 1
                server = {"name": server_obj_parts[0], "allocations": allocations}

                alloc_part["servers"].append(server)
            alloc_obj['allocs'][obj_parts[0]] = alloc_part

        self.alloc_recipe[alloc[0]] = alloc_obj
        # Console.pretty_json(self.alloc_recipe)

    def process_commandline(self, init_flags_only=True):
        """Process the command line.

        Parameters:
        init_flags_only : When True, shallow processing to pick up initial
                          configuration items that may be later overriden
                          by command line flags

        Returns:
        Nothing
        """

        arg = ""
        aidx = 1
        while arg is not None:
            arg, aidx = self.get_arg(aidx)
            if not arg:
                continue

            # Begin by looking for initialization flags...things like the config file and output verbosity
            if arg == "-?":
                self.usage("", retval=0)

            if arg in ["-c", "--config"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A configuration file must be specified with the -c or --config argument   e.g. -c my.cfg")
                if init_flags_only:
                    self.config_file = arg
                    self.config_file_source = "CLI"
                continue

            if arg in ["-q"]:
                self.quiet = True
                continue

            if arg == "-v":
                if init_flags_only:
                    self.verbosity += 1
                continue

            if arg == "--version":
                if init_flags_only:
                    self.show_version = True
                continue

            # This continue ignores anything except the args above
            if init_flags_only:
                continue

            if arg in ["--alloc"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("An alloc recipe must be specified with --allow   e.g. -alloc \"fs-name;mgt=somerabbit;mdt=somerabbit;ost=somerabbit\"")

                self.process_alloc(arg)
                continue

            if arg in ["--context"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A context must be specified with --context.  Valid values are WFR.   e.g. --context WFR")
                self.context = arg.upper()
                continue

            if arg in ["--dw"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A datawarp directive must be specified with -n   e.g. -dw \"#DW ...some directive\"")
                self.dwdirectives.append(self.replace_vars(arg))
                continue

            if arg in ["--exc"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A comma delimited list of compute nodes to exclude must be specified with --exc   e.g. --exc c1,c2")
                self.exclude_computes += arg.split(",")
                continue

            if arg in ["--exr"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A comma delimited list of rabbit nodes to exclude must be specified with --exr   e.g. --exrc r1,r2")
                self.exclude_rabbits += arg.split(",")
                continue

            if arg in ["--force"]:
                self.force = True
                continue

            if arg in ["-i", "--inventory"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("An inventory file must be specified with the -i or --inventory argument   e.g. -y my-inv.yaml")
                self.inventory_file = arg
                self.inventory_file_source = "CLI"
                continue

            if arg in ["--ignoreready"]:
                self.ignore_ready = True
                continue

            if arg in ["-j", "--jobid"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A Job id name must be specified with -n   e.g. -j 5432")

                print(arg)
                self.job_id = int(self.replace_vars(arg))
                continue

            if arg in ["-k", "--kcfg"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A kubernetes configuration file must be specified with the -k or --kcfg argument   e.g. -k myk8s.cfg")
                self.k8s_config = arg
                self.k8s_config_source = "CLI"

                continue

            if arg in ["--kctx"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A kubernetes context must be specified with the -kctx   e.g. -kctx dp1b")
                self.k8s_active_context = arg
                self.k8s_active_context_source = "CLI"
                continue

            if arg in ["--munge"]:
                self.munge = True
                continue

            if arg in ["-n", "--name"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A Workflow Resource name must be specified with -n   e.g. -n my-workflow-01")
                self.wfr_name = arg
                continue

            if arg in ["--nodes"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A <number> of compute nodes must be specified with --nodes   e.g. --nodes 3")
                self.nodes = int(arg)
                continue

            if arg in ["--noreuse"]:
                self.reuse_rabbit = False
                continue

            if arg in ["--notimestamp"]:
                Console.timestamp = False
                continue

            if arg in ["--opcount"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A <number> of operations must be specified with --opcount   e.g. --opcount 5")
                self.operation_count = int(arg)
                continue

            if arg in ["--operation"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("An operation must be specified with --operation.   e.g. --operation CREATE")
                self.operation = arg.upper()
                continue

            if arg in ["--ostcount"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A <number> of OSTs must be specified with --ostcount   e.g. --ostcount 5")
                self.ost_count = int(arg)
                continue

            if arg in ["--ostperrabbit"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A <number> of OSTs per Rabbit must be specified with --ostperrabbit   e.g. --ostperrabbit 2")
                self.ost_per_rabbit = int(arg)
                continue

            if arg in ["--pretty"]:
                self.pretty = True
                Console.pretty = True
                continue

            if arg in ["--preview"]:
                self.preview = True
                continue

            if arg in ["--regex"]:
                self.regexEnabled = True
                continue

            if arg in ["--showconfig"]:
                self.showconfigonly = True
                continue

            if arg in ["-u", "--userid"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A User id name must be specified with -n   e.g. -u 1001")
                self.user_id = int(self.replace_vars(arg))
                continue

            if arg in ["-w", "--wlmid"]:
                arg, aidx = self.get_arg(aidx)
                if arg is None:
                    self.usage("A WLM id name must be specified with -n   e.g. --wlmid flux01")
                self.wlm_id = arg
                continue

            self.usage(f"Unknown flag: {arg}")

        #   # Process the remaining flags
        #   print(f"[{aidx}] [{arg}]")

        # print(f"Config: {self.config_file}")
        # print(f"Verbosity: {self.verbosity}")

    def get_config_entry(self, cfg, key, val, default=""):
        """Return an entry from the configuration dictionary.

        Parameters:
        cfg : The dictionary containing the configuration
        key : The key of the section that you are looking for
        val : The value key that you want the value for
        default : The default value to be returned if key/val doesn't exist

        Returns:
        Value if it exists otherwise default
        """

        if key in cfg:
            if val in cfg[key]:
                return cfg[key][val]
        return default

    def resolve_k8s_config(self):
        """Find a k8s config file if one has not been specified.  This will
           set the internal k8s_config value if a config file is located or
           will die with a usage msg pertaining to the k8s config.

        Returns:
        Nothing
        """

        # First look in the environment
        Console.debug(Console.MIN, "Looking for $KUBECONFIG setting")
        if "KUBECONFIG" in os.environ:
            self.k8s_config = os.environ['KUBECONFIG']
            if self.k8s_config is not None and self.k8s_config != "":
                Console.debug(Console.MIN, f"Looking for {self.k8s_config}")
                self.k8s_config = os.path.expandvars(self.k8s_config)
                if os.path.exists(self.k8s_config):
                    Console.debug(Console.MIN, f"Using {self.k8s_config}")
                    self.k8s_config_source = "$KUBECONFIG env"
                    return

        # Second look in the home directory
        self.k8s_config = os.path.expandvars("$HOME/.kube/config")
        Console.debug(Console.MIN, f"Looking for {self.k8s_config}")
        if os.path.exists(self.k8s_config):
            Console.debug(Console.MIN, f"Using {self.k8s_config}")
            self.k8s_config_source = "Home directory"
            return

        Console.debug(Console.MIN, "Unable to locate kube config file")
        self.usage("Kubernetes config file must be specified via"
                   " $KUBECONFIG, in $HOME/.kube/config, or in"
                   " a valid dwsutil configuration file")

    def load_config(self):
        """Load and process a DWS Utility configuration file.  This method
           will attempt to find the default dwsutil.cfg if a config has not
           been specified.  Additionally, this method will attempt to resolve
           a k8s config file if one has not been specified.

        Parameters:
        None

        Returns:
        Nothing
        """

        if self.config_file == "" or self.config_file is None:
            Console.debug(Console.MIN, "No dwutil config specified,"
                                       " looking for $DWSUTIL_CONFIG setting")
            if "DWSUTIL_CONFIG" in os.environ:
                self.config_file = os.environ['DWSUTIL_CONFIG']
                self.config_file_source = "$DWSUTIL_CONFIG"
            else:
                Console.debug(Console.MIN, "$DWSUTIL_CONFIG not set,"
                                           " looking for dwsutil.cfg")
                if os.path.exists("dwsutil.cfg"):
                    Console.debug(Console.MIN, "dwsutil.cfg found and used")
                    self.config_file = "dwsutil.cfg"
                    self.config_file_source = "Existing dwsutil.cfg"

        # The dwsutil config file isn't necessary if we can find a kube config
        if self.config_file == "" or self.config_file is None:
            Console.debug(Console.MIN, "No config file specified and no default config file present")
        elif not os.path.exists(self.config_file):
            self.usage(f"{self.long_name} configuration file '{self.config_file}' does not exist")
        else:
            with open(self.config_file) as file:
                cfg = yaml.safe_load(file)
                self.k8s_config = self.get_config_entry(cfg, "k8s", "config", "")
                if self.k8s_config is not None and self.k8s_config != "":
                    self.k8s_config = os.path.expandvars(self.k8s_config)
                    Console.debug(Console.MIN, "Using kube config from config")
                    self.k8s_config_source = "Config file"
                else:
                    Console.debug(Console.MIN, "No kubernetes config specified in config file")

                # *******************************
                # * Kubernetes section
                # *******************************
                kctx = self.get_config_entry(cfg, "k8s", "context", None)
                if kctx is not None:
                    self.k8s_active_context = kctx
                    self.k8s_active_context_source = "Config file"

                # *******************************
                # * Config section
                # *******************************
                alloc_specs = self.get_config_entry(cfg, "config", "allocations", None)
                if alloc_specs is not None:
                    for alloc in alloc_specs:
                        self.process_alloc(alloc['alloc'])

                directives = self.get_config_entry(cfg, "config", "directives", None)
                if directives is not None:
                    for directive in directives:
                        self.dwdirectives.append(self.replace_vars(directive["dw"]))

                excludes = self.get_config_entry(cfg, "config", "exclude_computes", None)
                if excludes is not None:
                    for exclude in excludes:
                        self.exclude_computes.append(exclude["name"])

                excludes = self.get_config_entry(cfg, "config", "exclude_rabbits", None)
                if excludes is not None:
                    for exclude in excludes:
                        self.exclude_rabbits.append(exclude["name"])

                ignore_ready = self.get_config_entry(cfg, "config", "ignoreready", None)
                if ignore_ready is not None:
                    self.ignore_ready = ignore_ready

                self.inventory_file = self.get_config_entry(cfg, "config", "inventory", None)
                if self.inventory_file is not None:
                    self.inventory_file = os.path.expandvars(self.inventory_file)

                jobid = self.get_config_entry(cfg, "config", "jobid", None)
                if jobid is not None:
                    if (isinstance(jobid, str)):
                        jobid = int(self.replace_vars(jobid))
                    self.job_id = jobid

                munge = self.get_config_entry(cfg, "config", "munge", None)
                if munge is not None:
                    self.munge = munge

                nodes = self.get_config_entry(cfg, "config", "nodes", None)
                if nodes is not None:
                    self.nodes = nodes

                ostcount = self.get_config_entry(cfg, "config", "ostcount", None)
                if ostcount is not None:
                    self.ost_count = ostcount

                ostper = self.get_config_entry(cfg, "config", "ostperrabbit", None)
                if ostcount is not None:
                    self.ost_per_rabbit = ostper

                preview = self.get_config_entry(cfg, "config", "preview", None)
                if preview is not None:
                    self.preview = preview

                pretty = self.get_config_entry(cfg, "config", "pretty", None)
                if pretty is not None:
                    self.pretty = pretty
                    Console.pretty = pretty

                quiet = self.get_config_entry(cfg, "config", "quiet", None)
                if quiet is not None:
                    self.quiet = quiet

                regex = self.get_config_entry(cfg, "config", "regex", None)
                if regex is not None:
                    self.regexEnabled = regex

                reuse = self.get_config_entry(cfg, "config", "reuse_rabbit", None)
                if reuse is not None:
                    self.reuse_rabbit = reuse

                userid = self.get_config_entry(cfg, "config", "userid", None)
                if userid is not None:
                    if (isinstance(userid, str)):
                        userid = int(self.replace_vars(userid))
                    self.user_id = userid

                wfrname = self.get_config_entry(cfg, "config", "wfrname", None)
                if wfrname is not None:
                    self.wfr_name = wfrname

                wlmid = self.get_config_entry(cfg, "config", "wlmid", None)
                if wlmid is not None:
                    self.wlm_id = wlmid

    def to_json(self):
        return json.dumps({x: self.__dict__[x] for x in self.__dict__ if x not in ['seq_gen']})
