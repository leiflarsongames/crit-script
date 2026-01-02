from crit_script import *



@crit_script(
    outputs=(
        Pin(str, "value-out-0"),
        Pin(str, "value-out-1"),
        Pin(str, "value-out-2"),
    ))
def get_test_values():
    return "One", "Two", "Three"


@crit_script(inputs=(Pin(str, "value-in-0")))
def debug_print(*inputs:str):
    print(*inputs)

def main():

    start_pin = ExecutionPin("program-start", out=True)
    node_0 = make_node("get-test-values")
    node_1 = make_node("debug-print")

    print(f"connect on-program-start : {start_pin.try_connect(node_0.exec_in_pins[0])}")
    print(f"      connect value line : {node_0.out_pins[0].try_connect(node_1.in_pins[0])}")

    print(f"exec_out_pins[0] = {"out" if node_0.exec_out_pins[0].out else "in"}")
    print(f"     exec_in_pin = {"out" if node_1.exec_in_pins[0].out else "in"}")

    print(f"  connect execution line : {node_0.exec_out_pins[0].try_connect(node_1.exec_in_pins[0])}")

    print("Running...")
    run(start_pin)

print(f"keys = {', '.join(CRIT_SCRIPT_FUNCTIONS.keys())}")
main()