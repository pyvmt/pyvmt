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
    Module to test the properties module
'''
import sys
from unittest import TestCase
import pytest
from pysmt import typing
from pysmt.shortcuts import Symbol, And
from pyvmt.environment import reset_env, get_env
from pyvmt import exceptions
from pyvmt.properties import INVAR_PROPERTY, LIVE_PROPERTY, LTL_PROPERTY, VmtProperty

class TestProperties(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_invalid_property_type(self):
        '''Test if the InvalidPropertyTypeError is raised correctly'''
        x = Symbol('x')
        self.assertRaises(exceptions.InvalidPropertyTypeError,
            lambda: VmtProperty('foo', x))
        # the following lines should not raise an exception
        VmtProperty(INVAR_PROPERTY, x)
        VmtProperty(LIVE_PROPERTY, x)
        VmtProperty(LTL_PROPERTY, x)

    def test_type_error(self):
        '''Test if an exception is raised if the created formula type is not boolean'''
        x = Symbol('x', typing.INT)
        self.assertRaises(exceptions.PyvmtTypeError,
            lambda: VmtProperty(INVAR_PROPERTY, x))
        self.assertRaises(exceptions.PyvmtTypeError,
            lambda: VmtProperty(LIVE_PROPERTY, x))
        self.assertRaises(exceptions.PyvmtTypeError,
            lambda: VmtProperty(LTL_PROPERTY, x))

    def test_unexpected_ltl(self):
        '''Test if an exception is raised if a property which isn't an LTL property
        contains LTL operators'''
        x = Symbol('x')
        mgr = get_env().formula_manager
        ltlf = mgr.X(x)
        self.assertRaises(exceptions.UnexpectedLtlError,
            lambda: VmtProperty(INVAR_PROPERTY, ltlf))
        self.assertRaises(exceptions.UnexpectedLtlError,
            lambda: VmtProperty(LIVE_PROPERTY, ltlf))
        # the following line should not raise an exception
        VmtProperty(LTL_PROPERTY, ltlf)

    def test_property_str(self):
        '''Test if the property is correctly formatted as a string'''
        x = Symbol('x')
        y = Symbol('y')
        mgr = get_env().formula_manager
        f = And(x, y)
        ltlf = mgr.X(f)
        invar_prop = VmtProperty(INVAR_PROPERTY, f)
        live_prop = VmtProperty(LIVE_PROPERTY, f)
        ltl_prop = VmtProperty(LTL_PROPERTY, ltlf)
        self.assertEqual(str(invar_prop), 'invar prop: (x & y)')
        self.assertEqual(str(live_prop), 'live prop: (x & y)')
        self.assertEqual(str(ltl_prop), 'ltl prop: (X (x & y))')

    def test_property_types(self):
        '''Test if the property type check correctly work'''
        x = Symbol('x')
        mgr = get_env().formula_manager
        ltlf = mgr.X(x)
        invar_prop = VmtProperty(INVAR_PROPERTY, x)
        live_prop = VmtProperty(LIVE_PROPERTY, x)
        ltl_prop = VmtProperty(LTL_PROPERTY, ltlf)

        self.assertTrue(invar_prop.is_invar())
        self.assertFalse(invar_prop.is_live())
        self.assertFalse(invar_prop.is_ltl())

        self.assertFalse(live_prop.is_invar())
        self.assertTrue(live_prop.is_live())
        self.assertFalse(live_prop.is_ltl())

        self.assertFalse(ltl_prop.is_invar())
        self.assertFalse(ltl_prop.is_live())
        self.assertTrue(ltl_prop.is_ltl())

if __name__ == '__main__':
    pytest.main(sys.argv)
