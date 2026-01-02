from typing import Any

from crit_script import crit_script, Pin, Exec


@crit_script()
def reroute_execution() -> tuple:
    return tuple()

@crit_script(
    inputs=(Pin(float, "value-in-0"),
            Pin(float, "value-in-1"),
            Pin(float, "value-in-2"),
            ),
    outputs=(Pin(float, "value-out-0"),
             Pin(float, "value-out-1"),
             Pin(float, "value-out-2"),
             ),
    just_in_time_node=False,
)
def sort_ascending(*args: Any) -> list(Any):
    list(*args)