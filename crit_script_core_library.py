from crit_script import InvalidCritScriptFunctionException, add_to_crit_script, CRIT_SCRIPT_FUNCTIONS


def crit_script(function, *args, **kwargs):
    """Function decorator for any CritScript function."""
    def crit_script_wrapper_fn(*sub_args, **sub_kwargs):
        return_values = function(*sub_args, **sub_kwargs)
        if not isinstance(return_values, list|tuple):
            raise InvalidCritScriptFunctionException(function) ## TODO is this necessary?
        return return_values
    crit_script_wrapper_fn.__name__ = function.__name__         # this is hilarious.
    crit_script_wrapper_fn.__qualname__ = function.__qualname__
    add_to_crit_script(crit_script_wrapper_fn, *args, **kwargs)
    return crit_script_wrapper_fn

@crit_script
def reroute_execution() -> tuple:
    return tuple()

reroute_execution()
print(CRIT_SCRIPT_FUNCTIONS)