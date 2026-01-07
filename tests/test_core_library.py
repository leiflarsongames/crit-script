import unittest

from crit_script import crit_script, Pin, Node, make_node, run_graph, ExecutionPin, ALL_FUNCTIONS, NodeContext
from crit_script_core import *

_DETERMINISTIC_VARIATION_COUNT = 15
"""The number of variations assessed for deterministic tests"""
_TRIAL_COUNT = 5000
"""The trial count for randomness-based tests"""
_ACCEPTABLE_DEVIATION_OF_MEAN = 0.02
"""The largest absolute deviation we will tolerate from the mean before failing a test, as a fraction of the expected mean."""

TEST_VALUES = (4, 6, 8)
TEST_VALUE = 42

@crit_script( inputs=(Pin(Any, "value-in")),
             outputs=(Pin(Any, "value-out")))
def test_buffer(ctx:NodeContext, value_in:Any) -> Any:
    return value_in

class TestCoreLibrary(unittest.TestCase):

    ## TODO rewrite a test or something! This isn't working for now.

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
        number_node = make_node(roll_percent)
        buffer_node = make_node(test_buffer)
        self.assertEqual(number_node.read_all_out_pins()[0], None, "(1/2) Unevaluated nodes should have no output available!")
        self.assertEqual(buffer_node.read_all_out_pins()[0], None, "(2/2) Unevaluated nodes should have no output available!")

    def test_run_simple_graph(self):
        """Runs a small graph, and inspects the output on the other side."""
        start_pin = ExecutionPin("program-start", out=True)
        node_0 = make_node(test_buffer)
        node_0.in_pins[0].write_value(TEST_VALUE)
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
                             TEST_VALUE,
                             "Program yields expected output")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")

    def test_reroute(self):
        numbers_node = make_node(test_buffer)
        numbers_node.in_pins[0].write_value(TEST_VALUE)
        reroute_node = make_node(reroute_execution)
        buffer_node  = make_node(test_buffer)
        ## connect everything
        self.assertTrue(numbers_node.exec_out_pins[0].try_connect(reroute_node.exec_in_pins[0])), "Connecting "
        self.assertTrue(reroute_node.exec_out_pins[0].try_connect(buffer_node.exec_in_pins[0]), "Connecting reroute-exec to buffer-exec")
        self.assertTrue(numbers_node.out_pins[0].try_connect(buffer_node.in_pins[0]))
        try:
            run_graph(numbers_node)
            self.assertEqual(numbers_node.read_all_out_pins()[0], TEST_VALUE, "Program yields expected output")
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
        self.assertTrue(random_node.out_pins[0].try_connect(output_node.in_pins[0]), "Connecting value line")

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

    def test_switch_compare(self):
        switch_node = make_node(switch_compare)
        out_node_0 = make_node(test_buffer)
        out_node_1 = make_node(test_buffer)
        out_node_2 = make_node(test_buffer)
        out_node_0.in_pins[0].write_value(500)  # when run, it will push this value to the output.
        out_node_1.in_pins[0].write_value(500)
        out_node_2.in_pins[0].write_value(500)

        ## connect everything
        self.assertTrue(switch_node.exec_out_pins[0].try_connect(out_node_0.exec_in_pins[0]),
                        "Connecting execution line 0")
        self.assertTrue(switch_node.exec_out_pins[1].try_connect(out_node_1.exec_in_pins[0]),
                        "Connecting execution line 1")
        self.assertTrue(switch_node.exec_out_pins[2].try_connect(out_node_2.exec_in_pins[0]),
                        "Connecting execution line 2")
        ## LESS THAN, PATH 0
        try:
            switch_node.in_pins[0].write_value(-1.0)
            switch_node.in_pins[1].write_value(12.0)
            self.assertIsNone(out_node_0.out_pins[0].read_value(),
                              "Assuring out_node_0's output starts as None")
            run_graph(switch_node)
            self.assertIsNotNone(out_node_0.out_pins[0].read_value(),
                                 "Assuring out_node_0's output becomes Something")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")

        ## EQUALITY, PATH 1
        try:
            switch_node.in_pins[0].write_value(9.0)
            switch_node.in_pins[1].write_value(9.0)
            self.assertIsNone(out_node_1.out_pins[0].read_value(),
                              "Assuring out_node_1's output starts as None")
            run_graph(switch_node)
            self.assertIsNotNone(out_node_1.out_pins[0].read_value(),
                                 "Assuring out_node_1's output becomes Something")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")

        ## EQUALITY, PATH 1
        try:
            switch_node.in_pins[0].write_value(9.0)
            switch_node.in_pins[1].write_value(7.0)
            self.assertIsNone(out_node_2.out_pins[0].read_value(),
                              "Assuring out_node_2's output starts as None")
            run_graph(switch_node)
            self.assertIsNotNone(out_node_2.out_pins[0].read_value(),
                                 "Assuring out_node_2's output becomes Something")
        except Exception as e:
            self.fail(f"Failed to run CritScript graph. Exception is as follows: {e}")

    def test_for_loop(self):
        raise NotImplementedError()

    def test_count_and_reset(self): ## TODO
        ## NOTE: outgoing execution pins not tested!
        cr_node = make_node(count_and_reset)
        run_graph(cr_node.exec_in_pins[0])    # exec-in
        self.assertEqual(cr_node.read_all_out_pins()[0], 0, "step 0")
        run_graph(cr_node.exec_in_pins[2])    # add-one
        self.assertEqual(cr_node.read_all_out_pins()[0], 1, "step 1")
        run_graph(cr_node.exec_in_pins[2])    # add-one
        self.assertEqual(cr_node.read_all_out_pins()[0], 2, "step 2")
        run_graph(cr_node.exec_in_pins[0])    # exec-in
        self.assertEqual(cr_node.read_all_out_pins()[0], 2, "step 3")
        run_graph(cr_node.exec_in_pins[1])    # reset
        self.assertEqual(cr_node.read_all_out_pins()[0], 0, "step 4")
        run_graph(cr_node.exec_in_pins[2])    # add-one
        self.assertEqual(cr_node.read_all_out_pins()[0], 1, "step 5")
        run_graph(cr_node.exec_in_pins[0])    # exec-in
        self.assertEqual(cr_node.read_all_out_pins()[0], 1, "step 6")
        run_graph(cr_node.exec_in_pins[1])    # reset
        self.assertEqual(cr_node.read_all_out_pins()[0], 0, "step 7")

    # def test_wake_up(self):         ## TODO
    #     raise NotImplementedError()
    #
    # def test_modulo(self):          ## TODO
    #     raise NotImplementedError()
    #
    # def test_negate(self):          ## TODO
    #     raise NotImplementedError()
    #
    # def test_just_in_time_propagation(self):    ## TODO
    #     raise NotImplementedError()
    #
    # def test_for_loop(self):        ## TODO
    #     raise NotImplementedError()
    #
    # def test_signal(self):          ## TODO
    #     raise NotImplementedError()

if __name__ == '__main__':
    ## show all loaded functions
    print(f"keys = {', '.join(ALL_FUNCTIONS.keys())}")
    unittest.main()

