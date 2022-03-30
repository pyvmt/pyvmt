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
    Module to test renaming of models
'''
import sys
from unittest import TestCase
import pytest
from pysmt import typing
from pysmt.shortcuts import Symbol, Equals, Int, ForAll, Exists, And, Iff
from pyvmt.environment import reset_env
from pyvmt.model import Model
from pyvmt.renamer import rename, add_prefix, add_suffix, replace_prefix, replace_suffix
from pyvmt import exceptions

class TestRenamer(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_prefixes(self):
        '''test the add prefix and replace prefix function'''
        model = Model()
        a = model.create_state_var('left.a', typing.INT)
        x = model.create_input_var('left.x',typing.REAL)
        new_model = add_prefix(model, 'right.')

        state_vars = set(new_model.get_state_vars())
        input_vars = set(new_model.get_input_vars())

        self.assertEqual(len(state_vars), 1)
        self.assertEqual(len(input_vars), 1)

        state_var = Symbol(f'right.{a.symbol_name()}', a.symbol_type())
        self.assertIn(state_var, state_vars)
        self.assertIn(Symbol(f'right.{x.symbol_name()}', x.symbol_type()), input_vars)

        new_model = replace_prefix(model, 'left.', 'right.')
        state_vars = set(new_model.get_state_vars())
        input_vars = set(new_model.get_input_vars())

        self.assertEqual(len(state_vars), 1)
        self.assertEqual(len(input_vars), 1)

        state_var = Symbol('right.a', a.symbol_type())
        self.assertIn(state_var, state_vars)
        self.assertIn(Symbol('right.x', x.symbol_type()), input_vars)

    def test_suffixes(self):
        '''test the add suffix and replace suffix function'''
        model = Model()
        a = model.create_state_var('a.left', typing.INT)
        x = model.create_input_var('x.left',typing.REAL)
        new_model = add_suffix(model, '.right')

        state_vars = set(new_model.get_state_vars())
        input_vars = set(new_model.get_input_vars())

        self.assertEqual(len(state_vars), 1)
        self.assertEqual(len(input_vars), 1)

        state_var = Symbol(f'{a.symbol_name()}.right', a.symbol_type())
        self.assertIn(state_var, state_vars)
        self.assertIn(Symbol(f'{x.symbol_name()}.right', x.symbol_type()), input_vars)

        new_model = replace_suffix(model, '.left', '.right')
        state_vars = set(new_model.get_state_vars())
        input_vars = set(new_model.get_input_vars())

        self.assertEqual(len(state_vars), 1)
        self.assertEqual(len(input_vars), 1)

        state_var = Symbol('a.right', a.symbol_type())
        self.assertIn(state_var, state_vars)
        self.assertIn(Symbol('x.right', x.symbol_type()), input_vars)

    def test_strict(self):
        '''test if the replacement function correctly raises the exception
            while checking a missing prefix or suffix
        '''
        model = Model()
        a = model.create_state_var('a', typing.INT)
        x = model.create_input_var('left.x.foo',typing.REAL)

        self.assertRaises(exceptions.IncorrectSymbolNameError,
            lambda: replace_prefix(model, 'left.', 'right.'))
        self.assertRaises(exceptions.IncorrectSymbolNameError,
            lambda: replace_suffix(model, '.foo', '.bar'))
        new_model = replace_prefix(model, 'left.', 'right.', strict=False)
        state_vars = set(new_model.get_state_vars())
        input_vars = set(new_model.get_input_vars())

        self.assertEqual(len(state_vars), 1)
        self.assertEqual(len(input_vars), 1)

        state_var = Symbol('a', a.symbol_type())
        self.assertIn(state_var, state_vars)
        self.assertIn(Symbol('right.x.foo', x.symbol_type()), input_vars)

        new_model = replace_suffix(model, '.foo', '.bar', strict=False)
        state_vars = set(new_model.get_state_vars())
        input_vars = set(new_model.get_input_vars())

        self.assertEqual(len(state_vars), 1)
        self.assertEqual(len(input_vars), 1)

        state_var = Symbol('a', a.symbol_type())
        self.assertIn(state_var, state_vars)
        self.assertIn(Symbol('left.x.bar', x.symbol_type()), input_vars)

    def test_replace(self):
        '''Test the replace function with a custom lambda'''
        model = Model()
        a = model.create_state_var('a', typing.INT)
        x = model.create_input_var('x',typing.INT)
        model.add_init(Equals(a, Int(0)))
        model.add_trans(Equals(a, model.next(a)))
        model.add_invar_property(Equals(x, a))
        model.add_live_property(Equals(x, model.next(a)))
        new_model = rename(model, lambda x: f'foo.{x}.bar')

        new_a = Symbol('foo.a.bar', typing.INT)
        new_an = model.next(new_a)
        new_x = Symbol('foo.x.bar', typing.INT)

        new_trans = new_model.get_trans_constraints()
        new_init = new_model.get_init_constraints()
        new_live = new_model.get_live_properties()
        new_invar = new_model.get_invar_properties()
        self.assertEqual(len(new_trans), 1)
        self.assertEqual(len(new_init), 1)
        self.assertEqual(len(new_live), 1)
        self.assertEqual(len(new_invar), 1)
        self.assertEqual(new_trans[0], Equals(new_a, new_an))
        self.assertEqual(new_init[0], Equals(new_a, Int(0)))
        self.assertEqual(new_invar[0].formula, Equals(new_x, new_a))
        self.assertEqual(new_live[1].formula, Equals(new_x, new_an))

    def test_invalid_callback(self):
        '''Test if an exception is raised if the renamer
        return type is invalid'''
        model = Model()
        model.create_state_var('a', typing.INT)
        invalid_callback = lambda x: 1
        self.assertRaises(exceptions.PyvmtTypeError,
            lambda: rename(model, invalid_callback))

    def test_bound_variables(self):
        '''Test if the renamer avoids renaming bound variables like quantifiers
        '''
        model = Model()
        x = model.create_input_var('x', typing.INT)
        a = model.create_state_var('a', typing.BOOL)
        f = And(Iff(a, model.next(a)), Equals(x, Int(0)))
        model.add_invar_property(ForAll([x], f))
        model.add_live_property(Exists([x, a], f))

        new_model = add_prefix(model, 'foo.')
        new_a = new_model.get_state_vars()[0]
        new_invar = And(Iff(new_a, model.next(new_a)), Equals(x, Int(0)))
        new_live = And(Iff(a, model.next(a)), Equals(x, Int(0)))

        self.assertEqual(new_model.get_property(0).formula,
            ForAll([x], new_invar))
        self.assertEqual(new_model.get_property(1).formula,
            Exists([x, a], new_live))

if __name__ == '__main__':
    pytest.main(sys.argv)
