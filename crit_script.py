from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, Iterable

POST_MAINTAINER_CONTACT_INFORMATION = "please email the maintainer at leiflarsongames@gmail.com"

ALL_FUNCTIONS:dict[str, 'CritScriptNodePrototype'] = dict()
"""Dictionary of all CritScript functions, populated by calling ``add_to_crit_script``."""
## TODO important! Update this to use `fn.__qualname__` internally instead of `sanitize_identifier(fn.__name__)`!
## TODO cont. because we can't handle ambiguity!

_IN = False
_OUT = True

class NodeType(Enum):
    JustInTime = 0
    """This node will only be executed "just-in-time", and will not include any execution pins."""
    Standard = 1
    """This node will automatically include an exec-in and exec-out pin."""
    Macro = 2
    """Allows the user to add input and output execution pins manually.
    The list returned by this node's function MUST end with an integer indicating which execution pin to use!

    * Note: ``Macro`` is the only node type that allows manual addition of execution pins."""
    # External = -1   ## TODO implement!
    # """This node is an event which is callable from Python code. It may NOT have any inputs, and will include an
    # exec-out output. May include data outputs."""


class CritScriptException(Exception):
    def __init__(self, message):
        super().__init__(message)

class InvalidCritScriptFunctionException(CritScriptException):
    def __init__(self, function):
        super().__init__(f"{function} must return a list of outputs, but does not.")

class CritScriptPin:
    def __init__(self, name:str="unnamed", node:'CritScriptNode|None'=None, conducted_type:type|None=None, out:bool=False):
        self.name:str = name
        self.node:CritScriptNode|None = node
        self.conducted_type:type|None = conducted_type
        self.out:bool = out
        self.friend:CritScriptPin|None = None   # The other pin this one is connected to.

    def clone_to_new_node(self, node:'CritScriptNode|None', new_pin_type:type, *args, **kwargs):
        return_value = new_pin_type.__init__(name=self.name, node=self.node, *args, **kwargs)
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
        # ## TODO debug block!
        # print(f" self = {self}\n"
        #       f"other = {other}\n")
        if self.out and not other.out:
            # ## TODO debug block!
            # print(f" self.friend = {self.friend}\n"
            #       f"other.friend = {other.friend}\n"
            #       f" self conducts {self.conducted_type}\n"
            #       f"other conducts {other.conducted_type}\n")
            return ( self.friend is None and
                    other.friend is None and
                     (self.conducted_type is other.conducted_type or
                      self.conducted_type is Any or
                      other.conducted_type is Any)) ## Because this doesn't invite trouble at all, no way!!
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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_value:Any = None

    @classmethod
    def from_prototype(cls, node:'CritScriptNode', out:bool, prototype:'CritScriptPinPrototype') -> 'ValuePin':
        if prototype.conducted_type is None:
            raise ValueError(
                "Tried to produce a ValuePin from a CritScriptPinPrototype that conducted None! Was this supposed to be an ExecutionPin's prototype?")
        return ValuePin(
            conducted_type=prototype.conducted_type,
            name=prototype.name,
            node=node,
            out=out,
        )

    def can_read_previous_pin_value(self):
        return self.has_friend() and isinstance(self.friend, ValuePin)

    def read_value(self) -> Any:
        if self.node.is_just_in_time_node():
            raise NotImplementedError("\"just-in-time\" logic is not implemented!")     ## TODO implement just-in-time logic!
        else:
            if self.out:
                return self.last_value
            elif self.last_value is not None:
                return self.last_value  ## If a value's been written in as a "magic number", read it.
            elif self.can_read_previous_pin_value():
                return self.friend.last_value
            else:
                return None

    def write_value(self, value):
        if self.conducted_type is Any:
            self.last_value = value
        elif isinstance(value, self.conducted_type):
            self.last_value = value
        else:
            raise ValueError(
                f"Cannot write a value of type={type(value)} to a pin which conducts type={self.conducted_type}!")

    def has_magic_number(self):
        return not self.out and self.last_value is not None

    def can_add_magic_number(self):
        return not self.out and self.last_value is None

    can_edit_magic_number = has_magic_number


class ExecutionPin(CritScriptPin):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @classmethod
    def from_prototype(cls, node:'CritScriptNode', out:bool, prototype:'str|CritScriptPinPrototype') -> 'ExecutionPin':
        # String-based prototype
        if isinstance(prototype, str):
            return ExecutionPin(
                conducted_type=None,
                name=prototype,
                node=node,
                out=out,
            )
        # CritScriptPinPrototype-based prototype
        if prototype.conducted_type is not None:
            raise ValueError(
                "Tried to produce an ExecutionPin from a CritScriptPinPrototype that did not conduct None! Was this supposed to be a ValuePin's prototype?")
        return ExecutionPin(
            conducted_type=None,
            name=prototype.name,
            node=node,
            out=out,
        )


@dataclass
class Position:
    x:float = 0.0
    y:float = 0.0


@dataclass
class CritScriptPinPrototype:
    conducted_type:type|None = str
    name:str = "unnamed"


@dataclass
class CritScriptNodePrototype:
    function: Callable
    node_type: NodeType = NodeType.Standard,
    inputs: list[CritScriptPinPrototype] | None = None
    outputs: list[CritScriptPinPrototype] | None = None
    exec_inputs: list[str] | None = None
    exec_outputs: list[str] | None = None


class CritScriptNode:
    def __init__(self, function_name):
        # (function, inputs, outputs, node_type, exec_out_pins)
        entry = ALL_FUNCTIONS[_calc_func_identifier(function_name)]

        # default values
        self.node_type: NodeType = NodeType.Standard
        self.in_pins:list[ValuePin] = list()
        self.out_pins:list[ValuePin] = list()
        self.exec_in_pins:list[ExecutionPin] = list()
        self.exec_out_pins:list[ExecutionPin] = list()

        # CREATE VALUES
        self.function: Callable = entry.function

        # Create data pins
        self.node_type = entry.node_type if entry.node_type is not None else NodeType.Standard
        if entry.inputs is not None:
            self.in_pins = list([ValuePin.from_prototype(self, _IN, prototype) for prototype in entry.inputs])
        if entry.outputs is not None:
            self.out_pins = list([ValuePin.from_prototype(self, _OUT, prototype) for prototype in entry.outputs])

        # Create execution pins
        match self.node_type:
            case NodeType.JustInTime:
                pass    # don't bother setting up execution pins on "just-in-time" nodes.
            case NodeType.Standard:
                self.exec_in_pins  = list((ExecutionPin.from_prototype(self, _IN, "exec-in"),))
                self.exec_out_pins = list((ExecutionPin.from_prototype(self, _OUT, "exec-out"),))
            case NodeType.Macro:
                self.exec_in_pins  = (
                    list([ExecutionPin.from_prototype(self,  _IN, prototype) for prototype in entry.exec_inputs])
                        if entry.exec_inputs is not None else
                    list((ExecutionPin.from_prototype(self,  _IN,  "exec-in"),)))
                self.exec_out_pins = (
                    list([ExecutionPin.from_prototype(self, _OUT, prototype) for prototype in entry.exec_outputs])
                        if entry.exec_outputs is not None else
                    list((ExecutionPin.from_prototype(self, _OUT, "exec-out"),)))
            case _:
                raise NotImplementedError(f"CritScriptNode.__init__() is not implemented for case node_type={self.node_type}!")

    def read_all_out_pins(self) -> list:
        """Returns a list of all out pins' data. Primarily for testing."""
        return [pin.read_value() for pin in self.out_pins]

    def is_just_in_time_node(self) -> bool:
        """Whether this Node is invoked as a "just in time" node, or if it needs to be invoked explicitly via its
        execution pin input before it's used."""
        return len(self.exec_in_pins) == 0

    def invoke(self, exec_in_index:int=0, debug=False) -> ExecutionPin | None:
        """Returns the out pin from this node, if it exists."""

        # NOTE: For CritScript users:
        #   If this type hint throws an error, make sure your function is returning a tuple with every data pin's value.
        #   If it's a macro, include the index of the execution out pin that's being used as the last value.
        #   TODO update this note!
        result:Any

        ## CALL THE INTERNAL FUNCTION WITH PARAMETERS FROM GIVEN PINS
        try:
            if self.node_type is NodeType.Macro:
                result = self.function(exec_in_index=exec_in_index,
                                       *[pin.read_value() for pin in self.in_pins])
            else:
                result = self.function(*[pin.read_value() for pin in self.in_pins])
        except Exception as e:
            print(f"Failed while invoking {self.function.__qualname__}, see the following exception:")
            raise e
        finally:
            if debug:
                print(f"Invoked {self.function.__qualname__}")

        ## ensure result is iterable
        if result is None:
            result = tuple()
        elif isinstance(result, Iterable):
            pass
        else:       # is single value
            result = (result,)

        # UPDATE OUTGOING VALUE PINS
        values = result[0:-1] if self.node_type is NodeType.Macro else result
        for index, result_value in enumerate(values):
            # NOTE: If this throws an error, it's probably because there's a mismatch between the values leaving the
            # wrapped function, and the values the node is configured to actually output.
            # TODO add an exception here for cases where that happens so we can explain that to the user!
            self.out_pins[index].write_value(result_value)

        ## SELECT OUTGOING EXECUTION PIN
        # If there is perhaps more than one outgoing execution pin, pull which one to use from the result!
        if self.node_type is NodeType.Macro:
            exec_out_index = result[-1]     # Macros write which execution pin to use in the last position of their returned list.
            return self.exec_out_pins[exec_out_index]
        elif self.node_type is NodeType.JustInTime:
            return None
        else:
            return self.exec_out_pins[0]    # return the only exec-out pin.


## CLASS-LESS FUNCTIONS

def can_run_graph(start_from:ExecutionPin|CritScriptNode):
    """Whether ``run_graph`` can begin running from this node or execution pin."""
    return (not (isinstance(start_from, CritScriptNode) and start_from.is_just_in_time_node()) and
            not (isinstance(start_from, ExecutionPin) and (start_from.has_friend() or not start_from.out))
            )

def run_graph(start_from: ExecutionPin | CritScriptNode):
    """Runs a CritScript graph from the given node or execution pin."""
    start_pin:ExecutionPin
    if isinstance(start_from, CritScriptNode):
        start_from:CritScriptNode
        if start_from.is_just_in_time_node():
            raise ValueError("Cannot start execution from a \"just-in-time\" node!")
            ## TODO is this true? We can probably infer just fine where to start. Wait for CritScript to be used by a GM before deciding on this issue.
        elif start_from.node_type is NodeType.Standard or start_from.node_type is NodeType.Macro:
            in_pin = start_from.exec_in_pins[0]     # Assume the first input execution pin is to be used.
        else: ## NOTE this assumes that the node type is some kind of event, which guarantees an exec-out pin.
            # punt the decision for what the start_pin is to the next if block.
            start_from:ExecutionPin = start_from.exec_out_pins[0]
    elif isinstance(start_from, ExecutionPin):
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
        raise NotImplementedError(f"In CritScript, run() was not implemented for start_from with type={type(start_from)} with value={start_from}.\n"
                                  f"{POST_MAINTAINER_CONTACT_INFORMATION}")     ## NOTE nothing should be able to do this.

    ## NOTE in_pin is guaranteed to be an in-pin by now. This means we can start.

    ## EXECUTION LOOP
    while in_pin and in_pin.node is not None:
        out_pin = in_pin.node.invoke()
        # advance to next in-pin, if available
        if out_pin.has_friend():
            in_pin = out_pin.friend
        else:
            in_pin = None

def make_node(function:Callable):
    """Creates a node from a function which has been submitted with an @crit_script decorator."""
    return CritScriptNode(function)

def _calc_func_identifier(fn:Callable) -> str:
    return sanitize_identifier(fn.__qualname__)

def _add_to_crit_script(
        function,
        inputs:Iterable[CritScriptPinPrototype]|None=None,
        outputs:Iterable[CritScriptPinPrototype]|None=None,
        node_type: NodeType = NodeType.Standard,
        exec_inputs:Iterable[str|CritScriptPinPrototype]|None = None,
        exec_outputs:Iterable[str|CritScriptPinPrototype]|None = None,
    ):
    if isinstance(inputs, tuple):
        inputs = list(inputs)
    if isinstance(outputs, tuple):
        outputs = list(outputs)
    identifier = _calc_func_identifier(function)
    if node_type is NodeType.Macro:
        if exec_inputs is None:
            exec_inputs = list("exec-in")
        if exec_outputs is None:
            exec_outputs = list("exec-out")
        ALL_FUNCTIONS[identifier] = CritScriptNodePrototype(function, node_type, inputs, outputs, exec_inputs, exec_outputs)
    else:
        ALL_FUNCTIONS[identifier] = CritScriptNodePrototype(function, node_type, inputs, outputs)

def sanitize_identifier(identifier:str):
    """Makes a given identifier comply with the lower-kebab-case variable names in CritScript."""
    return identifier.replace("_", "-").replace(" ","-").lower()

## CritScript Decorators

def crit_script(
        inputs:  Iterable[CritScriptPinPrototype] | CritScriptPinPrototype | None = None,
        outputs: Iterable[CritScriptPinPrototype] | CritScriptPinPrototype | None = None,
        just_in_time_node:bool = False,
    ):
    """Function decorator for any CritScript function that isn't a macro.
    TODO document the return types and parameters here with examples!"""
    ## Normalize inputs to be iterable
    if inputs is None:
        inputs = tuple()
    elif not isinstance(inputs, Iterable):
        inputs = (inputs,)
    if outputs is None:
        outputs = tuple()
    elif not isinstance(outputs, Iterable):
        outputs = (outputs,)
    def decorator(function):
        def wrapper(*sub_args, **sub_kwargs):
            return function(*sub_args, **sub_kwargs)
        wrapper.__name__ = function.__name__                        # Ensures decorated functions keep their names.
        wrapper.__qualname__ = function.__qualname__
        node_type = NodeType.JustInTime if just_in_time_node else NodeType.Standard
        _add_to_crit_script(wrapper, inputs, outputs, node_type)    # submits this function to CritScript
        return wrapper
    return decorator

def crit_script_macro(
        inputs:  Iterable[CritScriptPinPrototype] | CritScriptPinPrototype | None=None,
        outputs: Iterable[CritScriptPinPrototype] | CritScriptPinPrototype | None=None,
        exec_inputs:  Iterable[str] | str | None = None,
        exec_outputs: Iterable[str] | str | None = None,
    ):
    """Function decorator for any CritScript function that will become a macro.
    TODO document the return types and parameters here with examples!"""

    ## Normalize inputs to be iterable
    if inputs is None:
        inputs = tuple()
    elif not isinstance(inputs, Iterable):
        inputs  = (inputs,)
    if outputs is None:
        outputs = tuple()
    elif not isinstance(outputs, Iterable):
        outputs = (outputs,)
    if exec_inputs is None:
        exec_inputs = tuple()
    elif not isinstance(exec_inputs, Iterable):
        exec_inputs  = (exec_inputs,)
    if exec_outputs is None:
        exec_outputs = tuple()
    elif not isinstance(exec_outputs, Iterable):
        exec_outputs = (exec_outputs,)
    def decorator(function):
        def wrapper(*sub_args, **sub_kwargs):
            return function(*sub_args, **sub_kwargs)
        wrapper.__name__ = function.__name__  # Ensures decorated functions keep their names.
        wrapper.__qualname__ = function.__qualname__
        _add_to_crit_script(wrapper, inputs, outputs, NodeType.Macro, exec_inputs, exec_outputs) # submits this function to CritScript
        return wrapper
    return decorator

## Decorator paramter shorthand

def Pin(type: type | None = str, name: str = "unnamed") -> CritScriptPinPrototype:
    """Shorthand for prototyping a ValuePin of a given type and name. Used in ``@crit_script`` an ``@crit_script_macro`` parameters"""
    return CritScriptPinPrototype(type, name)

# ## TODO implement bundle pins!
# def MultiPin(type: type | None = str, name: str = "unnamed") -> CritScriptPinPrototype:
#     """Shorthand for prototyping a MultiValuePin of a given type and name."""
#     return CritScriptPinPrototype(type, name)

def Exec(name: str = "exec-unnamed") -> str:
    """Shorthand for prototyping an ExecutionPin of a given name."""
    return name



