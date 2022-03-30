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
'''Wrapper for ic3ia solver
'''

import os
from subprocess import run, CalledProcessError
from io import StringIO
from pathlib import Path
from enum import Enum
import re
from pysmt.smtlib.parser.parser import Tokenizer, SmtLibParser
from pyvmt.solvers.solver import Solver, Result, Options
from pyvmt import exceptions
from pyvmt.properties import LIVE_PROPERTY, INVAR_PROPERTY, LTL_PROPERTY, VmtProperty
from pyvmt.solvers.traces import Trace

# the possible results from witness computation
class _Ic3iaWitnessRes(Enum):
    ERROR = 'ERROR computing witness'
    COUNTEREXAMPLE = 'counterexample'
    INVARIANT = 'invariant'

class Ic3iaSolver(Solver):
    '''Class that wraps the Ic3ia solver
    '''

    def __init__(self, model):
        super().__init__(model)
        self.options = Ic3iaOptions()

        # find the executable
        env_var = 'PYVMT_IC3IA_PATH'
        solver_path = os.getenv(env_var)
        if solver_path is None:
            raise exceptions.SolverNotConfiguredError('Ic3ia', env_var)
        self._solver_path = Path(solver_path)
        if not self._solver_path.is_file():
            raise exceptions.SolverNotFoundError(
                f"Ic3ia executable not found in {self._solver_path}")

    def check_properties(self):
        results_map = self.check_invar_properties()
        results_map.update(self.check_live_properties())
        results_map.update(self.check_ltl_properties())
        return results_map

    def check_property_idx(self, property_idx):
        prop = self.model.get_property(property_idx)
        return self.check_property(prop.prop_type, prop.formula)

    def check_invar_properties(self):
        results_map = {}
        for property_idx, prop in self.model.get_invar_properties().items():
            results_map[property_idx] = self.check_invar_property(prop.formula)
        return results_map

    def check_invar_property(self, formula):
        return self.check_property(INVAR_PROPERTY, formula)

    def check_live_properties(self):
        results_map = {}
        for property_idx, prop in self.model.get_live_properties().items():
            results_map[property_idx] = self.check_live_property(prop.formula)
        return results_map

    def check_live_property(self, formula):
        return self.check_property(LIVE_PROPERTY, formula)

    def check_ltl_properties(self):
        results_map = {}
        for property_idx, prop in self.model.get_ltl_properties().items():
            results_map[property_idx] = self.check_ltl_property(prop.formula)
        return results_map

    def check_ltl_property(self, formula):
        return self.check_property(LTL_PROPERTY, formula)

    def check_property(self, property_type, formula):
        self.options.set_property_index(0)
        self.options.set_print_witness()
        args = [self._solver_path]
        args.extend(self.options.to_array())

        model_stream = StringIO()
        prop = VmtProperty(property_type, formula)
        self.model.serialize(model_stream, properties={ 0: prop })

        solver_in = model_stream.getvalue()

        try:
            # this may raise a CalledProcessError if the subprocess
            # returns a non-zero returncode since check is True
            solver = run(args, capture_output=True, input=solver_in, text=True,
                check=True)
        except CalledProcessError as err:
            raise exceptions.UnknownSolverAnswerError(
                f"Solver returned code {err.returncode}") from err
        solver_out = solver.stdout
        return self._read_result(StringIO(solver_out))

    def _read_result(self, solver_out):
        # read the result from the solver output
        try:
            res_type = _Ic3iaWitnessRes(solver_out.readline().strip())
        except ValueError as err:
            raise exceptions.UnknownSolverAnswerError(
                f"Expected witness type, {res_type} found") from err
        #TODO handle different results
        trace = None
        if res_type == _Ic3iaWitnessRes.COUNTEREXAMPLE:
            trace = self._read_counterexample(solver_out)
        elif res_type == _Ic3iaWitnessRes.INVARIANT:
            pass
        elif res_type == _Ic3iaWitnessRes.ERROR:
            pass
        last_line = solver_out.readlines()[-1].strip()

        if last_line not in ('safe', 'unsafe'):
            raise exceptions.UnknownSolverAnswerError(
                f"Solver returned {last_line}")

        return Ic3iaResult(last_line == 'safe', trace=trace)

    def _read_counterexample(self, solver_out):
        # the result is a trace, start reading the result
        step_re = re.compile(r'^;; step (\d+)\n$')

        trace = Trace('counterexample', self.model.get_state_vars(), env=self.model.get_env())

        parser = SmtLibParser()
        env = self.model.get_env()
        mgr = env.formula_manager

        parser.cache.update(mgr.symbols)
        # TODO check if interactive should be True or False
        tokens = Tokenizer(solver_out, interactive=True)
        while True:
            cur = solver_out.readline()
            if step_re.match(cur) is None:
                break
            full_assignment = parser.get_expression(tokens)
            assignments = {}

            if full_assignment.is_and():
                formulae = full_assignment.args()
            else:
                # a single assignment maybe have been returned
                formulae = [full_assignment]
            for formula in formulae:
                if formula.is_symbol():
                    # asserted symbol
                    symbol = formula
                    value = mgr.TRUE()
                elif formula.is_not():
                    # negated symbol
                    symbol = formula.arg(0)
                    value = mgr.FALSE()
                elif formula.is_equals():
                    # assignment
                    symbol = formula.arg(0)
                    value = formula.arg(1)
                else:
                    raise exceptions.UnknownSolverAnswerError(
                        "Counterexample assignment not recognized")
                assignments[symbol] = value

            if not solver_out.readline() == '\n':
                raise exceptions.UnknownSolverAnswerError(
                    "Expected to read newline after assignment")
            trace.create_step(assignments)
        return trace

class Ic3iaOptions(Options):
    '''
        The options to use while running Ic3ia solver
    '''

    # start options

    def set_property_index(self, value):
        '''-n N : work on property of index N (default 0)

        :param value: The property index to work on
        :type value: int
        '''
        self._options['n'] = value

    def set_verbosity(self, value):
        '''-v N : set verbosity level

        :param value: The new value for verbosity
        :type value: int
        '''
        self._options['v'] = value

    def set_dump_smt_queries(self, value):
        '''-t NAME : dump SMT queries into NAME.main.smt2 and NAME.itp.smt2

        :param value: The property index to work on
        :type value: str
        '''
        self._options['t'] = value

    def set_random_seed(self, value):
        '''-r VAL : set random seed to VAL (0 to disable [default])

        :param value: The random seed value
        :type value: int
        '''
        self._options['r'] = value

    def set_inc_ref(self, value):
        '''-inc-ref B : use incremental refinement

        :param value: The value for B
        :type value: int
        '''
        self._options['inc-ref'] = value

    def set_live_ref_maxiter(self, value):
        '''-live-ref-maxiter N : max number of unrollings when refining liveness properites

        :param value: the max number of unrollings
        :type value: int
        '''
        self._options['live-ref-maxiter'] = value

    def set_live_ref_ranking(self, value):
        '''-live-ref-ranking B : use ranking functions for  refinement for liveness properties

        :param value: the max number of unrollings
        :type value: int
        '''
        self._options['live-ref-ranking'] = value

    def set_live_ref_eager(self, value):
        '''-live-ref-eager B : use eager refinement strategy for liveness properties

        :param value: the value for B
        :type value: int
        '''
        self._options['live-ref-eager'] = value

    def set_live_ref_templates(self, value):
        '''-live-ref-templates B : enable template-based refinement strategy for liveness properties

        :param value: the value for B
        :type value: int
        '''
        self._options['live-ref-templates'] = value

    def set_live_no_cex(self, value):
        '''-live-no-cex B : do not check for concrete counterexample in liveness refinement

        :param value: the value for B
        :type value: int
        '''
        self._options['live-no-cex'] = value

    def set_live_bmc_cex(self, value):
        '''-live-bmc-cex B : use BMC to check for concrete counterexample
        in liveness refinementrefinement strategy for liveness properties

        :param value: the value for B
        :type value: int
        '''
        self._options['live-bmc-cex'] = value

    def set_live_klive_progress(self, value):
        '''-live-klive-progress B : fall back to k-liveness when liveness refinement fails

        :param value: the value for B
        :type value: int
        '''
        self._options['live-klive-progress'] = value

    def set_live_klive_start(self, value):
        '''-live-klive-start N : starting value for k-liveness counter

        :param value: the starting value for the counter
        :type value: int
        '''
        self._options['live-klive-start'] = value

    def set_live_klive_only(self, value):
        '''-live-klive-only B : use only k-liveness for handling liveness properties

        :param value: the value for B
        :type value: int
        '''
        self._options['live-klive-only'] = value

    def set_live_klive_nondet(self, value):
        '''-live-klive-nondet B : use a non-deterministic encoding
        for increasing the k-liveness counter

        :param value: the value for B
        :type value: int
        '''
        self._options['live-klive-nondet'] = value

    def set_live_klive_counter(self, value):
        '''-live-klive-counter B : use an integer counter
        instead of an absorbing circuit for k-liveness

        :param value: the value for B
        :type value: int
        '''
        self._options['live-klive-counter'] = value

    def set_max_bmc_k(self, value):
        '''-bmc-k N : max k value for BMC

        :param value: the max value for k
        :type value: int
        '''
        self._options['bmc-k'] = value

    def set_check_witness(self, value):
        '''-check-witness B : check the correctness of witnesses

        :param value: the value for B
        :type value: int
        '''
        self._options['bmc-k'] = value

    def set_witness_check_script(self, value):
        '''-witness-check-script OUT : generate a witness check script in OUT

        :param value: the path for the output
        :type value: str
        '''
        self._options['witness-check-script'] = value

    def set_ltl_single_fairness_sorted(self, value):
        '''-ltl-single-fairness-sorted B : if true, force a fixed order
        for recording the fairness contiditons when combining multiple
        fairness constraints (forced to true when -check-witness is on).

        :param value: the value for B
        :type value: int
        '''
        self._options['ltl-single-fairness-sorted'] = value

    def set_solver_reset_interval(self, value):
        '''-solver-reset-interval N : reset interval for the SMT solver in the IC3 engine.

        :param value: the reset interval
        :type value: int
        '''
        self._options['solver-reset-interval'] = value

    def set_solver_approx(self, value):
        '''-solver-approx B : use approximate SMT queries in IC3.

        :param value: the value for B
        :type value: int
        '''
        self._options['solver-approx'] = value

    # end options
    # start flags

    def set_print_witness(self, value = True):
        '''-w : print witness

        :param value: False to reset the flag, defaults to True
        :type value: bool, optional
        '''
        self._set_flag('w', value)

    def set_do_not_use_initial_predicates(self, value = True):
        '''-p : do not use initial predicates (if any)

        :param value: False to reset the flag, defaults to True
        :type value: bool, optional
        '''
        self._set_flag('p', value)

    def set_stack_based_proof_obligation_management(self, value = True):
        '''-s : stack-based proof obligation management

        :param value: False to reset the flag, defaults to True
        :type value: bool, optional
        '''
        self._set_flag('s', value)

    def set_disable_predicate_minimization_in_refinement(self, value = True):
        '''-m : disable predicate minimization in refinement

        :param value: False to reset the flag, defaults to True
        :type value: bool, optional
        '''
        self._set_flag('m', value)

    def set_enable_predecessor_generalization(self, value = True):
        '''-g : enable predecessor generalization

        :param value: False to reset the flag, defaults to True
        :type value: bool, optional
        '''
        self._set_flag('g', value)

    def set_use_bmc(self, value = True):
        '''-bmc : use BMC instead of IC3

        :param value: False to reset the flag, defaults to True
        :type value: bool, optional
        '''
        self._set_flag('bmc', value)

    # end flags

class Ic3iaResult(Result):
    '''
        Class to store an ic3ia result
    '''

    def __init__(self, is_safe, trace=None):
        self._is_safe = is_safe
        self._trace = trace

    def is_safe(self):
        return self._is_safe

    def get_trace(self):
        return self._trace

    def has_trace(self):
        return self._trace is not None
