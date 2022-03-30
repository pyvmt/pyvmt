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

import sys
from unittest import TestCase
import pytest
from io import StringIO
from pysmt.shortcuts import Symbol, Iff, And
from pyvmt.environment import reset_env, get_env
from pyvmt.operators import HasLtlOperatorsWalker
from pyvmt.vmtlib.printers import VmtPrinter, VmtDagPrinter

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

if __name__ == '__main__':
    pytest.main(sys.argv)
