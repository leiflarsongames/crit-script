import unittest

from crit_script import crit_script, Pin, CritScriptNode, make_node, run_graph, ExecutionPin, ALL_FUNCTIONS
from crit_script_core import *

_DETERMINISTIC_VARIATION_COUNT = 15
"""The number of variations assessed for deterministic tests"""
_TRIAL_COUNT = 5000
"""The trial count for randomness-based tests"""
_ACCEPTABLE_DEVIATION_OF_MEAN = 0.02
"""The largest absolute deviation we will tolerate from the mean before failing a test, as a fraction of the expected mean."""

@crit_script(
    outputs=(Pin(int, "value-out-0"),
             Pin(int, "value-out-1"),
             Pin(int, "value-out-2"))
    )
def get_test_values():
    """TODO remove this!"""
    ## TODO implement Magic Numbers! (constants)
    return 4, 6, 8

@crit_script( inputs=(Pin(Any, "value-in")),
             outputs=(Pin(Any, "value-out")))
def test_buffer(value_in) -> Any:
    return value_in

class TestCoreLibrary(unittest.TestCase):

    def test_decorator_shorthand_exec(self):
        for variation in range(_DETERMINISTIC_VARIATION_COUNT):
            self.assertEqual(
                Exec(f"exec-in-{variation}"),
                f"exec-in-{variation}",
                "Commonly generated exec-in variations work with shorthand as expected"
            )
            self.assertEqual(
                Exec(f"exec-out-{variation}"),
                f"exec-out-{variation}",
                "Commonly generated exec-out variations work with shorthand as expected"
            )
        non_treacherous_sentence = "some-of-that-stuff-right-there-oh-goodness-that's-a-long-string!-do-you-suppose-anything-other-than-caps-is-forbidden?"
        self.assertEqual(
            Exec(non_treacherous_sentence),
            non_treacherous_sentence,
            "long but otherwise straightforward identifiers work fine."
        )

    def test_unused_node(self):
        numbers_node = make_node(get_test_values)
        for idx in range(3):
            self.assertEqual(numbers_node.read_all_out_pins()[idx], None, "Unevaluated nodes should have no output available!")

    def test_run_simple_graph(self):
        """Runs a small graph, and inspects the output on the other side."""
        start_pin = ExecutionPin("program-start", out=True)
        node_0 = make_node(get_test_values)
        output_node = make_node(test_buffer)
        self.assertTrue(start_pin.try_connect(node_0.exec_in_pins[0]), "connect on-program-start")
        self.assertTrue(node_0.out_pins[0].try_connect(output_node.in_pins[0]), "connect value line")
        ## check pin parity on last execution line
        self.assertTrue({node_0.exec_out_pins[0].out == True}, "node_0.exec_out_pins[0] is an out pin")
        self.assertTrue({output_node.exec_in_pins[0].out == False}, "node_last.exec_in_pins[0] is an in pin")
        ## connect last execution line
        self.assertTrue({node_0.exec_out_pins[0].try_connect(output_node.exec_in_pins[0])}, "connect execution line")
        try:
            ## run program
            run_graph(start_pin)
            self.assertEqual(output_node.read_all_out_pins()[0],
                             get_test_values()[0],
                             "Program yields expected output")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")

    def test_reroute(self):
        numbers_node = make_node(get_test_values)
        reroute_node = make_node(reroute_execution)
        buffer_node  = make_node(test_buffer)
        ## connect everything
        self.assertTrue(numbers_node.exec_out_pins[0].try_connect(reroute_node.exec_in_pins[0])), "Connecting "
        self.assertTrue(reroute_node.exec_out_pins[0].try_connect(buffer_node.exec_in_pins[0]), "Connecting reroute-exec to buffer-exec")
        self.assertTrue(numbers_node.out_pins[0].try_connect(buffer_node.in_pins[0]))
        try:
            run_graph(numbers_node)
            self.assertEqual(numbers_node.read_all_out_pins()[0], get_test_values()[0], "Program yields expected output")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")


    def test_roll_percent(self):
        random_node = make_node(roll_percent)
        output_node = make_node(test_buffer)
        self.assertEqual(len(random_node.exec_out_pins), 1, "has one such pin")
        self.assertEqual(len(random_node.exec_in_pins), 1, "has one such pin")
        self.assertEqual(len(random_node.out_pins), 1, "has one such pin")
        self.assertEqual(len(random_node.in_pins), 0, "has no such pin")

        self.assertEqual(len(output_node.exec_out_pins), 1, "has one such pin")
        self.assertEqual(len(output_node.exec_in_pins), 1, "has one such pin")
        self.assertEqual(len(output_node.out_pins), 1, "has one such pin")
        self.assertEqual(len(output_node.in_pins), 1, "has one such pin")
        ## connect everything
        self.assertTrue(random_node.exec_out_pins[0].try_connect(output_node.exec_in_pins[0]), "Connecting execution line")
        self.assertTrue(random_node.out_pins[0].try_connect(output_node.in_pins[0]), "Connecting data line")

        try:
            accum = 0
            for trial in range(_TRIAL_COUNT):
                run_graph(random_node.exec_in_pins[0])
                accum += output_node.read_all_out_pins()[0]
            mean = float(accum) / _TRIAL_COUNT
            expected_mean = 0.5
            self.assertLessEqual(abs(expected_mean - mean),
                                 expected_mean * _ACCEPTABLE_DEVIATION_OF_MEAN,
                                 "Random percent within acceptable deviation")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")



if __name__ == '__main__':
    ## show all loaded functions
    print(f"keys = {', '.join(ALL_FUNCTIONS.keys())}")
    unittest.main()

