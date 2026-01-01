"""CritScript to Python conversions:
"""
from dataclasses import dataclass
## TODO planned redesign: make these functions NOT flood the call stack...
# so we'll have to...
#  * have a while loop which starts with an execution pin, and invokes the attached function
#  * have the next execution pin to be called be returned by invoke() instead of returning nothing
#  * set the current execution pin to the newly returned one from invoke()
#  * then loop again until the execution pin has no friend.

from enum import Enum
from typing import Callable, Any

POST_MAINTAINER_CONTACT_INFORMATION = "please email the maintainer at leiflarsongames@gmail.com"

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


class ValuePin(CritScriptPin):
    def __init__(self, conducted_type:type|None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conducted_type:type|None = conducted_type
        self.last_value:Any = None

    def read_value(self) -> Any:
        if self.node.is_just_in_time_node():
            raise NotImplementedError()     ## TODO implement just-in-time logic!
        else:
            return self.last_value

    def write_value(self, value):
        if isinstance(self.last_value, self.conducted_type):
            return self.last_value
        else:
            raise ValueError(f"Cannot write a value of type={value.__class__.__name__} to a pin which conducts type={self.conducted_type}!")

class ExecutionPin(CritScriptPin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_next(self) -> 'ExecutionPin':
        if self.out:
            return self.friend
        return None

@dataclass
class Position:
    x:float = 0.0
    y:float = 0.0

class CritScriptNode:
    def __init__(self, function_name):
        # (function, inputs, outputs, node_type, exec_out_pins)
        entry = CRIT_SCRIPT_FUNCTIONS[function_name]
        print(f"entry = {entry}")
        self.function:Callable = entry[0]

        # default values
        self.in_pins:tuple[ValuePin] = tuple()
        self.out_pins:tuple[ValuePin] = tuple()
        self.node_type:NodeType = NodeType.Standard
        self.exec_in_pin:ExecutionPin = None
        self.exec_out_pins:tuple[ExecutionPin] = tuple()

        # load real values
        if entry[1] is not None:
            self.in_pins = tuple([p.clone_to_new_node(self) for p in entry[1]])
        if entry[2] is not None:
            self.out_pins:tuple[ValuePin] = tuple([p.clone_to_new_node(self) for p in entry[2]])
            for index, out_pin in enumerate(self.out_pins):
                self.out_pins[index] = ValuePin(
                    conducted_type = self.out_pins[index].conducted_type,
                    name = self.out_pins[index].name,
                    node = self,
                )
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
        return self.exec_in_pin is None

    def invoke(self) -> ExecutionPin | None:
        """Returns the out pin from this node, if it exists."""
        print(f"Invoking {sanitize_identifier(self.function.__name__)}...")

        ## CALL THE INTERNAL FUNCTION WITH PARAMETERS FROM GIVEN PINS
        result = self.function.__call__(*[pin.read_value() for pin in self.in_pins])

        # UPDATE OUTGOING VALUE PINS
        last_index = -2 if self.node_type is NodeType.Macro else -1
        for index, result_value in enumerate(result[0:last_index]):
            # NOTE: If this throws an error, it's because there's a mismatch between the values leaving the wrapped function, and the values the node is configured to actually output.
            # TODO add an exception here for cases where that happens so we can explain that to the user!
            self.out_pins[index].write_value(result_value)

        ## SELECT OUTGOING EXECUTION PIN
        # If there is perhaps more than one outgoing execution pin, pull which one to use from the result!
        if self.node_type is NodeType.Macro:
            exec_out_index = result[-1]     # Macros write which execution pin to use in the last position of their returned tuple.
            return self.exec_out_pins[exec_out_index]
        elif self.node_type is NodeType.JustInTime:
            return None
        else:
            return self.exec_out_pins[0]    # return the only exec-out pin.



def can_run(start_from:ExecutionPin|CritScriptNode):
    return (not (isinstance(start_from, CritScriptNode) and start_from.is_just_in_time_node()) and
            not (isinstance(start_from, ExecutionPin) and (start_from.has_friend() or not start_from.out))
            )
def run(start_from:ExecutionPin|CritScriptNode):
    start_pin:ExecutionPin
    if isinstance(start_from, CritScriptNode):
        start_from:CritScriptNode
        if start_from.is_just_in_time_node():
            raise ValueError("Cannot start execution from a \"just-in-time\" node!")
            ## TODO is this true? We can probably infer just fine where to start. Wait for CritScript to be used by a GM before deciding on this issue.
        elif start_from.node_type is NodeType.Standard or start_from.node_type is NodeType.Macro:
            in_pin = start_from.exec_in_pin
        else: ## NOTE this assumes that the node type is some kind of event, which guarantees an exec-out pin.
            # punt the decision for what the start_pin is to the next if block.
            start_from:ExecutionPin = start_from.exec_out_pins[0]
    if isinstance(start_from, ExecutionPin):
        start_from:ExecutionPin
        if start_from.out:
            if not start_from.has_friend():
                raise ValueError("Cannot start execution from an \"out\" node with no connections!")
            else:
                in_pin = start_from.friend
        else:
            in_pin = start_from
    else:
        ## Posts maintainer's contact information and each parameter. Note that more context is probably needed.
        raise NotImplementedError(f"In CritScript, run() was not implemented for start_from with type={start_from.__class__.__name__} with value={start_from}.\n"
                                  f"{POST_MAINTAINER_CONTACT_INFORMATION}")     ## NOTE nothing should be able to do this.

    ## NOTE in_pin is guaranteed to be an in-pin by now.

    ## EXECUTION LOOP
    while in_pin and in_pin.node is not None:
        """TODO document better!"""
        out_pin = in_pin.node.invoke()
        if out_pin.has_friend():
            in_pin = out_pin.friend
        else:
            in_pin = None

def make_node(name):
    return CritScriptNode(sanitize_identifier(name))

def add_to_crit_script(
        function,
        inputs:tuple[ValuePin, ...]|None=None,
        outputs:tuple[ValuePin, ...]|None=None,
        node_type:NodeType=NodeType.Standard,
        exec_out_pins:tuple[ExecutionPin, ...] = tuple(),
    ):
    identifier = sanitize_identifier(function.__name__)
    if node_type is not NodeType.Macro:
        CRIT_SCRIPT_FUNCTIONS[identifier] = (function, inputs, outputs, node_type)
    else:
        CRIT_SCRIPT_FUNCTIONS[identifier] = (function, inputs, outputs, node_type, exec_out_pins)

def crit_script(function, ):
    """Function decorator for any CritScript function. TODO make this automatically add the function to CritScript!!!"""
    def subfunction(*args, **kwargs):

        return_values = function(*args, **kwargs)
        if not isinstance(return_values, list):
            raise InvalidCritScriptFunctionException(function.__name__) ## TODO is this necessary?
        return return_values
    subfunction.__name__ = function.__name__    # this is hilarious.
    return subfunction

# def crit_script_plugin(class):


CRIT_SCRIPT_FUNCTIONS = dict()
"""Dictionary of all CritScript functions, populated by calling ``add_to_crit_script``."""

def sanitize_identifier(identifier:str):
    """Makes a given identifier comply with the lower-kebab-case variable names in CritScript."""
    return identifier.replace("_", "-").replace(" ","-").lower()