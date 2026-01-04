from random import randint, random
from typing import Any
from crit_script import crit_script, Pin, Exec, crit_script_macro, CritScriptNode, CritScriptNodeContext

# TODO string manipulations
# TODO math
# TODO save/load JSON
# TODO accept events from Python
#
# TODO make node_ctx optional?

# square-root ("sqrt")
# nth-root ("radical")

@crit_script(inputs=(Pin(str, "message")))
def debug_print(node_ctx:CritScriptNodeContext, *inputs: str):
    """Prints a ``message`` to the underlying Python console."""
    print(*inputs)


@crit_script()
def reroute_execution(node_ctx:CritScriptNodeContext):
    """Does nothing. Used for redirecting an execution line."""
    pass


@crit_script(
    inputs=(Pin(float, "value-in-0"),
            Pin(float, "value-in-1"),
            Pin(float, "value-in-2")),
    outputs=(Pin(float, "value-out-0"),
             Pin(float, "value-out-1"),
             Pin(float, "value-out-2"))
)
def sort_ascending(node_ctx:CritScriptNodeContext, *args: Any) -> list:
    """Outputs each input in order with the lowest at the top, and the highest at the bottom."""
    rv = list(*args)
    rv.sort()
    return rv


@crit_script(
    inputs=(Pin(int, "die-type")),
    outputs=(Pin(float, "result"))
)
def roll_die(node_ctx:CritScriptNodeContext, die_type: int) -> int:
    """Rolls a ``die-type``-sided die."""
    return randint(1, die_type)


@crit_script(outputs=(Pin(float, "result")))
def roll_percent(node_ctx:CritScriptNodeContext) -> float:
    """Returns a random number from 0 to 1, not including 1.

    That is, ``result`` will be a random number on the interval [0,1)."""
    return random()


@crit_script(
    inputs=((Pin(str, "dice-algebra-expression"),
             Pin(int, "A"),
             Pin(int, "B"),
             Pin(int, "C"),
             Pin(int, "D"),
             Pin(int, "E"),)),
    outputs=(Pin(int, "result"))
)
def roll_dice_parameterized_expression(
        node_ctx:CritScriptNodeContext,
        dice_algebra_expression: str,
        *params: int):
    """TODO test this!"""
    from dice_algebra_expression import Expression
    return Expression(dice_algebra_expression,
                      {
                          'A': params[0],
                          'B': params[1],
                          'C': params[2],
                          'D': params[3],
                          'E': params[4],
                      }
                      ).evaluate()


@crit_script(
    inputs=Pin(str, "dice-algebra-expression"),
    outputs=Pin(int, "result")
)
def roll_dice_expression(node_ctx:CritScriptNodeContext, dice_algebra_expression: str):
    """TODO test this!"""
    from dice_algebra_expression import Expression
    return Expression(dice_algebra_expression).evaluate()


@crit_script_macro(
    inputs=(Pin(float, "a"),
            Pin(float, "b"),),
    outputs=None,
    exec_inputs=Exec("exec-in"),
    exec_outputs=(Exec("a<b"),
                  Exec("a=b"),
                  Exec("a>b"))
)
def switch_compare(node_ctx:CritScriptNodeContext, a, b) -> None:
    if a < b:
        node_ctx.exec_out_index = 0
    elif a == b:
        node_ctx.exec_out_index = 1
    else:
        node_ctx.exec_out_index = 2

@crit_script_macro(
    inputs=None,
    outputs=Pin(int, "current-count"),
    exec_inputs=(Exec("exec-in"),
                 Exec("reset"),
                 Exec("add-one")),
    exec_outputs=(Exec("exec-out"),
                  Exec("reset-out"),
                  Exec("added-one"),),
    uses_own_node=True,
)
def count_and_reset(node_ctx:CritScriptNodeContext) -> int:
    if node_ctx.memory is None:
        node_ctx.memory = 0
    match node_ctx.exec_in_index:
        case 0:
            pass
        case 1:
            node_ctx.memory = 0
        case 2:
            node_ctx.memory += 1
    node_ctx.exec_out_index = node_ctx.exec_in_index
    return node_ctx.memory
