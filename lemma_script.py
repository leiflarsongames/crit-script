"""LemmaScript to Python conversions:

"""
from enum import Enum
from typing import Callable

LEMMA_SCRIPT_FUNCTIONS = dict()
"""Dictionary of all Lemma Script functions, populated by calling ``add_to_lemma_script``.

* See Also: ``add_to_lemma_script``"""

def sanitize_identifier(identifier:str):
    """Makes a given identifier comply with the lower-kebab-case variable names in LemmaScript."""
    return identifier.replace("_", "-").replace(" ","-").lower()

class NodeType(Enum):
    JustInTime = 0
    """This node will only be executed "just-in-time", and will not include any execution pins."""
    Standard = 1
    """This node will automatically include an exec-in and exec-out pin."""
    Macro = 2   ## TODO implement!
    """This node automatically includes an exec-in pin, user must add any output execution pins manually.
    The list returned by this node's function MUST end with an integer indicating which execution pin to use!

    * Note: ``Macro`` is the only node type that allows manual addition of execution pins."""
    # External = -1   ## TODO implement!
    # """This node is an event which is callable from Python code. It may NOT have any inputs, and will include an
    # exec-out output."""


class LemmaScriptException(Exception):
    def __init__(self, message):
        super().__init__(message)

class NotActuallyALemmaFunctionException(LemmaScriptException):
    def __init__(self, function):
        super().__init__(f"{function.__name__} must return a list of outputs, but does not.")


class LemmaScriptPin:
    def __init__(self, name:str="unnamed", node:'LemmaScriptNode|None'=None, out:bool=False):
        self.name:str = name
        self.node:LemmaScriptNode|None = node
        self.conducted_type:type|None = None
        self.out:bool = out     # Needs to be set by the LemmaScriptNode constructor!
        self.friend:LemmaScriptPin|None = None  # The other pin this one is connected to.

    def clone_to_new_node(self, node:'LemmaScriptNode|None'=None):
        return_value = LemmaScriptPin(name=self.name, node=self.node)
        return_value.node = node
        return_value.conducted_type = self.conducted_type
        return_value.out = self.out
        return_value.friend = None
        return return_value



    def can_connect(self, other:'LemmaScriptPin') -> bool:
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
    def try_connect(self, other:'LemmaScriptPin') -> bool:
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


class LemmaScriptValuePin(LemmaScriptPin):
    def __init__(self, conducted_type:type|None = None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.conducted_type:type|None = conducted_type

    def get_value(self):
        raise NotImplemented()  # MUST be implemented on each subclass!

class BundlePin(LemmaScriptValuePin):
    pass  ## TODO implement!

class ExecutionPin(LemmaScriptPin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def execute(self):
        """Executes the node that owns the in pin. TODO document better!"""
        if self.has_friend():
            if self.out:
                self.friend.node.invoke()
            else:
                self.node.invoke()
        else:
            pass

    # def execute_backwards(self):
    #     """Executes the node that owns the out pin. TODO document better!"""
    #     if self.has_friend():
    #         if self.out:
    #             self.node.invoke()
    #         else:
    #             self.friend.node.invoke()
    #     else:
    #         pass

class StringPin(LemmaScriptValuePin):
    def __init__(self, last_value:str|None=None, *args, **kwargs,):
        super().__init__(conducted_type=str, *args, **kwargs)
        self.last_value:float|None = last_value

    def get_value(self):
        if self.node.is_just_in_time_node():
            raise NotImplementedError()     ## TODO implement just-in-time logic!
        else:
            return self.last_value

class NumberPin(LemmaScriptValuePin):
    def __init__(self, last_value:float|None=None, *args, **kwargs):
        super().__init__(conducted_type=float, *args, **kwargs)
        self.last_value:float|None = last_value

class Position:
    def __init__(self, x:float=0.0, y:float=0.0):
        self.x:float = x
        self.y:float = y

class LemmaScriptNode:
    def __init__(self, function_name):
        # (function, inputs, outputs, node_type, exec_out_pins)
        entry = LEMMA_SCRIPT_FUNCTIONS[function_name]
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
            case NodeType.Macro:
                self.exec_in_pin = ExecutionPin(name="exec-in", node=self)
                self.exec_out_pins = tuple([p.clone_to_new_node(self) for p in entry[4]]) if entry[4] is not None else tuple((ExecutionPin(name="exec-out", node=self),))
            case _:
                raise NotImplementedError(f"LemmaScriptNode.__init__() is not implemented for case node_type={self.node_type}!")     # TODO write something for this!

    def is_just_in_time_node(self) -> bool:
        """Whether this Node is invoked as a "just in time" node, or if it needs to be invoked explicitly via its
        execution pin input before it's used."""
        return self.node_type is NodeType.JustInTime

    def invoke(self) -> None:
        print(f"Invoking {sanitize_identifier(self.function.__name__)}...")
        result = self.function.__call__(*[pin.get_value() for pin in self.in_pins])
        match self.node_type:
            case NodeType.JustInTime:
                pass
            case NodeType.Standard:
                self.exec_out_pins[0].execute()
            case NodeType.Macro:
                self.exec_out_pins[result[-1]].execute()
            case _:
                raise NotImplementedError(f"LemmaScriptNode.invoke() is not implemented for case node_type={self.node_type}!")     # TODO write something for this!

def add_to_lemma_script(
        function,
        inputs:tuple[LemmaScriptValuePin, ...]|None=None,
        outputs:tuple[LemmaScriptValuePin, ...]|None=None,
        node_type:NodeType=NodeType.Standard,
        exec_out_pins:tuple[ExecutionPin, ...] = tuple(),
    ):
    identifier = sanitize_identifier(function.__name__)
    if node_type is not NodeType.Macro:
        LEMMA_SCRIPT_FUNCTIONS[identifier] = (function, inputs, outputs, node_type)
    else:
        LEMMA_SCRIPT_FUNCTIONS[identifier] = (function, inputs, outputs, node_type, exec_out_pins)

def make_node(name):
    return LemmaScriptNode(sanitize_identifier(name))

def lemma_script(function):
    """Function decorator for any LemmaScript function. TODO make this automatically add the function to lemma script!!!"""
    def wrapper(*args, **kwargs):
        return_values = function(*args, **kwargs)
        if not isinstance(return_values, list):
            raise NotActuallyALemmaFunctionException(function.__name__) ## TODO is this necessary?
        return return_values
    return wrapper

