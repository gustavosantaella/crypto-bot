import unittest
from logic import AndGate, OrGate, NotGate, XorGate, NandGate, HalfAdder, FullAdder, NBitAdder, ALU

class TestLogicGates(unittest.TestCase):
    def test_and_gate(self):
        g = AndGate("AND")
        g.input_a.set_value(0)
        g.input_b.set_value(0)
        self.assertEqual(g.output.get_value(), 0)
        g.input_a.set_value(1)
        self.assertEqual(g.output.get_value(), 0)
        g.input_b.set_value(1)
        self.assertEqual(g.output.get_value(), 1)

    def test_or_gate(self):
        g = OrGate("OR")
        g.input_a.set_value(0)
        g.input_b.set_value(0)
        self.assertEqual(g.output.get_value(), 0)
        g.input_a.set_value(1)
        self.assertEqual(g.output.get_value(), 1)

    def test_not_gate(self):
        g = NotGate("NOT")
        g.input.set_value(0)
        self.assertEqual(g.output.get_value(), 1)
        g.input.set_value(1)
        self.assertEqual(g.output.get_value(), 0)

    def test_xor_gate(self):
        g = XorGate("XOR")
        g.input_a.set_value(0)
        g.input_b.set_value(0)
        self.assertEqual(g.output.get_value(), 0)
        g.input_a.set_value(1)
        g.input_b.set_value(0)
        self.assertEqual(g.output.get_value(), 1)
        g.input_a.set_value(1)
        g.input_b.set_value(1)
        self.assertEqual(g.output.get_value(), 0)

    def test_nand_gate(self):
        g = NandGate("NAND")
        g.input_a.set_value(0)
        g.input_b.set_value(0)
        self.assertEqual(g.output.get_value(), 1)
        g.input_a.set_value(1)
        g.input_b.set_value(1)
        self.assertEqual(g.output.get_value(), 0)

class TestAdders(unittest.TestCase):
    def test_half_adder(self):
        ha = HalfAdder("HA")
        ha.input_a.set_value(0)
        ha.input_b.set_value(0)
        self.assertEqual(ha.sum.get_value(), 0)
        self.assertEqual(ha.carry.get_value(), 0)
        ha.input_a.set_value(1)
        ha.input_b.set_value(1)
        self.assertEqual(ha.sum.get_value(), 0)
        self.assertEqual(ha.carry.get_value(), 1)

    def test_full_adder(self):
        fa = FullAdder("FA")
        fa.input_a.set_value(1)
        fa.input_b.set_value(1)
        fa.input_carry.set_value(1)
        self.assertEqual(fa.sum.get_value(), 1)
        self.assertEqual(fa.carry_out.get_value(), 1)

    def test_n_bit_adder(self):
        nb = NBitAdder("NB", 4)
        # 5 (0101) + 3 (0011) = 8 (1000)
        nb.inputs_a[0].set_value(1)
        nb.inputs_a[1].set_value(0)
        nb.inputs_a[2].set_value(1)
        nb.inputs_a[3].set_value(0)
        nb.inputs_b[0].set_value(1)
        nb.inputs_b[1].set_value(1)
        nb.inputs_b[2].set_value(0)
        nb.inputs_b[3].set_value(0)
        
        results = [o.get_value() for o in nb.outputs]
        self.assertEqual(results, [0, 0, 0, 1])
        self.assertEqual(nb.carry_out.get_value(), 0)

class TestALU(unittest.TestCase):
    def test_alu_add(self):
        alu = ALU("ALU", 4)
        # ADD: 5 + 3 = 8
        alu.inputs_a[0].set_value(1)
        alu.inputs_a[1].set_value(0)
        alu.inputs_a[2].set_value(1)
        alu.inputs_a[3].set_value(0)
        alu.inputs_b[0].set_value(1)
        alu.inputs_b[1].set_value(1)
        alu.inputs_b[2].set_value(0)
        alu.inputs_b[3].set_value(0)
        # S1=0, S0=0 for ADD
        alu.s1.set_value(0)
        alu.s0.set_value(0)
        
        results = [o.get_value() for o in alu.outputs]
        self.assertEqual(results, [0, 0, 0, 1])

    def test_alu_sub(self):
        alu = ALU("ALU", 4)
        # SUB: 5 - 3 = 2
        alu.inputs_a[0].set_value(1)
        alu.inputs_a[1].set_value(0)
        alu.inputs_a[2].set_value(1)
        alu.inputs_a[3].set_value(0)
        alu.inputs_b[0].set_value(1)
        alu.inputs_b[1].set_value(1)
        alu.inputs_b[2].set_value(0)
        alu.inputs_b[3].set_value(0)
        # S1=0, S0=1 for SUB
        alu.s1.set_value(0)
        alu.s0.set_value(1)
        
        results = [o.get_value() for o in alu.outputs]
        self.assertEqual(results, [0, 1, 0, 0])

    def test_alu_and(self):
        alu = ALU("ALU", 4)
        # AND: 5 (0101) & 3 (0011) = 1 (0001)
        alu.inputs_a[0].set_value(1)
        alu.inputs_a[2].set_value(1)
        alu.inputs_b[0].set_value(1)
        alu.inputs_b[1].set_value(1)
        # S1=1, S0=0 for AND
        alu.s1.set_value(1)
        alu.s0.set_value(0)
        
        results = [o.get_value() for o in alu.outputs]
        self.assertEqual(results, [1, 0, 0, 0])

    def test_alu_or(self):
        alu = ALU("ALU", 4)
        # OR: 5 (0101) | 3 (0011) = 7 (0111)
        alu.inputs_a[0].set_value(1)
        alu.inputs_a[2].set_value(1)
        alu.inputs_b[0].set_value(1)
        alu.inputs_b[1].set_value(1)
        # S1=1, S0=1 for OR
        alu.s1.set_value(1)
        alu.s0.set_value(1)
        
        results = [o.get_value() for o in alu.outputs]
        self.assertEqual(results, [1, 1, 1, 0])

if __name__ == "__main__":
    unittest.main()
