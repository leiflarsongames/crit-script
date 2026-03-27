import unittest
from crit_script import *
from crit_script_make import *

class TestGlobalVariables(unittest.TestCase):
    def test_user_created_global_variable(self):
        create_global_variable("tree-species")
        set_node = make_node("set-tree-species")
        set_node.in_pins[0].write_value("juniper")
        run_graph(set_node.exec_in_pins[0])

        get_node = make_node("get-tree-species")
        run_graph(get_node.exec_in_pins[0])
        self.assertEqual(get_node.out_pins[0], "juniper", "can set the variable")

if __name__ == '__main__':
    unittest.main()
