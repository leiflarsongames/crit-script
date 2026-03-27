from crit_script import crit_script, delete_from_crit_script, Pin

# NOTE items are not sanitized. Items will raise KeyError or ValueError.

all_global_variables:dict[str, Any] = dict()
"""User-created global variables, accessible within CritScript"""

GLOBAL_VARIABLES_CATEGORY = "Global Variables"

def create_global_variable(unique_identifier:str) -> None:
    """Raises ValueError when TODO"""
    if unique_identifier in all_global_variables:
        raise ValueError(f"Global variable with unique identifier = \"{unique_identifier}\" already exists!")
    all_global_variables[unique_identifier] = None
    # add the global variable and it's various functions
    ## TODO DOUBLE CHECK THAT THE FUNCTIONS DO NOT ALREADY EXIST IN CRITSCRIPT!
    # create getter
    @crit_script(
        inputs = None,
        outputs = Pin("out"),
        category = GLOBAL_VARIABLES_CATEGORY,
        custom_name = f"get-{unique_identifier}"
    )
    def get_global_variable() -> Any:
        return get_global_variable(unique_identifier)
    # create setter
    @crit_script(
        inputs=Pin("new-value"),
        outputs=None,
        category=GLOBAL_VARIABLES_CATEGORY,
        custom_name=f"set-{unique_identifier}"
    )
    def set_global_variable() -> Any:
        return set_global_variable(unique_identifier)

def delete_global_variable(unique_identifier:str) -> None:
    """Raises KeyError when TODO"""
    if unique_identifier not in all_global_variables:
        raise KeyError("delete_global_variable() failed... tried to delete global variable with unique identifier = \"{unique_identifier}\" but it didn't exist to begin with!")
    del all_global_variables[unique_identifier]
    # remove the global variables' functions
    delete_from_crit_script(f"get-{unique_identifier}")
    delete_from_crit_script(f"set-{unique_identifier}")

def _set_global_variable(unique_identifier:str, value:Any) -> None:
    """Raises KeyError when TODO"""
    if unique_identifier not in all_global_variables:
        raise KeyError("set_global_variable() failed... tried to set global variable with unique identifier = \"{unique_identifier}\" but it doesn't exist!")
    all_global_variables[unique_identifier] = value


def _get_global_variable(unique_identifier:str) -> Any:
    """Raises KeyError when TODO"""
    if unique_identifier not in all_global_variables:
        raise KeyError("get_global_variable() failed... tried to set global variable with unique identifier = \"{unique_identifier}\" but it doesn't exist!")
    return all_global_variables[unique_identifier]
