from time import sleep
from crit_script import *
from crit_script_core import *
from crit_script_make import *
from crit_script_random import *
from crit_script_math import *

def get_node_io(*args) -> str:
    ## TODO make these look more like the "prototype.txt" document!
    '''returns the name, type, and details of the input and output pins of this node, in a human-readable format.'''
    DOCUMENTATION_TITLE_COLUMN_WIDTH  = 24
    DOCUMENTATION_FIRST_COLUMN_WIDTH  = 10
    DOCUMENTATION_SECOND_COLUMN_WIDTH = 14

    try:
        node_name:str = sanitize_identifier(*args[0])
    except KeyError:
        return f"Please enter the name of a node to look up!"
    node_prototype = None
    try:
        node_prototype = ALL_FUNCTIONS[node_name]
    except KeyError:
        return f"Cannot find node named \"{node_name}\"."

    if node_prototype.function.__doc__:
        print(node_prototype.function.__doc__)
    else:
        print("No accompanying docstring found.")

    accumulator:str = node_name
    accumulator += (' ' * (DOCUMENTATION_TITLE_COLUMN_WIDTH-len(accumulator)) +
                    ': ' + str(node_prototype.node_type) + '\n')

    ## EXECUTION PINS
    for idx, pin in enumerate(make_iterable(node_prototype.exec_inputs)):
        pin:PinPrototype
        line: str = ''
        if idx == 0:
            line += 'exec-ins'
        line += (' ' * (DOCUMENTATION_FIRST_COLUMN_WIDTH - len(line)) +
                 pin.name + ' ' * (DOCUMENTATION_SECOND_COLUMN_WIDTH - len(pin.name)) +
                 ': ' + str(pin.conducted_type) + '\n')
        accumulator += line
    for idx, pin in enumerate(make_iterable(node_prototype.exec_outputs)):
        pin: PinPrototype
        line: str = ''
        if idx == 0:
            line += 'exec-outs'
        line += (' ' * (DOCUMENTATION_FIRST_COLUMN_WIDTH - len(line)) +
                 pin.name + ' ' * (DOCUMENTATION_SECOND_COLUMN_WIDTH - len(pin.name)) +
                 ': ' + str(pin.conducted_type) + '\n')
        accumulator += line

    ## DATA PINS
    for idx, pin in enumerate(make_iterable(node_prototype.inputs)):
        pin: PinPrototype
        line:str = ''
        if idx == 0:
            line += 'inputs'
        line += (' ' * (DOCUMENTATION_FIRST_COLUMN_WIDTH - len(line)) +
                 pin.name + ' ' * (DOCUMENTATION_SECOND_COLUMN_WIDTH - len(pin.name)) +
                 ': ' + str(pin.conducted_type) + '\n')
        accumulator += line
    for idx, pin in enumerate(make_iterable(node_prototype.outputs)):
        pin: PinPrototype
        line:str = ''
        if idx == 0:
            line += 'outputs'
        line += (' ' * (DOCUMENTATION_FIRST_COLUMN_WIDTH - len(line)) +
                 pin.name + ' ' * (DOCUMENTATION_SECOND_COLUMN_WIDTH - len(pin.name)) +
                 ': ' + str(pin.conducted_type) + '\n')
        accumulator += line
    return accumulator

def commands_list() -> str:
    return ("# GENERAL COMMANDS\n"
            "commands               : shows this menu again\n"
            "nodes                  : lists all named nodes available to this crit-script instance\n"
            "show <node-name>       : shows the list of all inputs and outputs on a node\n"
            "quit                   : exits the program\n"
            "\n"
            "NOTE: graph editing from the command line is currently unimplemented.\n"
            # "graph open <path>      : (not implemented) enters graph mode on an existing graph\n"
            # "graph new <path>       : (not implemented) enters graph mode on a new graph\n"
            # "graph leave            : (not implemented) exits graph mode\n"
            # "\n"
            # "# GRAPH MODE ONLY COMMANDS   (NOTE: Graph mode is NOT implemented!)\n"
            # "spawn <node-name>                    : spawns a node, assigning it an idx\n"
            # "delete <node-idx>                    : deletes the node with the given idx\n"
            # "breakpoint <node-idx>                : sets a trap for when the current node executes\n"
            # "continue                             : continues from the current breakpoint\n"
            # "link data <node-idx-0> <pin-idx-0>\n"
            # "          <node-idx-1> <pin-idx-1>   : connects node-0's given data out-pin to node-1's given data in-pin\n"
            # "link exec <node-idx-0> <pin-idx-0>\n"
            # "          <node-idx-1> <pin-idx-1>   : connects node-0's given execution out-pin to node-1's given execution in-pin\n"
            # "break data in  <node-idx> <pin-idx>  : breaks the connection attached to this pin, if it exists.\n"
            # "break data out \"          \"          : \"\n"
            # "break exec in  \"          \"          : \"\n"
            # "break exec out \"          \"          : \"\n"
            # "break "
            # "write <node-idx> <pin-idx> <value>   : writes a value to the node's given data in-pin\n"
            # "read  <node-idx> <pin-idx>           : reads the value of the node's given data out-pin\n"
            # "exec  <node-idx> <pin-idx>           : executes from the node's given execution in-pin\n"
            # "\n"
            # "Note: pin indices always default to `0` if not specified\n."
            )

def quit():
    global running
    running = False

ALL_COMMANDS:dict[str, Callable] = {
    'nodes':    lambda *args : print("\n".join([e for e in ALL_FUNCTIONS])),
    'commands': lambda *args : print(commands_list()),
    'show':     lambda *args : print(get_node_io(args)),
    'quit':     lambda *args : quit(),
    'graph':    lambda *args : print("Not implemented!"),
    'write':    lambda *args : print("Not implemented!"),
    'read':     lambda *args : print("Not implemented!"),
}

def parse_command(tokens):
    global ALL_COMMANDS
    command_name = tokens[0]
    command_args = tokens[1:]

    if command_name in ALL_COMMANDS:
        out = ALL_COMMANDS[command_name](*command_args)
        if out:
            print(out)
    else:
        print(f"Unknown command `{command_name}`. Enter `commands` to see all available commands.")



print("type `commands` for a list of all available commands.")
running = True
while(running):
    cmd = input()
    parse_command(cmd.split(' '))
print("Thank you for trying Crit-Script!")
sleep(2)
