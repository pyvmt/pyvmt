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
    Module to test the traces module
'''

import sys
from unittest import TestCase
import pytest
from pysmt import typing
from pysmt.shortcuts import And, Plus, Equals, Not, Int, TRUE, FALSE
from pyvmt.environment import reset_env, get_env
from pyvmt.model import Model
from pyvmt import exceptions
from pyvmt.solvers.traces import Trace

def get_example_finite_trace(with_loopback=True, return_model=False):
    '''An example finite trace with a model and a few steps'''
    model = Model()
    x = model.create_state_var('x', typing.INT)
    y = model.create_state_var('y', typing.BOOL)
    trace = Trace('counterexample', model.get_state_vars(), env=model.get_env())
    trace.create_step({ x: Int(0), y: TRUE() })
    trace.create_step({ x: Int(1), y: FALSE() }, is_loopback=with_loopback)
    trace.create_step({ x: Int(2), y: FALSE() })
    trace.create_step({ x: Int(3), y: TRUE() })
    if return_model:
        return model, trace
    return trace

class TestTraces(TestCase):
    '''
        Class containing tests
    '''

    def setUp(self):
        reset_env()

    def test_loopback_step(self):
        '''Test all the functions regarding the loopback step
        '''
        trace = get_example_finite_trace()
        self.assertTrue(trace.has_loopback_step())
        self.assertEqual(trace.get_loopback_step_idx(), 1)
        mgr = get_env().formula_manager

        loopback_step = trace.get_loopback_step()
        assignments = loopback_step.get_assignments()
        self.assertEqual(assignments[mgr.get_symbol('x')], Int(1))
        self.assertEqual(assignments[mgr.get_symbol('y')], FALSE())
        self.assertTrue(trace.has_loopback_step())
        self.assertRaises(exceptions.DuplicateLoopbackStepError,
            lambda: trace.create_step({}, is_loopback=True))

        trace = get_example_finite_trace(with_loopback=False)
        self.assertFalse(trace.has_loopback_step())
        self.assertRaises(exceptions.MissingLoopbackStepError,
            trace.get_loopback_step)

    def test_steps_count(self):
        '''Test the steps count function
        '''
        trace = get_example_finite_trace()
        self.assertEqual(trace.steps_count(), 4)
        self.assertEqual(len(trace.get_steps()), 4)

    def test_different_variables(self):
        '''Test the functions for computing sets of different variables
        '''
        trace = get_example_finite_trace()
        mgr = get_env().formula_manager
        x = mgr.get_symbol('x')
        y = mgr.get_symbol('y')
        steps = trace.get_steps()
        self.assertSetEqual(set([x]), steps[1].get_different_variables(steps[2]))
        self.assertSetEqual(set([x, y]), steps[0].get_different_variables(steps[2]))
        self.assertSetEqual(set([x]), steps[1].get_changing_variables())
        self.assertSetEqual(set([x, y]), steps[1].get_changed_variables())

    def test_adj_steps(self):
        '''Test the function for getting and checking adjacent steps
        '''
        trace = get_example_finite_trace()
        steps = trace.get_steps()
        for step in steps:
            self.assertTrue(step.has_next_step())
        self.assertFalse(steps[0].has_prev_step())
        for step in steps[1:]:
            self.assertTrue(step.has_prev_step())
        self.assertEqual(steps[3].get_next_step(), steps[1])
        self.assertEqual(steps[3].get_prev_step(), steps[2])

        trace = get_example_finite_trace(with_loopback=False)
        steps = trace.get_steps()
        self.assertFalse(steps[3].has_next_step())

        self.assertRaises(exceptions.TraceStepNotFoundError,
            steps[3].get_next_step)
        self.assertRaises(exceptions.TraceStepNotFoundError,
            steps[0].get_prev_step)

    def test_assignments(self):
        '''Test the functoins to get assignments from the steps
        '''
        trace = get_example_finite_trace()
        mgr = get_env().formula_manager
        x = mgr.get_symbol('x')
        y = mgr.get_symbol('y')
        steps = trace.get_steps()
        self.assertDictEqual(steps[0].get_assignments(), { x: Int(0), y: TRUE() })
        self.assertDictEqual(steps[1].get_assignments(), { x: Int(1), y: FALSE() })
        self.assertEqual(steps[1].get_assignment(x), Int(1))
        self.assertEqual(steps[1].get_assignment(y), FALSE())

    def test_evaluate_formula(self):
        '''Test the evaluate_formula function
        '''
        model, trace = get_example_finite_trace(return_model=True)
        mgr = get_env().formula_manager
        x = mgr.get_symbol('x')
        y = mgr.get_symbol('y')
        steps = trace.get_steps()
        self.assertEqual(steps[1].evaluate_formula(Plus(x, model.next(x))), Int(3))
        self.assertEqual(steps[3].evaluate_formula(And(y, Equals(model.next(x), Int(1)))), TRUE())

        extra_symbol = mgr.Symbol('extra_symbol')
        self.assertRaises(exceptions.UnexpectedNextError,
            lambda: steps[1].evaluate_formula(model.next(extra_symbol)))

    def test_formula(self):
        '''Test if the functions to retrieve the formula from a step work correctly
        '''
        trace = get_example_finite_trace()
        mgr = get_env().formula_manager
        x = mgr.get_symbol('x')
        y = mgr.get_symbol('y')
        steps = trace.get_steps()
        self.assertEqual(steps[0].get_formula(), And(Equals(x, Int(0)), y))
        self.assertEqual(steps[1].get_formula(), And(Equals(x, Int(1)), Not(y)))
        self.assertEqual(steps[0].serialize_to_string(), 
            '(define-fun step-0 () Bool (and (= x 0) y))')
        self.assertEqual(steps[1].serialize_to_string(),
            '(define-fun loopback-step-1 () Bool (and (= x 1) (not y)))')

if __name__ == '__main__':
    pytest.main(sys.argv)
