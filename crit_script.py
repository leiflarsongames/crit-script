"""Implements functionality internal to CritScript.

``@author``: Leif Games leiflarsongames@gmail.com"""

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

class CritScriptValueException(CritScriptException):
    def __init__(self, message):
        super().__init__(message)

class CritScriptStopGraph(StopIteration):
    def __init__(self, msg):
        super().__init__(msg)

class CritScriptPin:
    def __init__(self, name:str="unnamed", node: 'Node|None' =None, conducted_type: type | None=None, out:bool=False, split_format:str|None=None, split_pin_count:int=1, tail:bool=False):
        self.name:str = name
        self.node: Node | None = node
        self.conducted_type:type|None = conducted_type
        self.out:bool = out
        self.split_format = split_format,
        self.split_pin_count = split_pin_count,
        self.tail = tail,
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
            index=index,
            split_format = prototype.split_format,
            split_pin_count = prototype.split_pin_count,
            tail = prototype.tail,
        )

    def read_value(self) -> Any:
        # Calculate the read value fresh each time it is called for.
        # TODO this should probably be optimized to only run if there are changes in initial conditions. Not the
        # end of the world if we cant because operations with high runtime cost should be explicitly executed nodes
        # anyways, but y'know. No need to multiply the same two numbers six hundred times when we could just do it
        # once. But also should dice should be rerolled each time? I'd like to try some A-B testing on this, if at all
        # possible!
        if self.node.is_just_in_time_node():
            ## TODO what are we doing calling this on EVERY PIN!?
            self.node.invoke(debug=True)    # begin propagating "just-in-time" logic
            return self.last_value
            # TODO make sure "just-in-time" logic isn't implemented in more places than necessary!
            # raise NotImplementedError("\"just-in-time\" logic is not implemented!") # TODO implement just-in-time logic!
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
        # print(f'conducts {self.conducted_type}')  # TODO remove debug!
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
                split_format = prototype.split_format,
                split_pin_count = prototype.split_pin_count,
                tail = prototype.tail,
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
    split_format:str|None = None
    split_pin_count:int = 1
    tail:bool = False

    def can_split_pin(self) -> bool:
        return self.split_format is not None

@dataclass
class NodePrototype:
    function: Callable
    node_type: NodeType = NodeType.Standard,
    inputs: list[PinPrototype] | None = None
    outputs: list[PinPrototype] | None = None
    exec_inputs: list[str] | None = None
    exec_outputs: list[str] | None = None
    category: str | None = None     # used for searching

class Node:
    def __init__(self):
        self._name = "NO-DEBUG-NAME-ASSIGNED"
        self.node_type: NodeType = NodeType.Standard
        self.in_pins: list[ValuePin] = list()
        self.out_pins: list[ValuePin] = list()
        self.exec_in_pins: list[ExecutionPin] = list()
        self.exec_out_pins: list[ExecutionPin] = list()
        self.memory: Any = None
        self.friend: Any = None     # A head node's friend is its connected tail node, and vice versa.
        self.tail: bool = False
        self.function:Callable|None = None

    @classmethod
    def _make_head_node(cls, function) -> 'Node':
        """Returns the created node. If multiple nodes are created, returns the head node.

        Note to User: You're probably looking for ``make_node``."""
        node = Node()
        node._name = make_crit_script_identifier(function) # DEBUG ONLY
        entry = ALL_FUNCTIONS[make_crit_script_identifier(function)]

        # default values
        has_tail = False
        tail_node = Node()

        # CREATE VALUES
        node.function: Callable = entry.function

        def attach_pin(
                from_prototype_method: Callable,
                out: bool,
                prototype: object,
                head: Node,
                tail: Node,
                head_target: list,
                tail_target: list
        ) -> bool:
            """Attaches a group of pins to the given head and tail nodes."""
            pin:CritScriptPin
            if prototype.tail:
                pin = from_prototype_method(tail, out, prototype, len(tail_target))
                tail_target.append(pin)
            else:
                pin = from_prototype_method(head, out, prototype, len(head_target))
                head_target.append(pin)
            return True

        # Create value pins
        node.node_type = entry.node_type if entry.node_type is not None else NodeType.Standard
        inputs = make_iterable(entry.inputs)
        for prototype in inputs:
            attach_pin(ValuePin.from_prototype, _IN, prototype,
                       node, tail_node,
                       node.in_pins, tail_node.in_pins)
        outputs = make_iterable(entry.outputs)
        for prototype in outputs:
            attach_pin(ValuePin.from_prototype, _OUT, prototype,
                       node, tail_node,
                       node.out_pins, tail_node.out_pins)

        # Create execution pins
        match node.node_type:
            case NodeType.JustInTime:
                pass    # don't bother setting up execution pins on "just-in-time" nodes.
            case NodeType.Standard:
                node.exec_in_pins  = list((ExecutionPin.from_prototype(node, _IN, Exec("exec-in"), 0),))
                node.exec_out_pins = list((ExecutionPin.from_prototype(node, _OUT, Exec("exec-out"), 0),))
            case NodeType.Macro:
                ## TODO refactor to allow head-tail nodes!
                node.exec_in_pins  = (
                    list([ExecutionPin.from_prototype(node,  _IN, prototype, index)
                          for index, prototype in enumerate(entry.exec_inputs)])
                        if entry.exec_inputs is not None else
                    list((ExecutionPin.from_prototype(node,  _IN,  Exec("exec-in"), 0),)))
                node.exec_out_pins = (
                    list([ExecutionPin.from_prototype(node, _OUT, prototype, index)
                          for index, prototype in enumerate(entry.exec_outputs)])
                        if entry.exec_outputs is not None else
                    list((ExecutionPin.from_prototype(node, _OUT, Exec("exec-out"), 0),)))
            case _:
                raise NotImplementedError(f"{Node.__init__.__qualname__} is not implemented for case node_type={node.node_type}!")
        # initialize the node, if it has a wake_up() function bound to it.
        node.wake_up()

        ## attach tail node if it exists
        if has_tail:
            node.friend = tail_node
            tail_node.friend = node

        return node

    def get_node(self):
        """Returns self. Note: you probably thought you were calling NodeContext.get_node(), not Node.get_node(). You can just use the node directly if this is what you're using.

        e.g., ``node.get_node().out_pins[0].read_value()`` can be simplified to ``node.out_pins[0].read_value()``."""
        return self

    def wake_up(self):
        if make_crit_script_identifier(self.function) in ALL_WAKE_UP_FUNCTIONS:
            ALL_WAKE_UP_FUNCTIONS[make_crit_script_identifier(self.function)](self)

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
                    msg_added = (f' because the connected {make_crit_script_identifier(self.function)} failed to give a '
                                 f'value for its pin "{in_pin.friend.name}" when invoked just-in-time!')
                raise CritScriptException(
                    f'"just-in-time" node {make_crit_script_identifier(self.function)} failed to summon needed value from '
                    f'value pin "{in_pin.name}"' + msg_added)

    def invoke(self, exec_in_index:int=0, debug=False) -> ExecutionPin | None:
        """Returns the out pin from this node, if it exists."""

        # NOTE: For CritScript users:
        #   If this type hint throws an error, make sure your function is returning a tuple with every data pin's value.
        #   If it's a macro, include the index of the execution out pin that's being used as the last value.
        #   TODO update this note!
        result:Any

        ## TODO this could be a source of optimization? When we're done building, we gotta profile this stuff.
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
        result = make_iterable(result)

        # UPDATE OUTGOING VALUE PINS
        for index, result_value in enumerate(result):
            # NOTE: If this throws an error, it's probably because there's a mismatch between the values leaving the
            # wrapped function, and the values the node is configured to actually output.
            # TODO add an exception here for cases where that happens so we can explain that to the user!
            self.out_pins[index].write_value(result_value)

        ## SELECT OUTGOING EXECUTION PIN
        if self.node_type is NodeType.JustInTime:
            return None
        elif node_context_object.exec_out_index is not None:
            return self.exec_out_pins[node_context_object.exec_out_index]
        else:
            return None
        ## TODO handle if the ``exec_out_index`` is out of range!

    def refresh_values_as_just_in_time_node(self):
        ## TODO procedurally implement "just-in-time" logic completely internal to this function!
        pass

class NodeContext:
    def __init__(
        self,
        node: Node,
        exec_in_index: int = 0,
        debug:bool = False):
        self._node:Node = node
        self.exec_in_index:int = exec_in_index
        self.exec_out_index:int|None = 0        # Note: this is set to None by functions which intentionally end a graph's execution.
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

def run_graph(start_from: ExecutionPin | Node) -> None:
    """Runs a CritScript graph from the given node or execution pin."""
    start_pin:ExecutionPin
    if isinstance(start_from, Node):
        start_from:Node
        if start_from.is_just_in_time_node():
            raise ValueError("Cannot start execution from a \"just-in-time\" node!")
            ## TODO is this true? We can probably infer just fine where to start. Wait for CritScript to be used by a GM before deciding on this issue.
            # Yeah, this would actually be pretty vague if our just-in-time node had multiple connections. Again, see if people need this feature before bothering further.
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
        out_pin = in_pin.node.invoke(in_pin.index)
        # advance to next in-pin, if available
        if out_pin is not None and out_pin.has_friend():
            in_pin = out_pin.friend
        else:
            in_pin = None

def make_node(function:Callable|str):
    """Creates a node from a function which has been submitted with a @crit_script or @crit_script_macro decorator."""
    if isinstance(function, str):
        if function in ALL_FUNCTIONS:
            function = ALL_FUNCTIONS[function]
        else:
            raise KeyError(f"Cannot make_node of function named {function}!")
    rv = Node._make_head_node(function)
    # self.wake_up()    ## TODO uncomment!
    return rv

def sanitize_identifier(identifier:str):
    """Makes a given identifier comply with the lower-kebab-case variable names in CritScript."""
    return identifier.replace("_", "-").replace(" ","-").lower()

def make_crit_script_identifier(fn:Callable) -> str:
    return sanitize_identifier(fn.__qualname__)

def make_iterable(obj:Any) -> Iterable:
    """Turns an input into an appropriate iterable.

    * ``None`` -> gives an empty iterable of length 0.
    * ``Object`` -> gives an iterable of length 1 containing that object.
    * ``Iterable`` -> simply returns the iterable.

    Note: Use alternative function ``make_mutable_iterable`` if you need to change the resulting iterable. This function does not provide any guarantees of stability when the iterable is mutated thereafter TODO check if mutating a result of this function affects the mutable iterable passed in!"""
    if obj is None:
        return tuple()      # empty tuple
    elif not isinstance(obj, Iterable):
        return (obj,)       # single element tuple
    return obj              # no change

def make_mutable_iterable(obj:Any) -> list:
    """Turns an input into an appropriate list.

        * ``None`` -> gives an empty list of length 0.
        * ``Object`` -> gives a list of length 1 containing that object.
        * ``Iterable`` -> returns as a list instead of whatever iterable type it was before.

    Note: Alternative function ``make_iterable`` is often less memory intensive for lists of length 0 and 1. TODO fact check this!"""
    if obj is None:
        return list()   # empty list
    elif not isinstance(obj, Iterable):
        return [obj,]   # single element list
    return list(obj)    # cast to list

def delete_from_crit_script(name:Callable|str):
    if isinstance(name, Callable):
        identifier = make_crit_script_identifier(function)
    else:
        identifier = sanitize_identifier(custom_name)
    del ALL_FUNCTIONS[identifier]

def _add_to_crit_script(
        function,
        inputs: Iterable[PinPrototype] | None=None,
        outputs: Iterable[PinPrototype] | None=None,
        node_type: NodeType = NodeType.Standard,
        exec_inputs: Iterable[str | PinPrototype] | None = None,
        exec_outputs: Iterable[str | PinPrototype] | None = None,
        category: str|None = None,      # Note: Category is NOT normalized to be a value.
        custom_name: str|None = None,
    ):
    if isinstance(inputs, tuple):
        inputs = list(inputs)
    if isinstance(outputs, tuple):
        outputs = list(outputs)
    if custom_name is None:
        identifier = make_crit_script_identifier(function)
    else:
        identifier = sanitize_identifier(custom_name)
    if node_type is NodeType.Macro:
        if exec_inputs is None:
            exec_inputs = list("exec-in")
        if exec_outputs is None:
            exec_outputs = list("exec-out")
        ALL_FUNCTIONS[identifier] = NodePrototype(function, node_type, inputs, outputs, exec_inputs, exec_outputs, category=category)
    else:
        ALL_FUNCTIONS[identifier] = NodePrototype(function, node_type, inputs, outputs, category=category)

## CritScript Decorators

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
        custom_name: str | None = None,        ## TODO allow custom names!!!!!
        # end of un-normalized user inputs
        just_in_time_node:bool = False,
        category:str|None = None
    ):
    """Function decorator for any CritScript function that isn't a macro.
    TODO document the return types and parameters here with examples!"""
    ## Normalize inputs to be iterable
    inputs = make_iterable(inputs)
    outputs = make_iterable(outputs)
    aliases = [sanitize_identifier(alias) for alias in make_iterable(aliases)]
    if custom_name:
        custom_name = sanitize_identifier(custom_name)
    # TODO test!
    # ## Convert string shorthands to proper PinPrototypes
    # if len(inputs) > 0 and isinstance(inputs[0], str):
    #     inputs:Iterable[PinPrototype] = [Pin(in_pin) for in_pin in inputs]
    # if len(outputs) > 0 and isinstance(outputs[0], str):
    #     outputs:Iterable[PinPrototype] = [Pin(out_pin) for out_pin in outputs]
    ## TODO use aliases!

    def decorator(function):
        def wrapper(*sub_args, **sub_kwargs):
            return function(*sub_args, **sub_kwargs)
        wrapper.__name__ = function.__name__                        # Ensures decorated functions keep their names.
        wrapper.__qualname__ = function.__qualname__
        node_type = NodeType.JustInTime if just_in_time_node else NodeType.Standard
        _add_to_crit_script(wrapper, inputs, outputs, node_type, category=category, custom_name=custom_name)    # submits this function to CritScript
        return wrapper
    return decorator

def normalize_pin_prototype(given, as_value_pin:bool):
    if isinstance(given, PinPrototype):
        return given
    if isinstance(given, string):
        if as_value_pin:
            return PinPrototype(Any, given)
        else:
            return PinPrototype(None, given)

# TODO enable scalable parameter counts
def crit_script_macro(
        # un-normalized user inputs
        inputs: Iterable[PinPrototype] | PinPrototype |
                Iterable[str] | str |
                None=None,
        outputs: Iterable[PinPrototype] | PinPrototype |
                 Iterable[str] | str |
                 None=None,
        exec_inputs:  Iterable[PinPrototype] | PinPrototype |
                      Iterable[str] | str |
                      None=None,
        exec_outputs: Iterable[PinPrototype] | PinPrototype |
                      Iterable[str] | str |
                      None=None,
        aliases:      Iterable[str] | str | None = None,
        custom_name:  str | None = None,
        # end of un-normalized user inputs
        category: str | None = None,
    ):
    """Function decorator for any CritScript function that will become a macro.
    TODO document the return types and parameters here with examples!"""

    ## Normalize inputs to be iterable
    inputs = make_iterable(inputs)
    outputs = make_iterable(outputs)
    exec_inputs = make_iterable(exec_inputs)
    exec_outputs = make_iterable(exec_outputs)
    inputs = [normalize_pin_prototype(p, as_value_pin=True) for p in inputs]
    outputs = [normalize_pin_prototype(p, as_value_pin=True) for p in outputs]
    exec_inputs = [normalize_pin_prototype(p, as_value_pin=False) for p in exec_inputs]
    exec_outputs = [normalize_pin_prototype(p, as_value_pin=False) for p in exec_outputs]

    aliases = [sanitize_identifier(alias) for alias in make_iterable(aliases)]
    if custom_name:
        custom_name = sanitize_identifier(custom_name)

    # TODO test!
    # ## Convert string shorthands to proper PinPrototypes
    # # TODO this relies on the given iterable ALSO implementing __len__()... include a fallback or Iterable-specific way of ensuring there's an element in there?
    # if len(inputs) > 0 and isinstance(inputs[0], str):
    #     inputs:Iterable[PinPrototype] = [Pin(in_pin, Any) for in_pin in inputs]
    # if len(outputs) > 0 and isinstance(outputs[0], str):
    #     outputs:Iterable[PinPrototype] = [Pin(out_pin, Any) for out_pin in outputs]

    ## TODO use aliases!

    def decorator(function):
        def wrapper(*sub_args, **sub_kwargs):
            return function(*sub_args, **sub_kwargs)
        wrapper.__name__ = function.__name__  # Ensures decorated functions keep their names.
        wrapper.__qualname__ = function.__qualname__
        _add_to_crit_script(wrapper, inputs, outputs, NodeType.Macro, exec_inputs, exec_outputs, category=category, custom_name=custom_name) # submits this function to CritScript
        return wrapper
    return decorator

def wake_up(
    target_function:Callable
):
    """Is called on new nodes whenever they are created."""
    def decorator(wrapped_function):
        def wrapper(node:Node):     # TODO this should probably be node_context instead for ease of teaching?
            return wrapped_function(node)
        wrapper.__name__ = wrapped_function.__name__  # Ensures decorated functions keep their names.
        wrapper.__qualname__ = wrapped_function.__qualname__
        ## adds this wake-up routine to ``ALL_WAKE_UP_FUNCTIONS``.
        ALL_WAKE_UP_FUNCTIONS[make_crit_script_identifier(target_function)] = wrapper
        return wrapper
    return decorator


## Decorator parameter shorthand

def Pin(name: str = "unnamed", type: type | None = Any, split_format:str|None = None) -> PinPrototype:
    """Shorthand for prototyping a ValuePin of a given type and name. For use in ``@crit_script`` and
    ``@crit_script_macro`` parameters.

    * Note: You may also opt to give a string instead, if the conducted type may be ``Any``."""
    ## TODO update to explain split_format!
    return PinPrototype(type, name, split_format)

def Exec(name: str = "exec-unnamed", split_format:str|None = None) -> PinPrototype:
    ## TODO update this to return a PinPrototype!
    """Shorthand for prototyping an ExecutionPin of a given name. For use in ``@crit_script_macro`` parameters."""
    ## TODO update to explain split_format!
    return PinPrototype(None, name, split_format)


