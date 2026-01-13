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

@crit_script( inputs=(Pin("value-in", Any)),
             outputs=(Pin("value-out", Any)))
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

    def test_run_graph_from_exec_out_pin(self):
        """Runs a small graph, and inspects the output on the other side."""
        ## start from an execution out pin (!)
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
        switch_node = make_node(switch_by_comparison)
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

    def test_count_and_reset(self): ## TODO
        ## NOTE: outgoing execution pins not tested!
        ## TODO test outgoing execution pins with a "select" node or something
        cr_node = make_node(count_and_reset)
        self.assertEqual(cr_node.memory, 0, "verify that count-and-reset node woke up properly")
        self.assertEqual(cr_node.read_all_out_pins()[0], 0, "step 0... nothing done yet.")
        run_graph(cr_node.exec_in_pins[0])    # add-one
        self.assertEqual(cr_node.read_all_out_pins()[0], 1, "step 1")
        run_graph(cr_node.exec_in_pins[0])    # add-one
        self.assertEqual(cr_node.read_all_out_pins()[0], 2, "step 2")
        run_graph(cr_node.exec_in_pins[1])    # reset
        self.assertEqual(cr_node.read_all_out_pins()[0], 0, "step 3")
        run_graph(cr_node.exec_in_pins[0])    # add-one
        self.assertEqual(cr_node.read_all_out_pins()[0], 1, "step 4")
        run_graph(cr_node.exec_in_pins[1])    # reset
        self.assertEqual(cr_node.read_all_out_pins()[0], 0, "step 5")

    def test_loop(self):
        ITERATIONS = 5
        looper_node = make_node(loop)
        count_node = make_node(count_and_reset)
        joint_node = make_node(execution_joint)
        branch_node = make_node(switch_by_comparison)
        branch_node.in_pins[1].last_value = ITERATIONS   # Set the number of iterations
        later_joint_node = make_node(execution_joint)
        debug_node = make_node(debug_wait_or_quit)
        self.assertTrue(looper_node.exec_out_pins[0].try_connect(count_node.exec_in_pins[0]), "connect loop to loop body")
        self.assertTrue(count_node.exec_out_pins[0].try_connect(joint_node.exec_in_pins[0]), "(1/2) connect counter to first joint")
        self.assertTrue(count_node.exec_out_pins[1].try_connect(joint_node.exec_in_pins[1]), "(2/2) connect counter to first joint")
        self.assertTrue(joint_node.exec_out_pins[0].try_connect(branch_node.exec_in_pins[0]), "connect joint to branch")
        self.assertTrue(count_node.out_pins[0].try_connect(branch_node.in_pins[0]), "connect counter out-value to branch")
        # Arguably, one could have simply attached ``branch_node.exec_out_pins[0]`` to ``count_node.exec_in_pins[0]``
        # and not involved this "loop" stuff, but this "loop stuff" is a precursor to for loops and for-each loops so
        # this is actually great.
        self.assertTrue(branch_node.exec_out_pins[1].try_connect(later_joint_node.exec_in_pins[0]), "connect a=b to second joint node")
        self.assertTrue(branch_node.exec_out_pins[2].try_connect(later_joint_node.exec_in_pins[1]), "connect a>b to second joint node")
        self.assertTrue(later_joint_node.exec_out_pins[0].try_connect(looper_node.exec_in_pins[1]), "connect second joint to loop break")
        self.assertFalse(branch_node.exec_out_pins[0].has_friend(), "verify that branch's [a<b] pin is disconnected")

        # ## DEBUG
        # self.assertTrue(branch_node.exec_out_pins[0].try_connect(debug_node.exec_in_pins[0]), "connect hanging branch to debug node for inspection.")
        # debug_node.in_pins[0].friend = count_node.out_pins[0]      # do something extremely suspicious
        # self.assertTrue(debug_node.in_pins[0].has_friend(), "If this fails, the DEBUG block won't work, but this isn't actually guaranteed functionality and the test battery maybe should otherwise succeed.")

        run_graph(looper_node.exec_in_pins[0])

        self.assertEqual(count_node.out_pins[0].read_value(), ITERATIONS, "Verifying final count = ITERATIONS")

    def test_reroute_value(self):
        """Note: relies on "just-in-time" logic but is not a full test of it."""

        self.fail('TODO fix "just-in-time" logic!')  ## TODO fix "just-in-time" logic!

        ## TODO write a test with only ONE reroute node to test the case where a "just-in-time" has NO neighbors that are also "just-in-time"!

        # transferring a value from an explicitly executed node to another explicitly executed node via multiple reroutes
        for test_value in TEST_VALUES:
            value_source = make_node(test_buffer)
            reroute_one = make_node(reroute_value)
            reroute_two = make_node(reroute_value)
            ## TODO add a third reroute node to test the case where a node has "just-in-time" on both sides!
            output_node = make_node(test_buffer)

            # insert the value into an explicitly executed node.
            value_source.in_pins[0].write_value(test_value)
            self.assertTrue(value_source.exec_out_pins[0].try_connect(output_node.exec_in_pins[0]), "connecting exec line")
            self.assertTrue(value_source.out_pins[0].try_connect(reroute_one.in_pins[0]), "Source->One value line")
            self.assertTrue(reroute_one.out_pins[0].try_connect(reroute_two.in_pins[0]), "One->Two value line")
            self.assertTrue(reroute_two.out_pins[0].try_connect(output_node.in_pins[0]), "Two->Output value line")

            run_graph(value_source)

            self.assertEqual(output_node.out_pins[0].read_value(), test_value,
                             "Able to transfer value between two explicitly executed nodes via reroutes.")

        for test_value in TEST_VALUES:
            reroute_one = make_node(reroute_value)
            reroute_two = make_node(reroute_value)
            ## TODO add a third reroute node to test the case where a node has "just-in-time" on both sides!
            output_node = make_node(test_buffer)

            # Insert value into a "just-in-time" node this time.
            reroute_one.in_pins[0].write_value(test_value)
            self.assertTrue(reroute_one.out_pins[0].try_connect(reroute_two.in_pins[0]), "One->Two value line")
            self.assertTrue(reroute_two.out_pins[0].try_connect(output_node.in_pins[0]), "Two->Output value line")

            run_graph(output_node)

            self.assertEqual(output_node.out_pins[0].read_value(), test_value,
                             "Able to transfer value from a chain starting with \"just-in-time\" nodes via reroutes.")



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

