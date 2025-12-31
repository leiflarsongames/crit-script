"""CritScript to Python conversions:

"""

## TODO planned redesign: make these functions NOT flood the call stack...
# so we'll have to...
#  * have a while loop which starts with an execution pin, and invokes the attached function
#  * have the next execution pin to be called be returned by invoke() instead of returning nothing
#  * set the current execution pin to the newly returned one from invoke()
#  * then loop again until the execution pin has no friend.

from enum import Enum
from typing import Callable

class NodeType(Enum):
    JustInTime = 0
    """This node will only be executed "just-in-time", and will not include any execution pins."""
    Standard = 1
    """This node will automatically include an exec-in and exec-out pin."""
    Macro = 2
    """This node automatically includes an exec-in pin, user must add any output execution pins manually.
    The list returned by this node's function MUST end with an integer indicating which execution pin to use!

    * Note: ``Macro`` is the only node type that allows manual addition of execution pins."""
    # External = -1   ## TODO implement!
    # """This node is an event which is callable from Python code. It may NOT have any inputs, and will include an
    # exec-out output."""


class CritScriptException(Exception):
    def __init__(self, message):
        super().__init__(message)

class InvalidCritScriptFunctionException(CritScriptException):
    def __init__(self, function):
        super().__init__(f"{function.__name__} must return a list of outputs, but does not.")


class CritScriptPin:
    def __init__(self, name:str="unnamed", node:'CritScriptNode|None'=None, out:bool=False):
        self.name:str = name
        self.node:CritScriptNode|None = node
        self.conducted_type:type|None = None
        self.out:bool = out     # Needs to be set by the CritScriptNode constructor!
        self.friend:CritScriptPin|None = None  # The other pin this one is connected to.

    def clone_to_new_node(self, node:'CritScriptNode|None'=None):
        return_value = CritScriptPin(name=self.name, node=self.node)
        return_value.node = node
        return_value.conducted_type = self.conducted_type
        return_value.out = self.out
        return_value.friend = None
        return return_value



    def can_connect(self, other:'CritScriptPin') -> bool:
        """Returns whether two pins can be connected.

        In order for two pins to connect:
 * Their ``out`` values must not match (in vs out pin)
 * Neither may already be connected
 * They must conduct the same types"""
        if self.out and not other.out:
            return ( self.friend is None and
                    other.friend is None and
                     self.conducted_type is other.conducted_type)
        elif not self.out and other.out:
            return other.can_connect(self)
        else:
            return False
    def try_connect(self, other:'CritScriptPin') -> bool:
        succeeds = self.can_connect(other)
        if succeeds:
            self.friend = other
            other.friend = self
        return succeeds

    def can_disconnect(self) -> bool:
        return self.friend is not None

    def try_disconnect(self) -> bool:
        succeeds = self.can_disconnect()
        if succeeds:
            self.friend.friend = None
            self.friend = None
        return succeeds

    def has_friend(self) -> bool:
        return self.friend is not None


class CritScriptValuePin(CritScriptPin):
    def __init__(self, conducted_type:type|None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conducted_type:type|None = conducted_type

    def read_value(self):
        raise NotImplemented()  # MUST be implemented on each subclass!

    def write_value(self, value):
        raise NotImplemented()  # MUST be implemented on each subclass!

class BundlePin(CritScriptValuePin):
    pass  ## TODO implement!

class ExecutionPin(CritScriptPin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute(self):
        """TODO document better!"""
        if not self.out:    # Only invokes on an in pin.
            self.node.invoke()
        ## TODO should we raise an error on an out pin?

    def get_next(self):
        if self.out:
            return self.friend
        ## TODO should we raise an error on an in pin?

class StringPin(CritScriptValuePin):
    def __init__(self, last_value:str|None=None, *args, **kwargs,):
        super().__init__(conducted_type=str, *args, **kwargs)
        self.last_value:float|None = last_value

    def read_value(self):
        if self.node.is_just_in_time_node():
            raise NotImplementedError()     ## TODO implement just-in-time logic!
        else:
            return self.last_value

    def write_value(self, value):
        self.last_value = value

class NumberPin(CritScriptValuePin):
    def __init__(self, last_value:float|None=None, *args, **kwargs):
        super().__init__(conducted_type=float, *args, **kwargs)
        self.last_value:float|None = last_value

    def read_value(self):
        if self.node.is_just_in_time_node():
            raise NotImplementedError()     ## TODO implement just-in-time logic!
        else:
            return self.last_value

    def write_value(self, value):
        self.last_value = value

class Position:
    def __init__(self, x:float=0.0, y:float=0.0):
        self.x:float = x
        self.y:float = y

class CritScriptNode:
    def __init__(self, function_name):
        # (function, inputs, outputs, node_type, exec_out_pins)
        entry = CRIT_SCRIPT_FUNCTIONS[function_name]
        print(f"entry = {entry}")
        self.function:Callable = entry[0]

        # default values
        self.in_pins = tuple()
        self.out_pins = tuple()
        self.node_type = tuple()
        self.exec_in_pin = None
        self.exec_out_pins = tuple()

        # load real values
        if entry[1] is not None:
            self.in_pins = tuple([p.clone_to_new_node(self) for p in entry[1]])
        if entry[2] is not None:
            self.out_pins = tuple([p.clone_to_new_node(self) for p in entry[2]])
            for out_pin in self.out_pins:
                out_pin.out = True
        if entry[3] is not None:
            self.node_type = entry[3]

        # load real values for execution pins
        match self.node_type:
            case NodeType.JustInTime:
                pass    # no modifications needed on "just-in-time" nodes.
            case NodeType.Standard:
                self.exec_in_pin = ExecutionPin(name="exec-in", node=self)
                self.exec_out_pins = tuple((ExecutionPin(name="exec-out", node=self),))
                self.exec_out_pins[0].out = True
            case NodeType.Macro:
                self.exec_in_pin = ExecutionPin(name="exec-in", node=self)
                self.exec_out_pins = tuple([p.clone_to_new_node(self) for p in entry[4]]) if entry[4] is not None else tuple((ExecutionPin(name="exec-out", node=self),))
                for pin in self.exec_out_pins:
                    pin.out = True
            case _:
                raise NotImplementedError(f"CritScriptNode.__init__() is not implemented for case node_type={self.node_type}!")     # TODO write something for this!

    def is_just_in_time_node(self) -> bool:
        """Whether this Node is invoked as a "just in time" node, or if it needs to be invoked explicitly via its
        execution pin input before it's used."""
        return self.node_type is NodeType.JustInTime

    def invoke(self) -> None:
        print(f"Invoking {sanitize_identifier(self.function.__name__)}...")
        result = self.function.__call__(*[pin.read_value() for pin in self.in_pins])
        match self.node_type:
            case NodeType.JustInTime:
                pass
            case NodeType.Standard:
                self.exec_out_pins[0].execute()
            case NodeType.Macro:
                self.exec_out_pins[result[-1]].execute()
            case _:
                raise NotImplementedError(f"CritScriptNode.invoke() is not implemented for case node_type={self.node_type}!")     # TODO write something for this!
        # update out pins
        # NOTE: If this throws an error, it's because there's a mismatch between the values leaving the wrapped function, and the values the node is configured to actually output.
        # TODO add an exception here for cases where that happens so we can explain that to the useer!
        for index, value in enumerate(result):
            self.out_pins[index].write_value(value)


def add_to_crit_script(
        function,
        inputs:tuple[CritScriptValuePin, ...]|None=None,
        outputs:tuple[CritScriptValuePin, ...]|None=None,
        node_type:NodeType=NodeType.Standard,
        exec_out_pins:tuple[ExecutionPin, ...] = tuple(),
    ):
    identifier = sanitize_identifier(function.__name__)
    if node_type is not NodeType.Macro:
        CRIT_SCRIPT_FUNCTIONS[identifier] = (function, inputs, outputs, node_type)
    else:
        CRIT_SCRIPT_FUNCTIONS[identifier] = (function, inputs, outputs, node_type, exec_out_pins)

def make_node(name):
    return CritScriptNode(sanitize_identifier(name))

def crit_script(function):
    """Function decorator for any CritScript function. TODO make this automatically add the function to CritScript!!!
    TODO this stops us from wrapping stuff correctly, find some ways around saving everything in the "wrapper" key in CRIT_SCRIPT_FUNCTIONS. Don't just remove this all hare-brained-like."""
    def wrapper(*args, **kwargs):
        return_values = function(*args, **kwargs)
        if not isinstance(return_values, list):
            raise InvalidCritScriptFunctionException(function.__name__) ## TODO is this necessary?
        return return_values
    return wrapper

CRIT_SCRIPT_FUNCTIONS = dict()
"""Dictionary of all CritScript functions, populated by calling ``add_to_crit_script``.

* See Also: ``add_to_crit_script``"""

def sanitize_identifier(identifier:str):
    """Makes a given identifier comply with the lower-kebab-case variable names in CritScript."""
    return identifier.replace("_", "-").replace(" ","-").lower()