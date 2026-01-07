from itertools import product
from random import randint, random
from typing import Any
from crit_script import crit_script, Pin, Exec, crit_script_macro, NodeContext

@crit_script(inputs=(Pin(str, "message")))
def debug_print(ctx, *inputs: str):
    """Prints a ``message`` to the underlying Python console."""
    print('\n'.join(*inputs))

@crit_script()
def reroute_execution(ctx) -> None:
    """Does nothing. Used for redirecting an execution line."""
    pass

@crit_script(inputs="value-in",
             outputs="value-out",
             just_in_time_node=True)
def reroute_value(ctx, value_in) -> Any:
    """Does nothing. Used for redirecting a value line."""
    return value_in

@crit_script(
    inputs=(Pin(float, "value-in-0"),
            Pin(float, "value-in-1"),
            Pin(float, "value-in-2")),
    outputs=(Pin(float, "value-out-0"),
             Pin(float, "value-out-1"),
             Pin(float, "value-out-2"))
)
def sort_ascending(ctx, *args: Any) -> list:
    """Outputs each input in order with the lowest at the top, and the highest at the bottom."""
    rv = list(*args)
    rv.sort()
    return rv

@crit_script(
    inputs=(Pin(int, "die-type")),
    outputs=(Pin(float, "result"))
)
def roll_die(ctx, die_type: int) -> int:
    """Rolls a ``die-type``-sided die."""
    return randint(1, die_type)

@crit_script(outputs=(Pin(float, "result")))
def roll_percent(ctx) -> float:
    """Returns a random number from 0 to 1, not including 1.

    That is, ``result`` will be a random number on the interval [0,1)."""
    return random()

@crit_script(inputs=(Pin(list[str], "keys"),
                     Pin(list[Any], "values")),
             outputs=Pin(dict[str, Any], "keyword-parameters"),
             aliases="make-dictionary")
def make_keyword_parameters(ctx, keys:list[str], values:list[Any]) -> dict[str, Any]:
    kwd_params = dict()
    for i in range(0, len(keys)):
        kwd_params[keys[i]] = values[i]
    return kwd_params


    # to all you purists listen I too hate parallel arrays but I'm NOT gonna be pushing that on people who don't do
    # CS. There's a reason parallel arrays are the second thing people do with arrays in school, because it's dead
    # simple. I'm enabling it because people are going to think to do it that way, and I don't need them worrying about
    # the "right" way to do something that should obviously work fine.

@crit_script(
    inputs=Pin(str, "dice-algebra-expression"),
    outputs=Pin(int, "result")
)
def roll_dice_expression(ctx, dice_algebra_expression: str):
    """TODO test this!"""
    from dice_algebra_expression import Expression
    return Expression(dice_algebra_expression).evaluate()

# TODO implement list handling for that crap!
@crit_script(
    inputs=((Pin(str, "dice-algebra-expression"),
             Pin(list[str], "parameter-names"),
             Pin(list[int], "parameter-values"),
             )),
    outputs=(Pin(int, "result"))
)
def roll_dice_parameterized_expression(
    ctx,
    dice_algebra_expression: str,
    parameters: dict[str, int],
):
    """TODO test this!"""
    from dice_algebra_expression import Expression

    ## construct parameters dictionary for the expression
    return Expression(dice_algebra_expression, parameters).evaluate()

@crit_script_macro(
    inputs=(Pin(float, "a"),
            Pin(float, "b"),),
    outputs=None,
    exec_inputs=Exec("exec-in"),
    exec_outputs=(Exec("a<b"),
                  Exec("a=b"),
                  Exec("a>b"))
)

def switch_compare(ctx:NodeContext, a, b) -> None:
    if a < b:
        ctx.exec_out_index = 0
    elif a == b:
        ctx.exec_out_index = 1
    else:
        ctx.exec_out_index = 2


@crit_script(
    inputs=(Pin(int, "dividend"),
            Pin(int, "divisor")),
    outputs=Pin(int, "modulo"),
    aliases="modulo",
    just_in_time_node=True
)
def remainder(ctx, a, b) -> int:
    """Returns the remainder of ``dividend``
    divided by ``divisor``. Also known as
    the "modulo" operator."""
    return a % b

@crit_script(
    inputs=("addend-0", "addend-1"),
    outputs="sum",
    just_in_time_node=True
)
def add(a, b) -> float:
    return a + b
