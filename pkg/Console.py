# -*- coding: utf-8 -*-
# -----------------------------------------------------------------
# Console output class
# Use to control and format console output
#
# Author: Bill Johnson ( billj@hpe.com )
#
# © Copyright 2021 Hewlett Packard Enterprise Development LP
#
# -----------------------------------------------------------------

import datetime
import inspect
import json


class FunctionTrace:
    """Provides function level strack trace output. """
    def __init__(self, function_name):
        """Create instance with function to be traced (create at top of fcn).

        Parameters:
        function_name : Name of function

        Returns:
        Nothing
        """

        self.function_name = function_name
        msg = f"---------------------- ENTRY: {self.function_name} ----------------------"
        Console.debug(Console.MAX, msg)
        # Console.debug(Console.MAX, "".rjust(len(msg), '-'))

    def __del__(self):
        """Report function exit as instance variable gets destroyed.

        Parameters:
        None

        Returns:
        Nothing
        """

        msg = f"---------------------- EXIT: {self.function_name} ----------------------"
        Console.debug(Console.MAX, msg)
#        Console.debug(Console.MAX, "".rjust(len(msg), '-'))

    def __enter__(self):
        """Called at the start of a "with" block.

        Parameters:
        None

        Returns:
        Nothing
        """
        return self

    def __exit__(self, type, value, traceback):
        """Called at the exit of a "with" block.

        Parameters:
        None

        Returns:
        Nothing
        """
        pass


class Console:
    """Use to control output to the console."""
    verbosity = 0
    timestamp = True
    pretty = False
    MIN = 1
    WORDY = 2
    TRACE = 3
    MAX = 4
    QTR_BAR = "-"*20
    HALF_BAR = "-"*40
    FULL_BAR = "-"*60

    def caller_name(skip=2):
        """Get a name of a caller in the format module.class.method.

        Parameters:
        skip : `skip` specifies how many levels of stack to skip while getting caller
        name. skip=1 means "who calls me", skip=2 "who calls my caller" etc.

        Returns:
        Name of the calling subroutine if available, otherwise ""
        """

        stack = inspect.stack()
        start = 0 + skip
        if len(stack) < start + 1:
            return ''
        parentframe = stack[start][0]

        name = []
        module = inspect.getmodule(parentframe)
        # `modname` can be None when frame is executed directly in console
        # TODO(techtonik): consider using __main__
        if module:
            name.append(module.__name__)
        # detect classname
        if 'self' in parentframe.f_locals:
            # I don't know any way to detect call from the object method
            # XXX: there seems to be no way to detect static method call - it will
            #      be just a function call
            name.append(parentframe.f_locals['self'].__class__.__name__)
        codename = parentframe.f_code.co_name
        if codename != '<module>':  # top level usually
            name.append(codename)  # function or a method

        # Avoid circular refs and frame leaks
        #  https://docs.python.org/2.7/library/inspect.html#the-interpreter-stack
        del parentframe, stack

        return ".".join(name)

    def generate_timestamp():
        """Generates and returns a formatted timestamp if Console.timestamp
            is True, otherwise returns.

        Parameters:
        None

        Returns:
        Nothing
        """

        if not Console.timestamp:
            return ""

        now = datetime.datetime.now()
        return now.strftime("%Y-%m-%d %H:%M:%S ")

    def outputnotsp(msg, msg_prefix=""):
        """Send output to the console without a timestamp regardless of any
            settings.

        Parameters:
        msg : Message to output to the console
        msg_prefix : Prefix message with prefix

        Returns:
        Nothing
        """

        print(f"{msg_prefix}{msg}")

    def output(msg, msg_prefix="", output_timestamp=None):
        """Send output to the console.

        Parameters:
        msg : Message to output to the console
        msg_prefix : Prefix message with prefix
        output_timestamp : If False, disable any timestamp display

        Returns:
        Nothing
        """

        tsp_reqd = Console.timestamp
        if output_timestamp is not None:
            tsp_reqd = output_timestamp
        if tsp_reqd:
            tsp = Console.generate_timestamp()
        else:
            tsp = ""

        print(f"{tsp}{msg_prefix}{msg}")

    def pretty_json(dict, output_timestamp=False):
        """Send json to the console.  If Console.pretty is true, it is
            formatted, otherwise it is just dumped.

        Parameters:
        output_timestamp : If False, disable any timestamp display

        Returns:
        Nothing
        """
        if Console.pretty:
            Console.output(json.dumps(dict, indent=4, sort_keys=True), output_timestamp=False)
        else:
            Console.output(json.dumps(dict), output_timestamp=False)

    def level_enabled(level):
        """Test to see if verbosity level allows specified level.

        Parameters:
        level : Verbosity level to check

        Returns:
        True if level is allowed with current verbosity setting
        """
        return level <= Console.verbosity

    def error(msg, msg_prefix="", output_timestamp=True):
        """Send error output to the console.

        Parameters:
        msg : Message to output to the console
        msg_prefix : Prefix message with prefix
        output_timestamp : If False, disable any timestamp display

        Returns:
        Nothing
        """
        Console.output(msg, f"** ERROR ** {msg_prefix}", output_timestamp)

    def debug(level, msg, msg_prefix="", output_timestamp=True):
        """Send debug output to the console.

        Parameters:
        level : Verbosity level of this message.  If current verbosity is less
                than this level, this message will not be sent to console.
        msg : Message to output to the console
        msg_prefix : Prefix message with prefix
        output_timestamp : If False, disable any timestamp display

        Returns:
        Nothing
        """
        if level <= Console.verbosity:
            Console.output(
                msg, f"(DBG {level}) {msg_prefix}", output_timestamp)

    def trace_function():
        """Used to perform function tracing as part of console output.

        Parameters:
        None

        Returns:
        Newly created FunctionTrace class initialized with caller name

        Example usage:
            def my_function(someargs):
                with Console.trace_function():
                    ... method body ...

        """
        return FunctionTrace(Console.caller_name())
