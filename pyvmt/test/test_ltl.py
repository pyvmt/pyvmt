#
#    Copyright 2022 Embedded Systems Unit, Fondazione Bruno Kessler
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.
#
'''Test the LTL operators of PyVmt
'''

from io import StringIO
import sys
from unittest import TestCase
import pytest
from pysmt.shortcuts import Symbol, Iff, And, Or, Not, TRUE
from pyvmt.shortcuts import Next, F, X, G, U, R
from pyvmt.environment import reset_env, get_env
from pyvmt.operators import HasLtlOperatorsWalker, NNFIzer
from pyvmt.vmtlib.printers import VmtPrinter, VmtDagPrinter
from pyvmt.model import Model
from pyvmt.ltl_encoder import ltl_encode, LtlEncodingWalker, LtlRewriter, LtlCircuitEncodingWalker

class TestLtl(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_has_ltl_operators_walker(self):
        '''Test if the HasLtlOperatorWalker class works correctly
        '''
        x = Symbol('x')
        y = Symbol('y')
        walker = HasLtlOperatorsWalker()
        mgr = get_env().formula_manager
        self.assertFalse(walker.has_ltl(Iff(x, y)))
        self.assertFalse(walker.has_ltl(x))
        self.assertTrue(walker.has_ltl(mgr.X(x)))
        self.assertTrue(walker.has_ltl(mgr.G(x)))
        self.assertTrue(walker.has_ltl(mgr.F(x)))
        self.assertTrue(walker.has_ltl(mgr.R(x, y)))
        self.assertTrue(walker.has_ltl(mgr.U(x, y)))
        self.assertTrue(walker.has_ltl(Iff(x, And(y, mgr.U(x, y)))))

    def test_printers(self):
        '''Test if the VMT-LIB printers work correctly
        '''
        x = Symbol('x')
        y = Symbol('y')
        mgr = get_env().formula_manager

        def f_to_str(formula, daggify):
            buf = StringIO()
            if daggify:
                printer = VmtDagPrinter(buf)
            else:
                printer = VmtPrinter(buf)
            printer.printer(formula)
            res = buf.getvalue()
            buf.close()
            return res

        # vmt printers
        self.assertEqual(f_to_str(mgr.X(x), False), '(ltl.X x)')
        self.assertEqual(f_to_str(mgr.F(x), False), '(ltl.F x)')
        self.assertEqual(f_to_str(mgr.G(x), False), '(ltl.G x)')
        self.assertEqual(f_to_str(mgr.U(x, y), False), '(ltl.U x y)')
        self.assertRaises(NotImplementedError, lambda: f_to_str(mgr.R(x, y), False))
        self.assertEqual(f_to_str(mgr.X(x), True), '(let ((.def_0 (ltl.X x))) .def_0)')
        self.assertEqual(f_to_str(mgr.F(x), True), '(let ((.def_0 (ltl.F x))) .def_0)')
        self.assertEqual(f_to_str(mgr.G(x), True), '(let ((.def_0 (ltl.G x))) .def_0)')
        self.assertEqual(f_to_str(mgr.U(x, y), True), '(let ((.def_0 (ltl.U x y))) .def_0)')
        self.assertRaises(NotImplementedError, lambda: f_to_str(mgr.R(x, y), True))

        # HR printer
        self.assertEqual(mgr.X(x).serialize(), '(X x)')
        self.assertEqual(mgr.F(x).serialize(), '(F x)')
        self.assertEqual(mgr.G(x).serialize(), '(G x)')
        self.assertEqual(mgr.U(x, y).serialize(), '(x U y)')
        self.assertEqual(mgr.R(x, y).serialize(), '(x R y)')

    def test_nnfizer(self):
        '''Test the NNFizer for the LTL operators'''
        mgr = get_env().formula_manager
        walker = NNFIzer()
        a = Symbol('a')
        b = Symbol('b')
        c = Symbol('c')
        f = And(a, Next(b))
        g = Or(a, c)
        negated_f = Or(Not(a), Next(Not(b)))
        negated_g = And(Not(a), Not(c))
        self.assertEqual(walker.convert(mgr.Not(mgr.X(f))),
            mgr.X(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.G(f))),
            mgr.F(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.G(f))),
            mgr.F(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.U(f, g))),
            mgr.R(negated_f, negated_g))
        self.assertEqual(walker.convert(mgr.Not(mgr.R(f, g))),
            mgr.U(negated_f, negated_g))
        for wrapper in [mgr.F, mgr.G, mgr.X, mgr.Next]:
            self.assertEqual(walker.convert(wrapper(mgr.Not(g))),
                wrapper(negated_g))
        for wrapper in [mgr.U, mgr.R]:
            self.assertEqual(walker.convert(wrapper(mgr.Not(f), mgr.Not(g))),
                wrapper(negated_f, negated_g))

    def test_ltl_rewriter(self):
        '''Test that the LTL rewriter works correctly'''
        rewriter = LtlRewriter()
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        f = And(x, y)
        self.assertEqual(rewriter.rewrite(X(f)), X(f))
        self.assertEqual(rewriter.rewrite(U(z, f)), U(z, f))
        self.assertEqual(rewriter.rewrite(R(z, f)),
            Not(U(Not(z), Not(f)))
        )
        self.assertEqual(rewriter.rewrite(F(f)), U(TRUE(), f))
        self.assertEqual(rewriter.rewrite(G(f)), Not(U(TRUE(), Not(f))))

    def test_ltl_encoding_walker(self):
        '''Test the LtlEncodingWalker, check the elementary subformulae and sat values'''
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        el1 = X(And(x, y))
        el0 = U(x, z)
        f = And(el1, el0)
        walker = LtlEncodingWalker(f)
        el = walker.get_el_map()
        self.assertSetEqual(set(el), { el1, X(el0) })

        self.assertEqual(walker.get_sat(el0),
            Or(z, And(x, el[X(el0)])))
        self.assertEqual(walker.get_sat(el1.arg(0)),
            And(x, y))

    def test_ltl_encode(self):
        '''Test the ltl encoding procedure'''
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        el0 = U(x, z)
        el1 = X(And(x, y))
        f = And(el1, el0)

        model = Model()
        model.add_state_var(x)
        model.add_state_var(y)
        model.add_state_var(z)
        new_model = ltl_encode(model, f)

        el_u_0 = Symbol('el_u_0')
        el_x_1 = Symbol('el_x_1')

        self.assertSetEqual(set(new_model.get_trans_constraints()),
            set([
                Iff(
                    el_u_0,
                    Next(Or(z, And(x, el_u_0)))
                ),
                Iff(
                    el_x_1,
                    Next(And(x, y))
                )
            ]))
        self.assertSetEqual(set(new_model.get_init_constraints()),
            set([
                Not(And(el_x_1, Or(z, And(x, el_u_0))))
            ])
        )
        self.assertEqual(new_model.get_live_properties()[0].formula,
            Or(Not(Or(z, And(x, el_u_0))) , z))
        new_model.get_live_properties()

    def test_circuit_encoding_walker(self):
        '''Test that the circuit encoding walker produces the correct subformulae
        '''
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        f = G(X(And(x, Or(y, z))))
        walker = LtlCircuitEncodingWalker(f)
        subformulae = walker.get_subformulae()
        lbls = [x for x, _ in subformulae]
        self.assertListEqual(subformulae, [
            ( lbls[0], Or(y, z), ),
            ( lbls[1], And(x, lbls[0]), ),
            ( lbls[2], X(lbls[1]) ),
            ( lbls[3], G(lbls[2]) ),
        ])

    def test_circuit_encoding_no_subformulae(self):
        '''Test the special case in which the circuit encoding walker does not find
            any subformulae
        '''
        x = Symbol('x')
        walker = LtlCircuitEncodingWalker(x)
        for _ in range(2):
            # running the function twice must not change the result
            subformulae = walker.get_subformulae()
            self.assertListEqual(subformulae, [
                ( Symbol('LTL.Z.0'), And(x, TRUE()), ),
            ])

if __name__ == '__main__':
    pytest.main(sys.argv)
