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
from pysmt.shortcuts import Symbol, And, TRUE, FALSE, Equals, Or, Int, Exists, BVExtract
from pysmt import typing
from pyvmt.environment import reset_env, get_env
from pyvmt.vmtlib.printers import VmtPrinter, VmtDagPrinter
from pyvmt.operators import NextPusher
from pyvmt import exceptions
from pyvmt.shortcuts import Next

class TestNext(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_printers(self):
        '''Test if the VMT-LIB printers work correctly
        '''
        x = Symbol('x')
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
        self.assertRaises(NotImplementedError, lambda: f_to_str(mgr.Next(x), False))
        self.assertRaises(NotImplementedError, lambda: f_to_str(mgr.Next(x), True))

        # HR printer
        self.assertEqual(mgr.Next(x).serialize(), 'x\'')

    def test_pusher(self):
        '''Test that the NextPusher walker correctly pushes the Next
        operators to the leaf nodes containing a Symbol
        '''
        mgr = get_env().formula_manager
        a = Symbol('a')
        b = Symbol('b')
        x = Symbol('x', typing.INT)

        pusher = NextPusher()
        self.assertEqual(pusher.push_next(mgr.Next(And(a, b))),
            And(mgr.Next(a), mgr.Next(b)))
        self.assertEqual(pusher.push_next(mgr.Next(And(a, FALSE()))),
            And(mgr.Next(a), FALSE()))

        f = And(mgr.Next(Or(a, b, FALSE())), mgr.Next(Equals(x, Int(0))))
        f_res = And(Or(mgr.Next(a), mgr.Next(b), FALSE()), Equals(mgr.Next(x), Int(0)))
        self.assertEqual(pusher.push_next(f), f_res)
        self.assertEqual(pusher.push_next(f_res), f_res)

    def test_quantifiers(self):
        '''Test if a formula with quantifiers is handled correctly.'''
        mgr = get_env().formula_manager
        a = Symbol('a')
        b = Symbol('b')
        x = Symbol('x', typing.INT)
        pusher = NextPusher()

        f_quant = mgr.Next(Exists([x], And(a, b, TRUE(), Equals(x, Int(1)))))
        f_quant_res = Exists([x],
            And(mgr.Next(a), mgr.Next(b), TRUE(), Equals(x, Int(1))))
        self.assertEqual(pusher.push_next(f_quant), f_quant_res)

    def test_has_next(self):
        '''Test if the HasNextOperatorWalker works correctly'''
        mgr = get_env().formula_manager
        a = Symbol('a')
        b = Symbol('b')
        x = Symbol('x', typing.INT)

        walker = get_env().has_next_operator_walker
        self.assertTrue(walker.has_next(mgr.Next(a)))
        self.assertTrue(walker.has_next(And(mgr.Next(a), b)))
        self.assertTrue(walker.has_next(Exists([x], And(mgr.Next(a), b, Equals(x, Int(1))))))
        self.assertFalse(walker.has_next(And(a, b)))
        self.assertFalse(walker.has_next(Exists([x], And(a, b, Equals(x, Int(1))))))

    def test_nested(self):
        '''Test if nesting Next operators raises an exception'''
        mgr = get_env().formula_manager
        a = Symbol('a')

        f = mgr.Next(a)
        self.assertRaises(exceptions.UnexpectedNextError,
            lambda: mgr.Next(f))

    def test_bv_operators(self):
        '''Tests if the Next operator works with the BV Operators as intended'''
        #TODO change behavior to make the test pass
        a = Symbol('a', typing.BV32)
        f = BVExtract(a, start=12, end=14)
        next_f = Next(f)

        pusher = NextPusher()
        self.assertEqual(pusher.push_next(next_f),
            BVExtract(Next(a), start=12, end=14))

if __name__ == '__main__':
    pytest.main(sys.argv)
