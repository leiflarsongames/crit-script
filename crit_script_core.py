from random import randint, random
from typing import Any, Iterable
from crit_script import crit_script, Pin, Exec, crit_script_macro, NodeContext, wake_up, run_graph, Node, \
    CritScriptStopGraph

## DEBUG STUFF, USES THE CONSOLE
@crit_script(inputs=Pin('message'))
def debug_wait_or_quit(ctx, msg) -> None:
    """Debug only. Pauses until user enters something. Kills the graph if """
    given = input(f"{msg} -> ")
    if len(given) > 0 and given[0].lower() == 'q':
        raise CritScriptStopGraph(f"Graph ended by debug user after message {msg}")

@crit_script(inputs=(Pin('message', str)))
def debug_print(ctx, *inputs: str):
    """Prints a ``message`` to the underlying Python console."""
    print('\n'.join(*inputs))

## REROUTES AND VALUE/EXECUTION FLOW
@crit_script()
def reroute_execution(ctx) -> None:
    """Does nothing. Used for redirecting an execution line."""
    pass

@crit_script(inputs=Pin('value-in'),
             outputs=Pin('value-out'),
             just_in_time_node=True)
def reroute_value(ctx, value_in) -> Any:
    """Does nothing. Used for redirecting a value line."""
    return value_in

@crit_script(
    inputs=(Pin('value-in-0', float),
            Pin('value-in-1', float),
            Pin('value-in-2', float)),
    outputs=(Pin('value-out-0', float),
             Pin('value-out-1', float),
             Pin('value-out-2', float))
)
def sort_ascending(ctx, *args: Any) -> list:
    """Outputs each input in order with the lowest at the top, and the highest at the bottom."""
    rv = list(*args)
    rv.sort()
    return rv


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

@crit_script(inputs=(Pin('keys', list[str]),
                     Pin('values', list[Any])),
             outputs=Pin('keyword-parameters', dict[str, Any]),
             aliases='make-dictionary')
def make_keyword_parameters(ctx, keys:list[str], values:list[Any]) -> dict[str, Any]:
    kwd_params = dict()
    for i in range(0, len(keys)):
        kwd_params[keys[i]] = values[i]
    return kwd_params

    # To all you purists: Listen. I, too, hate parallel arrays, but I'm NOT gonna be pushing that on people who don't
    # usually do CS. There's a reason parallel arrays are the second thing people do with arrays in school, because
    # it's dead simple. I'm enabling it because people are going to think to do it that way, and I don't need them
    # worrying about the 'right' way to do something that should obviously work fine.

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

@crit_script_macro(
    inputs=(Pin('a', Any),
            Pin('b', Any),),
    outputs=None,
    exec_inputs=Exec('exec-in'),
    exec_outputs=(Exec('a<b'),
                  Exec('a=b'),
                  Exec('a>b')),
    aliases=('switch-compare', 'compare'),
)
def switch_by_comparison(ctx:NodeContext, a, b) -> None:
    if a < b:
        ctx.exec_out_index = 0
    elif a == b:
        ctx.exec_out_index = 1
    else:
        ctx.exec_out_index = 2

@crit_script(
    inputs=(Pin('dividend', int),
            Pin('divisor', int)),
    outputs=Pin('modulo', int),
    aliases='modulo',
    just_in_time_node=True
)
def remainder(ctx, a, b) -> int:
    """Returns the remainder of ``dividend``
    divided by ``divisor``. Also known as
    the 'modulo' operator."""
    return a % b

@crit_script(
    inputs=('addend-0', 'addend-1'),
    outputs='sum',
    just_in_time_node=True
)
def add(a, b) -> float:
    return a + b

@crit_script_macro(
    inputs=None,
    outputs=Pin('count', Any),
    exec_inputs=(Exec('add-one'),
                 Exec('reset')),
    exec_outputs=(Exec('after-added-one'),
                  Exec('after-reset')),
    aliases=('counter', 'increment-counter')
)
def count_and_reset(ctx:NodeContext) -> int:
    # activate node
    if ctx.memory is None:
        ctx.memory = 0
    # normal behavior
    match ctx.exec_in_index:
        case 0:
            ctx.memory += 1
        case 1:
            ctx.memory = 0
        case _:
            raise NotImplementedError('TODO')
    return ctx.memory

@wake_up(count_and_reset)
def wake_up_count_and_reset(node:Node) -> int:
    if node.memory is None:
        node.memory = 0
    if node.out_pins[0].read_value() is None:
        node.out_pins[0].write_value(node.memory)
    # print(f"woke up: ctx.memory = {node.memory}")
    # print(f"woke up: ctx.get_node().out_pins[0].read_value() = {node.get_node().out_pins[0].read_value()}")
    return node.memory

@crit_script_macro(
    inputs=None,
    outputs=None,
    exec_inputs=(Exec('start'),
                 Exec('stop')),
    exec_outputs=(Exec('repeat-here'),
                  Exec('done')),
    aliases='while-loop',)
def loop(ctx:NodeContext) -> None:
    """Repeatedly executes at [repeat-here] until [stop] is called. Then the graph continues at [done].

    * Note: This will run FOREVER unless you eventually call [done] from INSIDE of the loop! TODO include an example and counter-example here!"""
    if ctx.exec_in_index == 1:
        ctx.memory = False
        ctx.exec_out_index = None
        return
    else:
        ctx.memory = True

    while ctx.memory:
        run_graph(ctx.get_node().exec_out_pins[0])

    # proceed with normal execution
    ctx.exec_out_index = 1


@crit_script_macro(
    inputs=None,
    outputs=None,
    exec_inputs=(Exec('exec-in-0'),
                 Exec('exec-in-1')),
    exec_outputs=Exec('exec-out'),
)
def execution_joint(ctx:NodeContext) -> None:
    ctx.exec_out_index = 0
    return

# @crit_script_macro(
#     exec_inputs=(Exec('exec-in')))
# def throw_exception(ctx:NodeContext) -> None:
#     raise CritScriptUserException

# @crit_script_macro() # call for loops "repeat"
#
# @crit_script_macro() # call for each loops "repeat-for-each"
#
# @crit_script_macro(
#     inputs=Pin('list-in', Iterable[Any]),
#     outputs=(Pin('list-index', int),
#              Pin('list-element', Any),),
#     exec_inputs=(Exec('begin-looping'),
#                  Exec('break')),
#     exec_outputs=Exec('after-looping'),
#     aliases='for',
# )
# def for_loop(ctx:NodeContext, list_in:Iterable[any]) -> tuple[int, Any]:
#     # when loop is called to break
#     if ctx.exec_in_index == 1:
#
#     while True:     # loop until break
#         ctx.get_node().