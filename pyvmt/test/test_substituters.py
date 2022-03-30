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
import sys
from unittest import TestCase
import pytest
from pysmt import typing
from pysmt.shortcuts import Iff, ForAll, Exists, Symbol, Not
from pyvmt.environment import reset_env, get_env
from pyvmt.model import Model
from pyvmt.substituters import VmtLibSubstituter

class TestSubstituters(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_bound(self):
        '''
            bound variables should not be replaced
        '''
        model = Model()
        a = model.create_state_var('a', typing.BOOL)
        b = model.create_state_var('b', typing.BOOL)

        # symbols for substitution
        an = Symbol('a.next')
        bn = Symbol('b.next')

        f1 = ForAll([a], model.next(Iff(a, b)))
        f2 = model.next(Exists([a], Iff(a, b)))

        f1_sub = ForAll([a], Iff(a, bn))
        f2_sub = Exists([a], Iff(a, bn))

        substituter = VmtLibSubstituter({a: an, b: bn})
        self.assertEqual(substituter.replace(f1), f1_sub)
        self.assertEqual(substituter.replace(f2), f2_sub)

    def test_vmtlib_substituter(self):
        '''Test if VmtLibSubstituter correctly replaces the unsupported VMT-LIB operators
        '''
        substituter = VmtLibSubstituter({})
        mgr = get_env().formula_manager
        x = Symbol('x')
        y = Symbol('y')
        f = mgr.R(x, y)
        f_res = Not(mgr.U(Not(x), Not(y)))

        f2 = mgr.R(x, f)
        f2_res = Not(mgr.U(Not(x), Not(f_res)))
        self.assertEqual(substituter.replace(f), f_res)
        self.assertEqual(substituter.replace(f2), f2_res)

if __name__ == '__main__':
    pytest.main(sys.argv)
