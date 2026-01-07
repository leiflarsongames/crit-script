"""Implements internal functionality for CritScript.

``@author``:  Leif Larson Games"""

from dataclasses import dataclass
from enum import Enum
from typing import Callable, Any, Iterable

## NOTE: should this be removed to prevent polluting the console? I do like people emailing me...
print("Thank you for using CritScript. Please send any questions or feedback to leiflarsongames@gmail.com!")

## TODO move this to a config file or something? It'd be a TOML in Rust, not sure what to do here.
## Low priority for now, I like when people email me.
POST_MAINTAINER_CONTACT_INFORMATION = "please email the maintainer at leiflarsongames@gmail.com"

ALL_FUNCTIONS:dict[str, 'NodePrototype'] = dict()
"""Dictionary of all CritScript functions, populated by adding ``@crit_script`` or ``@crit_script_macro`` decorators on
functions."""

ALL_WAKE_UP_FUNCTIONS:dict[str, Callable] = dict()
"""Dictionary of all CritScript wake-up functions, populated by adding ``@wake_up`` to a function.

* See also: ``@wake_up`` decorator"""


## TODO decide on a policy for using lists vs tuples for these functions with performance (memory, run-time) in mind!

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
    # exec-out output. May include value outputs."""


class CritScriptException(Exception):
    def __init__(self, message):
        super().__init__(message)

class InvalidCritScriptFunctionException(CritScriptException):
    def __init__(self, function):
        super().__init__(f"{function} must return a list of outputs, but does not.")

class CritScriptPin:
    def __init__(self, name:str="unnamed", node: 'Node|None' =None, conducted_type: type | None=None, out:bool=False):
        self.name:str = name
        self.node: Node | None = node
        self.conducted_type:type|None = conducted_type
        self.out:bool = out
        self.friend:CritScriptPin|None = None   # The other pin this one is connected to.

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
    def __init__(self, index:int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.last_value:Any = None
        self.index:int = index

    @classmethod
    def from_prototype(cls, node: 'Node', out:bool, prototype: 'PinPrototype', index:int) -> 'ValuePin':
        if prototype.conducted_type is None:
            raise ValueError(
                "Tried to produce a ValuePin from a PinPrototype that conducted None! Was this supposed to be an ExecutionPin's prototype?")
        return ValuePin(
            conducted_type=prototype.conducted_type,
            name=prototype.name,
            node=node,
            out=out,
            index=index
        )

    def read_value(self) -> Any:
        if self.node.is_just_in_time_node():
            raise NotImplementedError("\"just-in-time\" logic is not implemented!") # TODO implement just-in-time logic!
        else:
            if self.out:
                return self.last_value
            elif self.last_value is not None:
                return self.last_value  ## If a value's been written in as a "magic number", read it.
            elif self.has_friend() and isinstance(self.friend, ValuePin):
                # "if this in-pin can read the previous value, then..."
                return self.friend.last_value
            else:
                return None

    def write_value(self, value):
        print(f'conducts {self.conducted_type}')  # TODO remove debug!
        if self.conducted_type is not None and not isinstance(self.conducted_type, type):
            raise InvalidCritScriptFunctionException(
                f'{self.node.function.__qualname__}\'s value pin @ index = {self.index} is not set up properly. It ' +
                f'believes it is conducting "{self.conducted_type}" when it should be conducting either None or a ' +
                f'type!\n' +
                f'TIP: Did you write the pin prototype like "Pin(type=\'pin_name\', /* ... */)"?' ## TODO wait how would this actually happen?
            )
        if self.conducted_type is Any:
            self.last_value = value
        elif isinstance(value, self.conducted_type):
            self.last_value = value
        else:
            raise ValueError(
                f"Cannot write a value of type = {type(value)} to a pin which conducts type = {self.conducted_type}!")

    # def has_magic_number(self):
    #     return not self.out and self.last_value is not None
    #
    # def can_add_magic_number(self):
    #     return not self.out and self.last_value is None
    #
    # can_edit_magic_number = has_magic_number


class ExecutionPin(CritScriptPin):
    def __init__(self, index:int, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._index:int = index

    @property
    def index(self) -> int:
        return self._index

    @classmethod
    def from_prototype(cls, node: 'Node', out:bool, prototype: 'str|PinPrototype', index:int) -> 'ExecutionPin':
        # String-based prototype
        if isinstance(prototype, str):
            return ExecutionPin(
                conducted_type=None,
                name=prototype,
                node=node,
                out=out,
                index=index,
            )
        # PinPrototype-based prototype
        if prototype.conducted_type is not None:
            raise ValueError(
                "Tried to produce an ExecutionPin from a PinPrototype that did not conduct None! Was this supposed to be a ValuePin's prototype?")
        return ExecutionPin(
            conducted_type=None,
            name=prototype.name,
            node=node,
            out=out,
            index=index,
        )

@dataclass
class PinPrototype:
    conducted_type:type|None = str
    name:str = "unnamed"

@dataclass
class NodePrototype:
    function: Callable
    node_type: NodeType = NodeType.Standard,
    inputs: list[PinPrototype] | None = None
    outputs: list[PinPrototype] | None = None
    exec_inputs: list[str] | None = None
    exec_outputs: list[str] | None = None

class Node:
    def __init__(self, function_name):
        # (function, inputs, outputs, node_type, exec_out_pins)
        entry = ALL_FUNCTIONS[make_function_identifier(function_name)]

        # default values
        self.node_type: NodeType = NodeType.Standard
        self.in_pins:list[ValuePin] = list()
        self.out_pins:list[ValuePin] = list()
        self.exec_in_pins:list[ExecutionPin] = list()
        self.exec_out_pins:list[ExecutionPin] = list()
        self.memory:Any = None      # Note: is not initialized here.

        # CREATE VALUES
        self.function: Callable = entry.function

        # Create value pins
        self.node_type = entry.node_type if entry.node_type is not None else NodeType.Standard
        if entry.inputs is not None:
            self.in_pins = list([ValuePin.from_prototype(self, _IN, prototype, index)
                                 for index, prototype in enumerate(entry.inputs)])
        if entry.outputs is not None:
            self.out_pins = list([ValuePin.from_prototype(self, _OUT, prototype, index)
                                  for index, prototype in enumerate(entry.outputs)])

        # Create execution pins
        match self.node_type:
            case NodeType.JustInTime:
                pass    # don't bother setting up execution pins on "just-in-time" nodes.
            case NodeType.Standard:
                self.exec_in_pins  = list((ExecutionPin.from_prototype(self, _IN, "exec-in", 0),))
                self.exec_out_pins = list((ExecutionPin.from_prototype(self, _OUT, "exec-out", 0),))
            case NodeType.Macro:
                self.exec_in_pins  = (
                    list([ExecutionPin.from_prototype(self,  _IN, prototype, index)
                          for index, prototype in enumerate(entry.exec_inputs)])
                        if entry.exec_inputs is not None else
                    list((ExecutionPin.from_prototype(self,  _IN,  "exec-in", 0),)))
                self.exec_out_pins = (
                    list([ExecutionPin.from_prototype(self, _OUT, prototype, index)
                          for index, prototype in enumerate(entry.exec_outputs)])
                        if entry.exec_outputs is not None else
                    list((ExecutionPin.from_prototype(self, _OUT, "exec-out", 0),)))
            case _:
                raise NotImplementedError(f"{Node.__init__.__qualname__} is not implemented for case node_type={self.node_type}!")

    def read_all_out_pins(self) -> list:
        """Returns a list of all out pins' values. Primarily for testing."""
        return [pin.read_value() for pin in self.out_pins]

    def is_just_in_time_node(self) -> bool:
        """Whether this Node is invoked as a "just in time" node, or if it needs to be invoked explicitly via its
        execution pin input before it's used."""
        return len(self.exec_in_pins) == 0

    def summon_values(self):
        if not self.is_just_in_time_node():
            return
        for in_pin in self.in_pins:
            if in_pin.has_friend() and in_pin.friend.node.is_just_in_time_node():
                in_pin.friend.node.invoke()
            else:
                msg_added:str = ' because a node was not attached to that pin and it did not have a magic number!'
                if in_pin.has_friend() and in_pin.friend.node is not None:
                    msg_added = (f' because the connected {make_function_identifier(self.function)} failed to give a '
                                 f'value for its pin "{in_pin.friend.name}" when invoked just-in-time!')
                raise CritScriptException(
                    f'"just-in-time" node {make_function_identifier(self.function)} failed to summon needed value from '
                    f'value pin "{in_pin.name}"' + msg_added)

    def invoke(self, exec_in_index:int=0, debug=False) -> ExecutionPin | None:
        """Returns the out pin from this node, if it exists."""

        # NOTE: For CritScript users:
        #   If this type hint throws an error, make sure your function is returning a tuple with every data pin's value.
        #   If it's a macro, include the index of the execution out pin that's being used as the last value.
        #   TODO update this note!
        result:Any

        node_context_object = NodeContext(self, exec_in_index, debug)
        kwargs = dict()
        kwargs["ctx"] = node_context_object

        if not self.is_just_in_time_node():
            # for all in-pins attached to just-in-time nodes, do the just-in-time logic for those nodes!
            for in_pin in self.in_pins:
                if (in_pin.friend is not None and
                    in_pin.friend.node is not None and
                    in_pin.friend.node.is_just_in_time_node()
                    ):
                    in_pin.friend.node.summon_values()    # Only for "just-in-time" nodes.

        ## CALL THE INTERNAL FUNCTION WITH PARAMETERS FROM GIVEN PINS
        try:
            # print(f"CALLING FUNCTION: {self.function.__qualname__} ----------------")                                                               # TODO is debug
            # print(f'Args given:\n\t{'\n\t'.join((str(node_context_object), *[str(pin.read_value()) for pin in self.in_pins]))}')                    # TODO is debug
            # print(f'Arg types given:\n\t{'\n\t'.join((str(type(node_context_object)), *[str(type(pin.read_value())) for pin in self.in_pins]))}')   # TODO is debug
            result = self.function(
                node_context_object,                            # Node context object
                *[pin.read_value() for pin in self.in_pins],    # Pin arguments
                )
            # print(f'Args received:\n\t{'\n\t'.join([str(elem) for elem in _make_iterable(result)])}')               # TODO is debug
            # print(f'Arg types received:\n\t{'\n\t'.join([str(type(elem)) for elem in _make_iterable(result)])}')    # TODO is debug
        except Exception as e:
            print(f"Failed while invoking {self.function.__qualname__}, see the following exception:")
            raise e
        finally:
            if debug:
                print(f"Invoked {self.function.__qualname__}")

        ## ensure result is iterable
        result = _make_iterable(result)

        # UPDATE OUTGOING VALUE PINS
        for index, result_value in enumerate(result):
            # NOTE: If this throws an error, it's probably because there's a mismatch between the values leaving the
            # wrapped function, and the values the node is configured to actually output.
            # TODO add an exception here for cases where that happens so we can explain that to the user!
            self.out_pins[index].write_value(result_value)

        ## SELECT OUTGOING EXECUTION PIN
        if self.node_type is NodeType.JustInTime:
            return None
        else:
            return self.exec_out_pins[node_context_object.exec_out_index]

class NodeContext:
    def __init__(
        self,
        node: Node,
        exec_in_index: int = 0,
        debug:bool = False):
        self._node:Node = node
        self.exec_in_index:int = exec_in_index
        self.exec_out_index:int = 0
        self.debug:bool = debug

    @property
    def memory(self) -> Any:
        return self._node.memory

    @memory.setter
    def memory(self, value:Any) -> None:
        self._node.memory = value

    def get_node(self):
        """This is probably overkill for what you need, but if you really need access to the node, here it is."""
        return self._node


## CLASS-LESS FUNCTIONS

def can_run_graph(start_from: ExecutionPin | Node):
    """Whether ``run_graph`` can begin running from this node or execution pin."""
    return (not (isinstance(start_from, Node) and start_from.is_just_in_time_node()) and
            not (isinstance(start_from, ExecutionPin) and (start_from.has_friend() or not start_from.out))
            )

def run_graph(start_from: ExecutionPin | Node):
    """Runs a CritScript graph from the given node or execution pin."""
    start_pin:ExecutionPin
    if isinstance(start_from, Node):
        start_from:Node
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
        raise NotImplementedError(f"In CritScript, {run_graph} was not implemented for start_from with type={type(start_from)} with value={start_from}.\n"
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
    rv = Node(function)
    # self.wake_up()    ## TODO uncomment!
    return rv

def make_function_identifier(fn:Callable) -> str:
    return sanitize_identifier(fn.__qualname__)

def _add_to_crit_script(
        function,
        inputs: Iterable[PinPrototype] | None=None,
        outputs: Iterable[PinPrototype] | None=None,
        node_type: NodeType = NodeType.Standard,
        exec_inputs: Iterable[str | PinPrototype] | None = None,
        exec_outputs: Iterable[str | PinPrototype] | None = None,
    ):
    if isinstance(inputs, tuple):
        inputs = list(inputs)
    if isinstance(outputs, tuple):
        outputs = list(outputs)
    identifier = make_function_identifier(function)
    if node_type is NodeType.Macro:
        if exec_inputs is None:
            exec_inputs = list("exec-in")
        if exec_outputs is None:
            exec_outputs = list("exec-out")
        ALL_FUNCTIONS[identifier] = NodePrototype(function, node_type, inputs, outputs, exec_inputs, exec_outputs)
    else:
        ALL_FUNCTIONS[identifier] = NodePrototype(function, node_type, inputs, outputs)

def sanitize_identifier(identifier:str):
    """Makes a given identifier comply with the lower-kebab-case variable names in CritScript."""
    return identifier.replace("_", "-").replace(" ","-").lower()

## CritScript Decorators

def _make_iterable(obj:Any) -> Iterable:
    """Turns an input into an appropriate iterable.

    * ``None`` -> gives an empty iterable of length 0.
    * ``Object`` -> gives an iterable of length 1 containing that object.
    * ``Iterable`` -> simply returns the iterable."""
    if obj is None:
        return tuple()      # empty tuple
    elif not isinstance(obj, Iterable):
        return (obj,)  # single element tuple
    return obj         # no change made to iterable

# TODO enable scalable parameter counts
def crit_script(
        # un-normalized user inputs
        inputs: Iterable[PinPrototype] | PinPrototype |
                Iterable[str] | str |
                None = None,
        outputs: Iterable[PinPrototype] | PinPrototype |
                 Iterable[str] | str |
                 None = None,
        aliases: str | Iterable[str] | None = None,
        # end of un-normalized user inputs
        just_in_time_node:bool = False,
    ):
    """Function decorator for any CritScript function that isn't a macro.
    TODO document the return types and parameters here with examples!"""
    ## Normalize inputs to be iterable
    inputs = _make_iterable(inputs)
    outputs = _make_iterable(outputs)
    aliases = [sanitize_identifier(alias) for alias in _make_iterable(aliases)]

    ## TODO use aliases!

    def decorator(function):
        def wrapper(*sub_args, **sub_kwargs):
            return function(*sub_args, **sub_kwargs)
        wrapper.__name__ = function.__name__                        # Ensures decorated functions keep their names.
        wrapper.__qualname__ = function.__qualname__
        node_type = NodeType.JustInTime if just_in_time_node else NodeType.Standard
        _add_to_crit_script(wrapper, inputs, outputs, node_type)    # submits this function to CritScript
        return wrapper
    return decorator

# TODO enable scalable parameter counts
def crit_script_macro(
        # un-normalized user inputs
        inputs: Iterable[PinPrototype] | PinPrototype |
                Iterable[str] | str |
                None=None,
        outputs: Iterable[PinPrototype] | PinPrototype |
                 Iterable[str] | str |
                 None=None,
        exec_inputs:  Iterable[str] | str | None = None,
        exec_outputs: Iterable[str] | str | None = None,
        aliases:      Iterable[str] | str | None = None,
        # end of un-normalized user inputs
    ):
    """Function decorator for any CritScript function that will become a macro.
    TODO document the return types and parameters here with examples!"""

    ## Normalize inputs to be iterable
    inputs = _make_iterable(inputs)
    outputs = _make_iterable(outputs)
    exec_inputs = _make_iterable(exec_inputs)
    exec_outputs = _make_iterable(exec_outputs)
    aliases = [sanitize_identifier(alias) for alias in _make_iterable(aliases)]

    ## TODO use aliases!

    def decorator(function):
        def wrapper(*sub_args, **sub_kwargs):
            return function(*sub_args, **sub_kwargs)
        wrapper.__name__ = function.__name__  # Ensures decorated functions keep their names.
        wrapper.__qualname__ = function.__qualname__
        _add_to_crit_script(wrapper, inputs, outputs, NodeType.Macro, exec_inputs, exec_outputs) # submits this function to CritScript
        return wrapper
    return decorator

def wake_up(
    target_function:Callable
):
    """Decorator. The wrapped function is called on a node TODO explain how this stuff works! Is called on a node immediately after it is created in ``make_node``."""
    def decorator(wrapped_function):
        def wrapper(*sub_args, **sub_kwargs):
            return wrapped_function(*sub_args, **sub_kwargs)
        wrapper.__name__ = wrapped_function.__name__  # Ensures decorated functions keep their names.
        wrapper.__qualname__ = wrapped_function.__qualname__
        ## adds this wake-up routine to ``ALL_WAKE_UP_FUNCTIONS``.
        ALL_WAKE_UP_FUNCTIONS[make_function_identifier(target_function)] = wrapper
        return wrapper
    return decorator


## Decorator parameter shorthand

def Pin(name: str = "unnamed", type: type | None = Any) -> PinPrototype:
    """Shorthand for prototyping a ValuePin of a given type and name. For use in ``@crit_script`` and
    ``@crit_script_macro`` parameters.

    * Note: You may also opt to give a string instead, if the conducted type may be ``Any``."""
    return PinPrototype(type, name)

def Exec(name: str = "exec-unnamed") -> str:
    """Shorthand for prototyping an ExecutionPin of a given name. For use in ``@crit_script_macro`` parameters."""
    return name