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
    Module to test the composer module
'''
import sys
from unittest import TestCase
import pytest
from pysmt import typing
from pysmt.shortcuts import Equals, Plus, Int, Iff, Times, Not, GT
from pyvmt.environment import reset_env, Environment
from pyvmt.model import Model
from pyvmt import exceptions
from pyvmt.composer import compose

class TestComposer(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_mismatched_environment(self):
        '''Test if an exception is raised when composing models
        with different environments'''
        model_a = Model()
        model_b = Model(Environment())
        self.assertRaises(exceptions.MismatchedEnvironmentError,
            lambda: compose(model_a, model_b))

    def test_compose(self):
        '''Test the composition of two models'''
        model_a = Model()
        mgr = model_a.get_env().formula_manager

        a = model_a.create_state_var('a', typing.INT)
        b = model_a.create_state_var('b', typing.BOOL)
        c = model_a.create_input_var('c', typing.INT)

        all_init = [
            b,
            Equals(a, Int(5))
        ]
        all_trans = [
            Iff(b, Equals(mgr.Next(a), Plus(a, Int(1)))),
            Iff(mgr.Next(b), Not(b)),
            Iff(b, Equals(mgr.Next(c), Times(c, Int(2))))
        ]
        all_invar_prop = {
            0: GT(a, Int(5))
        }
        all_live_prop = {
            1: GT(c, Int(25))
        }

        model_a.add_init(all_init[0])
        model_a.add_init(all_init[1])
        model_a.add_trans(all_trans[0])
        model_a.add_trans(all_trans[1])
        model_a.add_invar_property(all_invar_prop[0], property_idx=0)

        model_b = Model()
        x = model_b.create_input_var('x', typing.REAL)
        model_b.add_input_var(b)
        model_b.add_state_var(c)
        model_b.add_trans(all_trans[2])
        model_b.add_live_property(all_live_prop[1], property_idx=1)

        model = compose(model_a, model_b)

        # check that the state variables are correct
        self.assertTrue(model.is_state_variable(a))
        self.assertTrue(model.is_state_variable(b))
        self.assertTrue(model.is_state_variable(c))

        # check that the inputs are correct
        self.assertTrue(model.is_input_variable(x))

        # check that there are no extra variables
        self.assertEqual(len(model.get_state_vars()), 3)
        self.assertEqual(len(model.get_input_vars()), 1)

        # check that the constraints are the same
        new_all_init = set(model.get_init_constraints())
        new_all_trans = set(model.get_trans_constraints())
        self.assertEqual(len(new_all_init.symmetric_difference(set(all_init))), 0)
        self.assertEqual(len(new_all_trans.symmetric_difference(set(all_trans))), 0)

        # check that the properties are the same
        new_all_invar_prop = model.get_invar_properties()
        new_all_live_prop = model.get_live_properties()
        self.assertCountEqual(new_all_invar_prop, all_invar_prop)
        self.assertCountEqual(new_all_live_prop, all_live_prop)
        self.assertEqual(model.get_property(0).formula, all_invar_prop[0])
        self.assertEqual(model.get_property(1).formula, all_live_prop[1])

if __name__ == '__main__':
    pytest.main(sys.argv)
