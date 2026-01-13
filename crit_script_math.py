from decimal import Decimal
from itertools import product
from typing import Any

from crit_script import crit_script, Pin, NodeContext, make_iterable, CritScriptValueException


## ARITHMETIC FUNCTIONS
# Note: some of these names are NOT valid verbs as is usual for CritScript basic library functions. This is fine.

# arithmetic
@crit_script(
    inputs=Pin("addends", split_format="addend"),
    outputs=Pin("sum"),
    just_in_time_node=True,
    aliases=("sum", "+", "plus")
)
def add(ctx: NodeContext, addends:Any) -> Any:
    addends = make_iterable(addends)
    return sum(addends)

@crit_script(
    inputs=(Pin("minuend"),
            Pin("subtrahend")),
    outputs=(Pin("difference")),
    just_in_time_node=True,
    aliases=("-", "minus")
)
def subtract(ctx: NodeContext, minuend:Any, subtrahend:Any) -> Any:
    return minuend - subtrahend

@crit_script(
    inputs=Pin("multiplicands", split_format="multiplicand"),
    outputs=Pin("product"),
    just_in_time_node=True,
    aliases=("times", "product", "*"),
)
def multiply(ctx:NodeContext, multiplicands:Any) -> Any:
    multiplicands = make_iterable(multiplicands)
    return product(multiplicands)

@crit_script(
    inputs=(Pin("dividend"),
            Pin("divisor"),),    # TODO we need better typing on this!
                                # We can admit *anything* that can be CONVERTED INTO a Decimal!
    outputs=Pin("quotient"),
    just_in_time_node=True,
    aliases=("decimal-division", "/", "slash")
)
def divide_as_decimal(ctx:NodeContext, dividend:Any, divisor:Any) -> Any:
    return dividend / divisor

@crit_script(
    inputs=(Pin("dividend"),
            Pin("divisor")),
    outputs=(Pin("quotient"), Pin("remainder")),
    just_in_time_node=True,
    aliases=("integer-division", "divide-as-integer", "modulo", "%")
)
def divide_with_remainder(ctx:NodeContext, dividend:Any, divisor:Any) -> Any:
    return (
        dividend // divisor,    # quotient
        dividend % divisor,     # remainder
    )

## clamps

@crit_script(
    inputs=(Pin("value-in"),
            Pin("upper-bound"),
            Pin("lower-bound"),),
    outputs=Pin("value-out"),
    just_in_time_node=True,
    aliases=("clamp-within", "within")
)
def clamp(ctx:NodeContext, value:Any, lower_bound:Any, upper_bound:Any) -> Any:
    return min(upper_bound, max(value, lower_bound))

@crit_script(
    inputs=(Pin("value-in"),
            Pin("upper-bound"),),
    outputs=Pin("value-out"),
    just_in_time_node=True,
    aliases=("at-most", "clamp-to-minimum")
)
# TODO verb makes little sense!
def clamp_at_most(ctx:NodeContext, value:Any, upper_bound:Any) -> Any:
    return min(upper_bound, value)

@crit_script(
    inputs=(Pin("value-in"),
            Pin("lower-bound"),),
    outputs=Pin("value-out"),
    just_in_time_node=True,
    aliases=("at-least", "clamp-to-maximum")
)
# TODO verb makes little sense!
def clamp_at_least(ctx:NodeContext, value:Any, lower_bound:Any) -> Any:
    return max(lower_bound, value)


# minimum, maximum

@crit_script(
    inputs=Pin("values-in", split_format="value-in"),
    outputs=Pin("smallest-value"),
    just_in_time_node=True,
    aliases=("minimum", "smallest", "find-minimum")
)
def find_smallest(ctx:NodeContext, values:Any) -> Any:
    values = make_iterable(values)
    return min(values)

@crit_script(
    inputs=Pin("values-in", split_format="value-in"),
    outputs=Pin("largest-value"),
    just_in_time_node=True,
    aliases=("maximum", "largest", "find-maximum")
)
def find_largest(ctx:NodeContext, values:Any) -> Any:
    values = make_iterable(values)
    return max(values)

# comparisons returning boolean

@crit_script(
    inputs=(Pin("a"), Pin("b")),
    outputs=Pin("a>b", bool),
    just_in_time_node=True,
    aliases=(">",),
)
def greater_than(ctx:NodeContext, a:Any, b:Any) -> bool:
    return a > b

@crit_script(
    inputs=(Pin("a"), Pin("b")),
    outputs=Pin("a<b", bool),
    just_in_time_node=True,
    aliases=("<",),
)
def less_than(ctx:NodeContext, a:Any, b:Any) -> bool:
    return a < b

@crit_script(
    inputs=(Pin("a"), Pin("b")),
    outputs=Pin("a≥b", bool),
    just_in_time_node=True,
    aliases=("greater-equals",
             ">=", "=>",),
)
def greater_than_or_equal_to(ctx:NodeContext, a:Any, b:Any) -> bool:
    return a >= b

@crit_script(
    inputs=(Pin("a"), Pin("b")),
    outputs=Pin("a≤b", bool),
    just_in_time_node=True,
    aliases=("less-equals",
             "<=", "=<",),
)
def less_than_or_equal_to(ctx:NodeContext, a:Any, b:Any) -> bool:
    return a <= b

@crit_script(
    inputs=(Pin("a"), Pin("b")),
    outputs=Pin("a=b", bool),
    just_in_time_node=True,
    aliases=("equal-to", "==")
)
def equals(ctx:NodeContext, a:Any, b:Any) -> bool:
    return a == b

@crit_script(
    inputs=(Pin("a"), Pin("b")),
    outputs=Pin("a≠b", bool),
    just_in_time_node=True,
    aliases=("is-not-equal-to",
             "not-equal-to",
             "not-equals-to",
             "neq",
             "!=", "=/=",
             )
)
def not_equals(ctx:NodeContext, a:Any, b:Any) -> bool:
    return a != b

# boolean operations

@crit_script(
    inputs=Pin("value-in", bool),
    outputs=Pin("value-out", bool),
    just_in_time_node=True,
    aliases=("not", "invert"),
)
def boolean_not(ctx:NodeContext, value:Any) -> bool:
    return not value

@crit_script(
    inputs=Pin("values-in", split_format="value-in"),
    outputs=Pin("value-out", split_format="value-out"),
    just_in_time_node=True,
    aliases=("or", "any"),
)
def boolean_or(ctx:NodeContext, values:Any) -> bool:
    values = make_iterable(values)
    return any(values)

@crit_script(
    inputs=Pin("values-in", split_format="value-in"),
    outputs=Pin("value-out", split_format="value-out"),
    just_in_time_node=True,
    aliases=("and", "all"),
)
def boolean_and(ctx:NodeContext, values:Any) -> bool:
    values = make_iterable(values)
    return all(values)

@crit_script(
    inputs=Pin("values-in", split_format="value-in"),
    outputs=Pin("value-out", split_format="value-out"),
    just_in_time_node=True,
    aliases=("xor-only-one", "boolean-xor-only-one"),
)
def boolean_only_one(ctx:NodeContext, values:Any) -> bool:
    """Returns True when only one input is True"""
    values = make_iterable(values)
    accum = sum([1 if v else 0 for v in values])
    return accum == 1

@crit_script(
    inputs=Pin("values-in", split_format="value-in"),
    outputs=Pin("value-out", split_format="value-out"),
    just_in_time_node=True,
    aliases=("xor",),
)
def boolean_xor(ctx:NodeContext, values:Any) -> bool:
    """Returns True when an odd number of inputs is True."""
    values = make_iterable(values)
    accum = sum([1 if v else 0 for v in values])
    return accum % 2 == 1

