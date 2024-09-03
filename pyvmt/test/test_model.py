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
    Module to test the Model class
'''
from io import StringIO
import sys
from unittest import TestCase
import pytest
from pysmt import typing
from pysmt.shortcuts import Equals, Plus, Int, Symbol, Iff, GE, And, TRUE, Times, Exists
from pysmt.logics import QF_BOOL, QF_IDL, QF_LIA, QF_UFLIRA, UFLIRA, QF_LIRA
from pyvmt.environment import reset_env, get_env
from pyvmt.model import Model
from pyvmt import exceptions
from pyvmt.shortcuts import Next

class TestModel(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_variables(self):
        '''
            Tests the adding of new variables
            and the functions to determine the type of the variable
        '''
        script = Model()
        x = script.create_state_var('x', typing.INT)
        a = script.create_input_var('a', typing.BOOL)
        b = Symbol('b')

        self.assertTrue(script.is_state_variable(x))
        self.assertFalse(script.is_input_variable(x))

        self.assertFalse(script.is_state_variable(a))
        self.assertTrue(script.is_input_variable(a))

        self.assertFalse(script.is_state_variable(b))
        self.assertFalse(script.is_input_variable(b))

    def test_add_init(self):
        '''
            Tests for the add_init method
        '''
        model = Model()
        x = model.create_state_var('x', typing.INT)
        xn = model.next(x)
        a = model.create_input_var('a', typing.BOOL)

        self.assertEqual(model.get_init_constraint(), TRUE())

        # adding new init constraint
        f = Equals(x, Int(0))
        model.add_init(f)
        init_constraints = model.get_init_constraints()
        self.assertEqual(len(init_constraints), 1)
        self.assertEqual(init_constraints[0], f)

        # adding init constraint with next variable
        self.assertRaises(exceptions.UnexpectedNextError,
                          lambda: model.add_init(Equals(x, Plus(xn, Int(1)))))

        # adding init constraint with input
        self.assertRaises(exceptions.StateVariableError,
                          lambda: model.add_init(Iff(a, Equals(x, Int(10)))))

        # adding init of wrong type
        self.assertRaises(exceptions.PyvmtTypeError,
                          lambda: model.add_init(Int(1)))

        self.assertEqual(model.get_init_constraint(), f)
        f2 = GE(x, Int(0))
        model.add_init(f2)
        self.assertEqual(model.get_init_constraint(), And(f, f2))

    def test_add_trans(self):
        '''
            Tests for the add_trans method
        '''
        script = Model()
        x = script.create_state_var('x', typing.INT)

        self.assertEqual(script.get_trans_constraint(), TRUE())

        # adding new trans constraint
        f = Equals(x, Int(0))
        script.add_trans(f)
        trans_constraints = script.get_trans_constraints()
        self.assertEqual(len(trans_constraints), 1)
        self.assertEqual(trans_constraints[0], f)

        # adding trans with undeclared variable
        a = Symbol('a', typing.INT)
        self.assertRaises(exceptions.UndeclaredSymbolError,
                          lambda: script.add_trans(a))

        # adding trans of wrong type
        self.assertRaises(exceptions.PyvmtTypeError,
                          lambda: script.add_trans(Int(1)))
        self.assertEqual(script.get_trans_constraint(), f)
        f2 = GE(x, Int(0))
        script.add_trans(f2)
        self.assertEqual(script.get_trans_constraint(), And(f, f2))

    def test_add_invar(self):
        '''Tests if invars are correctly added
        '''
        model = Model()
        x = model.create_state_var('x', typing.INT)

        # adding new invar constraint
        f = Equals(x, Int(0))
        model.add_invar(f)
        self.assertEqual(model.get_trans_constraint(), And(f, model.next(f)))
        self.assertEqual(model.get_init_constraint(), f)

    def test_add_state_var(self):
        '''
            Tests for the add_state_var method
        '''
        model = Model()
        mgr = get_env().formula_manager
        x = Symbol('x')
        xn = mgr.Next(x)
        model.add_state_var(x)

        # reusing state variable
        self.assertRaises(exceptions.DuplicateDeclarationError,
                          lambda: model.add_state_var(x))

        # adding a function instead of a symbol
        f = Iff(x, xn)
        self.assertRaises(exceptions.NotSymbolError,
                          lambda: model.add_state_var(f))

    def test_add_property(self):
        '''
            Tests for the add_live_property, add_invar_property, and
            add_live_property methods
        '''
        mgr = get_env().formula_manager
        model = Model()
        x = model.create_state_var('x', typing.INT)
        f = Equals(x, Int(0))
        ltl_f = mgr.X(mgr.G(f))

        # adding new invar property
        self.assertEqual(model.add_invar_property(f, property_idx=1), 1)
        prop = model.get_property(1)
        self.assertEqual(prop.formula, f)
        self.assertEqual(model.get_invar_properties()[1], prop)
        self.assertTrue(prop.is_invar())

        # adding new live property
        self.assertEqual(model.add_live_property(f), 0)
        prop = model.get_property(0)
        self.assertEqual(prop.formula, f)
        self.assertEqual(model.get_live_properties()[0], prop)
        self.assertTrue(prop.is_live())

        # adding new LTL property
        self.assertEqual(model.add_ltl_property(ltl_f), 2)
        prop = model.get_property(2)
        self.assertEqual(prop.formula, ltl_f)
        self.assertEqual(model.get_ltl_properties()[2], prop)
        self.assertTrue(prop.is_ltl())

        # adding property with undeclared variable
        a = Symbol('a', typing.BOOL)
        self.assertRaises(exceptions.UndeclaredSymbolError,
                          lambda: model.add_live_property(a))
        self.assertRaises(exceptions.UndeclaredSymbolError,
                          lambda: model.add_invar_property(a))

        # adding property of the wrong type
        self.assertRaises(exceptions.PyvmtTypeError,
                          lambda: model.add_invar_property(Int(1)))
        self.assertRaises(exceptions.PyvmtTypeError,
                          lambda: model.add_live_property(Int(1)))
        self.assertRaises(exceptions.PyvmtTypeError,
                          lambda: model.add_ltl_property(Int(1)))

        # reusing the same index
        self.assertRaises(exceptions.DuplicatePropertyIdxError,
                          lambda: model.add_invar_property(f, property_idx=0))
        self.assertRaises(exceptions.DuplicatePropertyIdxError,
                          lambda: model.add_live_property(f, property_idx=1))
        self.assertRaises(exceptions.DuplicatePropertyIdxError,
                          lambda: model.add_ltl_property(f, property_idx=2))

        # using an invalid index
        self.assertRaises(exceptions.InvalidPropertyIdxError,
                          lambda: model.add_invar_property(f, property_idx='1'))
        self.assertRaises(exceptions.InvalidPropertyIdxError,
                          lambda: model.add_live_property(f, property_idx=-1))
        self.assertRaises(exceptions.InvalidPropertyIdxError,
                          lambda: model.add_ltl_property(f, property_idx=-1))

        all_properties = model.get_all_properties()
        self.assertEqual(len(all_properties), 3)
        self.assertEqual(all_properties[0], model.get_property(0))
        self.assertEqual(all_properties[1], model.get_property(1))
        self.assertEqual(all_properties[2], model.get_property(2))

    def test_unexpected_ltl(self):
        '''Test if using ltl in wrong parts of the model raises an exception
        '''
        model = Model()
        x = model.create_state_var('x', typing.BOOL)
        mgr = get_env().formula_manager

        ltl_f = mgr.X(x)

        self.assertRaises(exceptions.UnexpectedLtlError,
                          lambda: model.add_init(ltl_f))
        self.assertRaises(exceptions.UnexpectedLtlError,
                          lambda: model.add_trans(ltl_f))
        self.assertRaises(exceptions.UnexpectedLtlError,
                          lambda: model.add_live_property(ltl_f))
        self.assertRaises(exceptions.UnexpectedLtlError,
                          lambda: model.add_invar_property(ltl_f))

    def test_hr_printing(self):
        '''Test if the HR serialization works correctly'''
        model = Model()
        x = model.create_state_var('x', typing.INT)
        xn = model.next(x)
        model.create_input_var('a', typing.BOOL)
        model.add_init(Equals(x, Int(0)))
        model.add_trans(Equals(xn, Plus(x, Int(1))))
        model.add_invar_property(GE(x, Int(0)))

        SAMPLE_OUTPUT = '--- State variables ---\nInt x, next(x) = x\'\n\n' \
                        '--- Input variables ---\nBool a\n\n'                  \
                        '--- Init constraints ---\n(x = 0)\n\n'                \
                        '--- Trans constraints ---\n(x\' = (x + 1))\n\n'    \
                        '--- Properties ---\n0) invar prop: (0 <= x)\n'

        self.assertEqual(str(model), SAMPLE_OUTPUT)

    def test_serialize_dag(self):
        '''Test if the VMT dag serialization works correctly'''
        mgr = get_env().formula_manager
        model = Model()
        x = model.create_state_var('x', typing.INT)
        xn = model.next(x)
        model.create_input_var('a', typing.BOOL)
        model.add_init(Equals(x, Int(0)))
        model.add_trans(Equals(xn, Plus(x, Int(1))))
        model.add_invar_property(GE(x, Int(0)))
        model.add_ltl_property(mgr.U(GE(xn, x), GE(x, Int(0))))

        SAMPLE_OUTPUT = '(declare-fun a () Bool)\n'\
            '(declare-fun x () Int)\n'\
            '(declare-fun x.__next0 () Int)\n'\
            '(define-fun next0 () Int (! x :next x.__next0))\n'\
            '(define-fun init0 () Bool (let ((.def_0 (= x 0))) '\
                '(! .def_0 :init true)))\n'\
            '(define-fun trans0 () Bool (let ((.def_0 (+ x 1))) '\
                '(let ((.def_1 (= x.__next0 .def_0))) (! .def_1 :trans true))))\n'\
            '(define-fun invar-property0 () Bool (let ((.def_0 (<= 0 x))) '\
                '(! .def_0 :invar-property 0)))\n'\
            '(define-fun ltl-property0 () Bool (let ((.def_0 (<= 0 x))) '\
                '(let ((.def_1 (<= x x.__next0))) (let ((.def_2 (ltl.U .def_1 .def_0))) '\
                '(! .def_2 :ltl-property 1)))))\n'\
            '(assert true)\n'

        result = StringIO()
        model.serialize(result)
        self.assertEqual(result.getvalue(), SAMPLE_OUTPUT)

    def test_serialize(self):
        '''Test if the VMT serialization works correctly'''
        mgr = get_env().formula_manager
        model = Model()
        x = model.create_state_var('x', typing.INT)
        xn = model.next(x)
        model.create_input_var('a', typing.BV16)
        model.add_init(Equals(x, Int(0)))
        model.add_trans(Equals(xn, Plus(x, Int(1))))
        model.add_invar_property(GE(x, Int(0)))
        model.add_ltl_property(mgr.U(GE(xn, x), GE(x, Int(0))))

        SAMPLE_OUTPUT = '(declare-fun a () (_ BitVec 16))\n'\
            '(declare-fun x () Int)\n'\
            '(declare-fun x.__next0 () Int)\n'\
            '(define-fun next0 () Int (! x :next x.__next0))\n'\
            '(define-fun init0 () Bool (! (= x 0) :init true))\n'\
            '(define-fun trans0 () Bool (! (= x.__next0 (+ x 1)) :trans true))\n'\
            '(define-fun invar-property0 () Bool (! (<= 0 x) :invar-property 0))\n'\
            '(define-fun ltl-property0 () Bool (! (ltl.U (<= x x.__next0) (<= 0 x)) '\
                ':ltl-property 1))\n'\
            '(assert true)\n'

        result = StringIO()
        model.serialize(result, daggify=False)
        self.assertEqual(result.getvalue(), SAMPLE_OUTPUT)

    def test_get_logic(self):
        '''Test if the get_logic function works correctly
        '''
        model = Model()
        x = model.create_state_var('x', typing.BOOL)
        self.assertEqual(model.get_logic(), QF_BOOL)

        y = model.create_state_var('y', typing.INT)
        self.assertEqual(model.get_logic(), QF_IDL)

        model.add_init(Equals(Times(y, Int(2)), Int(4)))
        self.assertEqual(model.get_logic(), QF_LIA)

        model.create_state_var('z', typing.REAL)
        self.assertEqual(model.get_logic(), QF_LIRA)
        self.assertEqual(model.get_logic([Exists([y], And(Next(x), Equals(y, Int(0))))]), UFLIRA)

        model.add_trans(Exists([y], And(Next(x), Equals(y, Int(0)))))
        self.assertEqual(model.get_logic(), UFLIRA)

if __name__ == '__main__':
    pytest.main(sys.argv)
