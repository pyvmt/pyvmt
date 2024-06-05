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
'''
    Module to test the VMT-LIB reader

    Also tests VmtLibParser by testing if the LTL operators are read correctly
'''
import sys
from unittest import TestCase
from io import StringIO
import pytest
from pysmt import typing
from pysmt.constants import Fraction
from pysmt.shortcuts import Equals, Plus, Minus, Symbol, Real, And, LE, GE, Times, Div
from pyvmt.environment import reset_env, get_env
from pyvmt import exceptions
from pyvmt.vmtlib.reader import read

# a demo script for testing purposes
DEMO_SCRIPT = '''
(declare-fun x () Real) ; input variable
(declare-fun a () Real)
(declare-fun a.next () Real)
(define-fun .a-next () Real (! a :next a.next ))
(declare-fun sqrta () Real)
(declare-fun sqrta.next () Real)
(define-fun .sqrta-next () Real (! sqrta :next sqrta.next ))
(define-fun .a-init () Bool (! (and (<= 25.0 a) (>= 36.0 a)) :init true ))
(define-fun .sqrta-init () Bool (! (= a sqrta) :init true ))
(define-fun partial1 () Real ( / a sqrta ))
(define-fun avg () Real (/ (+ partial1 sqrta) 2.0))
(define-fun err () Real (- a (* sqrta sqrta)))
(define-fun .a-trans () Bool (! (= a a.next) :trans true ))
(define-fun .sqrta-trans () Bool (! (= sqrta.next avg) :trans true ))
(define-fun .live-prop () Bool (! (and (<= err 0.01) (>= err -0.01)) :live-property 0 ))
(define-fun .invar-prop () Bool (! (>= a 1) :invar-property 1 ))
(assert true)'''

# a demo script containing LTL operators
DEMO_LTL = '''
(declare-fun a () Bool)
(declare-fun a.next () Bool)
(define-fun .a-next () Bool (! a :next a.next ))
(define-fun .ltl-prop () Bool (! (ltl.G (ltl.X (ltl.F (ltl.U a a.next)))) :ltl-property 0 ))
(define-fun .pltl-prop () Bool (! (ltl.H (ltl.Y (ltl.O (ltl.S a a.next)))) :ltl-property 1 ))
(assert true)'''

class TestReader(TestCase):
    '''
        Class containing tests for the reader
    '''

    def setUp(self):
        reset_env()

    def test_variables(self):
        '''
            Test if the next relations and the input variables are created correctly
        '''
        model = read(StringIO(DEMO_SCRIPT))
        a = Symbol('a', typing.REAL)
        x = Symbol('x', typing.REAL)

        self.assertTrue(model.is_state_variable(a))

        self.assertFalse(model.is_state_variable(x))
        self.assertTrue(model.is_input_variable(x))

    def test_init(self):
        '''
            Test if the init constraints are created correctly
        '''
        model = read(StringIO(DEMO_SCRIPT))
        a = Symbol('a', typing.REAL)
        sqrta = Symbol('sqrta', typing.REAL)
        init_0 = And(LE(Real(25), a), GE(Real(36), a))
        init_1 = Equals(a, sqrta)

        init_constraints = model.get_init_constraints()
        self.assertEqual(len(init_constraints), 2)
        self.assertEqual(init_constraints[0], init_0)
        self.assertEqual(init_constraints[1], init_1)

    def test_trans(self):
        '''
            Test if the transition constraints are created correctly
        '''
        model = read(StringIO(DEMO_SCRIPT))
        a = Symbol('a', typing.REAL)
        sqrta = Symbol('sqrta', typing.REAL)
        trans_0 = Equals(a, model.next(a))
        trans_1 = Equals(model.next(sqrta), Div(Plus(Div(a, sqrta), sqrta), Real(2)))

        trans_constraints = model.get_trans_constraints()
        self.assertEqual(len(trans_constraints), 2)
        self.assertEqual(trans_constraints[0], trans_0)
        self.assertEqual(trans_constraints[1], trans_1)

    def test_properties(self):
        '''
            Test if the properties are created correctly
        '''
        model = read(StringIO(DEMO_SCRIPT))
        a = Symbol('a', typing.REAL)
        sqrta = Symbol('sqrta', typing.REAL)
        live_prop = model.get_property(0)
        err = Minus(a, Times(sqrta, sqrta))
        exp_prop = And(LE(err, Real(Fraction(1) / 100)), LE(Real(Fraction(-1) / 100), err))
        self.assertEqual(live_prop.formula, exp_prop)

        invar_prop = model.get_property(1)
        exp_prop = LE(Real(1), a)
        self.assertEqual(invar_prop.formula, exp_prop)

        self.assertTrue(live_prop.is_live())
        self.assertTrue(invar_prop.is_invar())

    def test_invalid_property_idx(self):
        '''
            Test if an invalid property idx raises an exception
        '''
        invalid_1 = StringIO('''
(declare-fun a () Bool)
(define-fun prop () Bool (! a :live-property o ))
(assert true)''')
        invalid_2 = StringIO('''
(declare-fun a () Bool)
(define-fun prop () Bool (! a :invar-property o ))
(assert true)''')

        self.assertRaises(exceptions.InvalidPropertyIdxError,
            lambda: read(invalid_1))
        self.assertRaises(exceptions.InvalidPropertyIdxError,
            lambda: read(invalid_2))

    def test_invalid_annotation(self):
        '''Test if an invalid annotation value for init and trans raises an Exception'''
        invalid_1 = StringIO('''
(declare-fun a () Bool)
(define-fun f () Bool (! a :init false ))
(assert true)''')
        invalid_2 = StringIO('''
(declare-fun a () Bool)
(define-fun f () Bool (! a :trans false ))
(assert true)''')
        self.assertRaises(exceptions.InvalidAnnotationValueError,
            lambda: read(invalid_1))
        self.assertRaises(exceptions.InvalidAnnotationValueError,
            lambda: read(invalid_2))

    def test_ltl(self):
        '''Test if a script containing LTL properties is read correctly'''
        # (ltl.G (ltl.X (ltl.F (ltl.U a a.next))))
        mgr = get_env().formula_manager
        model = read(StringIO(DEMO_LTL))
        a = model.get_state_vars()[0]
        prop = model.get_property(0)
        self.assertTrue(prop.is_ltl())
        self.assertEqual(prop.formula, mgr.G(mgr.X(mgr.F(mgr.U(a, model.next(a))))))

        prop = model.get_property(1)
        self.assertTrue(prop.is_ltl())
        self.assertEqual(prop.formula, mgr.H(mgr.Y(mgr.O(mgr.S(a, model.next(a))))))

if __name__ == '__main__':
    pytest.main(sys.argv)
