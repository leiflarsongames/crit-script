from random import randint, random
from typing import Any, Iterable
from crit_script import crit_script, Pin, Exec, crit_script_macro, NodeContext, wake_up, run_graph, Node, \
    CritScriptStopGraph, make_iterable, make_mutable_iterable

@crit_script(
    inputs=(Pin('die-type', int)),
    outputs=(Pin('result', int))
)
def roll_die(ctx, die_type: int) -> int:
    """Rolls a ``die-type``-sided die."""
    return randint(1, die_type)

@crit_script(outputs=(Pin('result', float)))
def roll_percent(ctx) -> float:
    """Returns a random number from 0 to 1, not including 1.

    That is, ``result`` will be a random number on the interval [0,1)."""
    return random()


@crit_script(
    inputs=Pin('dice-algebra-expression', str),
    outputs=Pin('result', int)
)
def roll_dice_expression(ctx, dice_algebra_expression: str):
    """TODO test this!"""
    from dice_algebra_expression import Expression
    return Expression(dice_algebra_expression).evaluate()

# TODO implement list handling for that stuff!
@crit_script(
    inputs=((Pin('dice-algebra-expression', str),
             Pin('parameter-names', list[str]),
             Pin('parameter-values', list[int]),
             )),
    outputs=(Pin('result', int))
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