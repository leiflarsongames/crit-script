from crit_script import *

# @crit_script
def get_test_values():
    return "One", "Two", "Three"

# @crit_script
def debug_print(inputs:tuple[str]):
    print(inputs)

def setup():
    add_to_crit_script(
        get_test_values,
        inputs=None,
        outputs=(
            Pin(type=str, name="value-out-0"),
            Pin(type=str, name="value-out-1"),
            Pin(type=str, name="value-out-2"),
        )
    )
    add_to_crit_script(
        debug_print,
        inputs=(
            Pin(type=str, name="value-in-0"),
        )
    )

def main():

    start_pin = ExecutionPin("on-program-start")
    start_pin.out = True
    node_0 = make_node("get-test-values")
    node_1 = make_node("debug-print")

    print(f"connect on-program-start : {start_pin.try_connect(node_0.exec_in_pin)}")
    print(f"      connect value line : {node_0.out_pins[0].try_connect(node_1.in_pins[0])}")

    print(f"exec_out_pins[0] = {node_0.exec_out_pins[0].out}")
    print(f"     exec_in_pin = {node_1.exec_in_pin.out}")

    print(f"  connect execution line : {node_0.exec_out_pins[0].try_connect(node_1.exec_in_pin)}")

    print("Running...")
    run(start_pin)

setup()
print(f"keys = {', '.join(CRIT_SCRIPT_FUNCTIONS.keys())}")
main()