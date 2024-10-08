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
from pysmt.shortcuts import Symbol, Iff, And, Or, Not, TRUE, FALSE, Implies
from pyvmt.shortcuts import Next, F, X, G, U, R, Y, Z, H, S, O, T, N
from pyvmt.environment import reset_env, get_env
from pyvmt.operators import HasLtlOperatorsWalker, NNFIzer
from pyvmt.vmtlib.printers import VmtPrinter, VmtDagPrinter
from pyvmt.model import Model
from pyvmt.ltl_encoder import (
        ltl_encode, ltlf_encode, safetyltl_encode, LtlEncodingWalker, LtlRewriter,
        LtlCircuitEncodingWalker, LtlfEncodingWalker)

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
        self.assertTrue(walker.has_ltl(mgr.N(x)))
        self.assertTrue(walker.has_ltl(mgr.G(x)))
        self.assertTrue(walker.has_ltl(mgr.F(x)))
        self.assertTrue(walker.has_ltl(mgr.R(x, y)))
        self.assertTrue(walker.has_ltl(mgr.U(x, y)))
        self.assertTrue(walker.has_ltl(mgr.Y(x)))
        self.assertTrue(walker.has_ltl(mgr.Z(x)))
        self.assertTrue(walker.has_ltl(mgr.H(x)))
        self.assertTrue(walker.has_ltl(mgr.O(x)))
        self.assertTrue(walker.has_ltl(mgr.T(x, y)))
        self.assertTrue(walker.has_ltl(mgr.S(x, y)))
        self.assertTrue(walker.has_ltl(Iff(x, And(y, mgr.U(x, y)))))
        self.assertTrue(walker.has_ltl(Iff(x, And(y, mgr.S(x, y)))))

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
        self.assertEqual(f_to_str(mgr.N(x), False), '(ltl.N x)')
        self.assertEqual(f_to_str(mgr.F(x), False), '(ltl.F x)')
        self.assertEqual(f_to_str(mgr.G(x), False), '(ltl.G x)')
        self.assertEqual(f_to_str(mgr.U(x, y), False), '(ltl.U x y)')
        self.assertEqual(f_to_str(mgr.R(x, y), False), '(ltl.R x y)')
        self.assertEqual(f_to_str(mgr.Y(x), False), '(ltl.Y x)')
        self.assertEqual(f_to_str(mgr.Z(x), False), '(ltl.Z x)')
        self.assertEqual(f_to_str(mgr.O(x), False), '(ltl.O x)')
        self.assertEqual(f_to_str(mgr.H(x), False), '(ltl.H x)')
        self.assertEqual(f_to_str(mgr.S(x, y), False), '(ltl.S x y)')
        self.assertRaises(NotImplementedError, lambda: f_to_str(mgr.T(x, y), False))
        self.assertEqual(f_to_str(mgr.X(x), True), '(let ((.def_0 (ltl.X x))) .def_0)')
        self.assertEqual(f_to_str(mgr.N(x), True), '(let ((.def_0 (ltl.N x))) .def_0)')
        self.assertEqual(f_to_str(mgr.F(x), True), '(let ((.def_0 (ltl.F x))) .def_0)')
        self.assertEqual(f_to_str(mgr.G(x), True), '(let ((.def_0 (ltl.G x))) .def_0)')
        self.assertEqual(f_to_str(mgr.U(x, y), True), '(let ((.def_0 (ltl.U x y))) .def_0)')
        self.assertEqual(f_to_str(mgr.R(x, y), True), '(let ((.def_0 (ltl.R x y))) .def_0)')
        self.assertEqual(f_to_str(mgr.Y(x), True), '(let ((.def_0 (ltl.Y x))) .def_0)')
        self.assertEqual(f_to_str(mgr.Z(x), True), '(let ((.def_0 (ltl.Z x))) .def_0)')
        self.assertEqual(f_to_str(mgr.O(x), True), '(let ((.def_0 (ltl.O x))) .def_0)')
        self.assertEqual(f_to_str(mgr.H(x), True), '(let ((.def_0 (ltl.H x))) .def_0)')
        self.assertEqual(f_to_str(mgr.S(x, y), True), '(let ((.def_0 (ltl.S x y))) .def_0)')
        self.assertRaises(NotImplementedError, lambda: f_to_str(mgr.T(x, y), True))

        # HR printer
        self.assertEqual(mgr.X(x).serialize(), '(X x)')
        self.assertEqual(mgr.N(x).serialize(), '(N x)')
        self.assertEqual(mgr.F(x).serialize(), '(F x)')
        self.assertEqual(mgr.G(x).serialize(), '(G x)')
        self.assertEqual(mgr.U(x, y).serialize(), '(x U y)')
        self.assertEqual(mgr.R(x, y).serialize(), '(x R y)')
        self.assertEqual(mgr.Y(x).serialize(), '(Y x)')
        self.assertEqual(mgr.Z(x).serialize(), '(Z x)')
        self.assertEqual(mgr.O(x).serialize(), '(O x)')
        self.assertEqual(mgr.H(x).serialize(), '(H x)')
        self.assertEqual(mgr.S(x, y).serialize(), '(x S y)')
        self.assertEqual(mgr.T(x, y).serialize(), '(x T y)')

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
        self.assertEqual(walker.convert(mgr.Not(mgr.N(f))),
            mgr.X(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.X(f))),
            mgr.N(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.G(f))),
            mgr.F(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.G(f))),
            mgr.F(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.U(f, g))),
            mgr.R(negated_f, negated_g))
        self.assertEqual(walker.convert(mgr.Not(mgr.R(f, g))),
            mgr.U(negated_f, negated_g))

        self.assertEqual(walker.convert(mgr.Not(mgr.Y(f))),
            mgr.Z(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.Z(f))),
            mgr.Y(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.H(f))),
            mgr.O(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.O(f))),
            mgr.H(negated_f))
        self.assertEqual(walker.convert(mgr.Not(mgr.S(f, g))),
            mgr.T(negated_f, negated_g))
        self.assertEqual(walker.convert(mgr.Not(mgr.T(f, g))),
            mgr.S(negated_f, negated_g))

        unary_w = [mgr.F, mgr.G, mgr.X, mgr.N, mgr.Next, mgr.Y, mgr.Z, mgr.O, mgr.H]
        binary_w = [mgr.U, mgr.R, mgr.S, mgr.T]

        for wrapper in unary_w:
            self.assertEqual(walker.convert(wrapper(mgr.Not(g))),
                wrapper(negated_g))

        for wrapper in binary_w:
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
        self.assertEqual(rewriter.rewrite(N(f)), Not(X(Not(f))))
        self.assertEqual(rewriter.rewrite(U(z, f)), U(z, f))
        self.assertEqual(rewriter.rewrite(R(z, f)),
            Not(U(Not(z), Not(f)))
        )
        self.assertEqual(rewriter.rewrite(F(f)), U(TRUE(), f))
        self.assertEqual(rewriter.rewrite(G(f)), Not(U(TRUE(), Not(f))))

        # Past operators

        self.assertEqual(rewriter.rewrite(Y(f)), Y(f))
        # Z -> Y
        self.assertEqual(rewriter.rewrite(Z(f)), Not(Y(Not(f))))
        self.assertEqual(rewriter.rewrite(S(z, f)), S(z, f))
        # T -> S
        self.assertEqual(rewriter.rewrite(T(z, f)),
            Not(S(Not(z), Not(f)))
        )
        # O -> S
        self.assertEqual(rewriter.rewrite(O(f)), S(TRUE(), f))
        # H -> S
        self.assertEqual(rewriter.rewrite(H(f)), Not(S(TRUE(), Not(f))))

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

        el1 = Y(And(x, y))
        el0 = S(x, z)
        f = And(el1, el0)
        walker = LtlEncodingWalker(f)
        el = walker.get_el_map()
        self.assertSetEqual(set(el), { el1, Y(el0) })

        self.assertEqual(walker.get_sat(el0),
            Or(z, And(x, el[Y(el0)])))
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

        self.assertSetEqual(set(new_model.get_trans_constraints()[0:2]),
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
        self.assertSetEqual(set(new_model.get_init_constraints()[0:1]),
            set([
                Not(And(el_x_1, Or(z, And(x, el_u_0))))
            ])
        )
        self.assertEqual(new_model.get_live_properties()[0].formula,
            Not(Symbol('J_2')))

    def test_ltl_encode_past(self):
        '''Test the ltl encoding procedure for past operators'''
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        el0 = S(x, z)
        el1 = Y(And(x, y))
        f = And(el1, el0)

        model = Model()
        model.add_state_var(x)
        model.add_state_var(y)
        model.add_state_var(z)
        new_model = ltl_encode(model, f)

        el_s_0 = Symbol('el_s_0')
        el_y_1 = Symbol('el_y_1')

        self.assertSetEqual(set(new_model.get_trans_constraints()[0:2]),
            set([
                Iff(
                    Next(el_s_0),
                    Or(z, And(x, el_s_0))
                ),
                Iff(
                    Next(el_y_1),
                    And(x, y)
                )
            ]))
        self.assertSetEqual(set(new_model.get_init_constraints()[0:1]),
            set([
                Not(And(el_y_1, Or(z, And(x, el_s_0))))
            ])
        )

        self.assertEqual(new_model.get_live_properties()[0].formula,
            Not(TRUE()))

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

        f_past = G(And(Y(x),S(Or(y, z), y)))
        walker = LtlCircuitEncodingWalker(f_past)
        subformulae = walker.get_subformulae()
        lbls = [x for x, _ in subformulae]
        self.assertListEqual(subformulae, [
            ( lbls[0], Or(y, z), ),
            ( lbls[1], S(lbls[0], y), ),
            ( lbls[2], Y(x), ),
            ( lbls[3], And(lbls[2], lbls[1]), ),
            ( lbls[4], G(lbls[3]),), ])

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

    def test_monitors(self):
        '''Test that the generation of monitors for LTL circuit encoder is correct'''
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        f = R(U(F(G(X(And(x, Or(y, z))))), y), z)
        is_init = Symbol('is_init')
        walker = LtlCircuitEncodingWalker(f)
        subformulae = walker.get_subformulae()
        subf_map = dict(subformulae)
        lbls = list(subf_map.keys())

        # Or
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[0], subf_map[lbls[0]])
        self.assertListEqual(stvars, [])
        self.assertListEqual(init, [])
        self.assertListEqual(trans, [])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[0], Not(Or(y, z))))
        self.assertEqual(pending, FALSE())

        # And
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[1], subf_map[lbls[1]])
        self.assertListEqual(stvars, [])
        self.assertListEqual(init, [])
        self.assertListEqual(trans, [])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[1], Not(And(x, lbls[0]))))
        self.assertEqual(pending, FALSE())

        # LTL.X
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[2], subf_map[lbls[2]])
        self.assertEqual(len(stvars), 1)
        yz = stvars[0]
        self.assertListEqual(init, [Not(yz)])
        self.assertListEqual(trans, [Iff(Next(yz), lbls[2])])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(yz, Not(lbls[1])))
        self.assertEqual(pending, lbls[2])

        # LTL.G
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[3], subf_map[lbls[3]])
        self.assertEqual(len(stvars), 1)
        y_pending = stvars[0]
        self.assertListEqual(init, [Not(y_pending)])
        self.assertListEqual(trans, [Iff(Next(y_pending), pending)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(pending, Not(lbls[2])))
        self.assertEqual(pending, Or(y_pending, lbls[3]))

        # LTL.F
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[4], subf_map[lbls[4]])
        self.assertEqual(len(stvars), 1)
        y_pending = stvars[0]
        self.assertListEqual(init, [Not(y_pending)])
        self.assertListEqual(trans, [Iff(Next(y_pending), pending)])
        self.assertEqual(pending, And(Or(lbls[4], y_pending), Not(lbls[3])))
        self.assertEqual(accept, Not(pending))
        self.assertEqual(failed, FALSE())

        # LTL.U
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[5], subf_map[lbls[5]])
        self.assertEqual(len(stvars), 1)
        y_pending = stvars[0]
        self.assertListEqual(init, [Not(y_pending)])
        self.assertListEqual(trans, [Iff(Next(y_pending), pending)])
        self.assertEqual(pending, And(Or(lbls[5], y_pending), Not(y)))
        self.assertEqual(accept, Not(pending))
        self.assertEqual(failed, And(pending, Not(lbls[4])))

        # LTL.R
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[6], subf_map[lbls[6]])
        self.assertEqual(len(stvars), 1)
        y_pending = stvars[0]
        self.assertListEqual(init, [Not(y_pending)])
        self.assertListEqual(trans, [Iff(Next(y_pending), pending)])
        self.assertEqual(pending, And(Or(lbls[6], y_pending), Not(lbls[5])))
        self.assertEqual(accept, Not(pending))
        self.assertEqual(failed, And(pending, Not(z)))

    def test_monitors_past(self):
        '''Test that the generation of monitors for (past) LTL circuit encoder is correct'''
        x = Symbol('x')
        y = Symbol('y')
        z = Symbol('z')
        f = T(S(O(H(Y(x))), y), Z(z))
        is_init = Symbol('is_init')
        walker = LtlCircuitEncodingWalker(f)
        subformulae = walker.get_subformulae()
        subf_map = dict(subformulae)
        lbls = list(subf_map.keys())

        # LTL.Z
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[0], subf_map[lbls[0]])
        self.assertEqual(len(stvars), 1)
        zarg = stvars[0]
        self.assertListEqual(init, [zarg])
        self.assertListEqual(trans, [Iff(Next(zarg), z)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[0], Not(zarg)))
        self.assertEqual(pending, FALSE())

        # LTL.Y
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[1], subf_map[lbls[1]])
        self.assertEqual(len(stvars), 1)
        yarg = stvars[0]
        self.assertListEqual(init, [Not(yarg)])
        self.assertListEqual(trans, [Iff(Next(yarg), x)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[1], Not(yarg)))
        self.assertEqual(pending, FALSE())

        # LTL.H
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[2], subf_map[lbls[2]])
        self.assertEqual(len(stvars), 1)
        ynt = stvars[0]
        self.assertListEqual(init, [Not(ynt)])
        nt = Or(ynt, Not(lbls[1]))
        self.assertListEqual(trans, [Iff(Next(ynt), nt)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[2], nt))
        self.assertEqual(pending, FALSE())

        # LTL.O
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[3], subf_map[lbls[3]])
        self.assertEqual(len(stvars), 1)
        yt = stvars[0]
        self.assertListEqual(init, [Not(yt)])
        t = Or(yt, lbls[2])
        self.assertListEqual(trans, [Iff(Next(yt), t)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[3], Not(t)))
        self.assertEqual(pending, FALSE())

        # LTL.S
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[4], subf_map[lbls[4]])
        self.assertEqual(len(stvars), 1)
        yt = stvars[0]
        self.assertListEqual(init, [Not(yt)])
        t = Or(y, And(yt, lbls[3]))
        self.assertListEqual(trans, [Iff(Next(yt), t)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[4], Not(t)))
        self.assertEqual(pending, FALSE())

        # LTL.T
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, lbls[5], subf_map[lbls[5]])
        self.assertEqual(len(stvars), 1)
        ynt = stvars[0]
        self.assertListEqual(init, [Not(ynt)])
        nt = Or(Not(lbls[0]), And(ynt, Not(lbls[4])))
        self.assertListEqual(trans, [Iff(Next(ynt), nt)])
        self.assertEqual(accept, TRUE())
        self.assertEqual(failed, And(lbls[5], nt))
        self.assertEqual(pending, FALSE())

    def test_ltlf_encode(self):
        '''Test the ltlf encoding procedure'''
        a = Symbol('a')
        model = Model()
        model.add_state_var(a)

        el0 = X(a)
        el1 = G(el0)
        el2 = And(a, el1)
        el3 = G(a)
        f = Iff(el2, el3)

        model = Model()
        model.add_state_var(a)
        # (G X(a) & X (a)) <-> G (a)
        new_model = ltlf_encode(model, f)

        # From el0 X -> N/X (both polarities)
        el_n_0 = Symbol('el_n_0')
        el_x_4 = Symbol('el_x_4')

        # From el1 G -> U/R (both polarities)
        el_u_1 = Symbol('el_u_1')
        el_r_2 = Symbol('el_r_2')

        # From el3 G -> U/R (both polarities)
        el_u_3 = Symbol('el_u_3')
        el_r_5 = Symbol('el_r_5')

        self.assertSetEqual(set(new_model.get_trans_constraints()),
            set([
                Implies( el_n_0, Next(Not(a))),
                Implies(el_u_1, Next(Or(el_n_0, And(TRUE(), el_u_1)))),
                Implies(el_r_2, Next(And(a, Or(Not(TRUE()), el_r_2)))),
                Implies(el_u_3, Next(Or(Not(a), And(TRUE(), el_u_3)))),
                Implies(el_x_4, Next(a)),
                Implies(el_r_5, Next(And(el_x_4, Or(Not(TRUE()), el_r_5))))]))

        self.assertEqual(new_model.get_invar_properties()[0].formula,
                         Or(Or(Or(FALSE(), el_u_1), el_u_3), el_x_4))

if __name__ == '__main__':
    pytest.main(sys.argv)
