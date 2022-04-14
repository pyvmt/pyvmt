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
'''Wrapper for euforia solver
'''

import os
from subprocess import run, CalledProcessError
from io import StringIO
from pathlib import Path
import re
import tempfile
from pysmt.smtlib.parser.parser import SmtLibParser
from pysmt.logics import QF_AUFBV
from pyvmt.solvers.solver import Solver, Result, Options
from pyvmt import exceptions
from pyvmt.properties import LIVE_PROPERTY, INVAR_PROPERTY, LTL_PROPERTY, VmtProperty
from pyvmt.solvers.traces import Trace

class EuforiaSolver(Solver):
    '''Class that wraps the Euforia solver.

    Only Invar properties are supported by this solver, calling the
    check_properties function will return only those properties.

    The solver only supports Boolean and BitVector types.
    '''

    def __init__(self, model):
        super().__init__(model)
        self.options = EuforiaOptions()

        # find the executable
        env_var = 'PYVMT_EUFORIA_PATH'
        solver_path = os.getenv(env_var)
        if solver_path is None:
            raise exceptions.SolverNotConfiguredError('EUForia', env_var)
        self._solver_path = Path(solver_path)
        if not self._solver_path.is_file():
            raise exceptions.SolverNotFoundError(
                f"EUForia executable not found in {self._solver_path}")
        # check that the logic is supported by the solver
        if not self.supports_logic(self.model.get_logic()):
            raise exceptions.NoLogicAvailableError(
                "The model's logic is not supported by the solver")

    def check_properties(self):
        '''Only Invar properties are supported by this solver, this function
        will return only the results related to invar properties'''
        return self.check_invar_properties()

    def check_property_idx(self, property_idx):
        prop = self.model.get_property(property_idx)
        return self.check_property(prop.prop_type, prop.formula)

    def check_invar_properties(self):
        results_map = {}
        for property_idx, prop in self.model.get_invar_properties().items():
            results_map[property_idx] = self.check_invar_property(prop.formula)
        return results_map

    def check_invar_property(self, formula):
        # check that the logic is supported by the solver
        if not self.supports_logic(self.model.get_logic(extra_formulae=[formula]),
            options=self.options):
            raise exceptions.NoLogicAvailableError(
                "This logic is not supported by the solver")

        # write model to temporary file
        with tempfile.NamedTemporaryFile('w') as out_file:
            self.model.serialize(out_file, properties={ 0: VmtProperty(INVAR_PROPERTY, formula) })
            out_file.flush()

            self.options.set_print_witness()
            args = [self._solver_path, out_file.name]
            args.extend(self.options.to_array())

            try:
                # this may raise a CalledProcessError if the subprocess
                # returns a non-zero returncode since check is True
                solver = run(args, capture_output=True, text=True, check=True)
            except CalledProcessError as err:
                raise exceptions.UnknownSolverAnswerError(
                    f"Solver returned code {err.returncode}") from err
            if len(solver.stderr) > 0:
                raise exceptions.UnknownSolverAnswerError(
                    f"Solver printed errors `{solver.stderr}`")

            # analyze the result
            lines = solver.stdout.strip().split('\n')
            last_line = lines[-1]
            match = re.match(r'(.*)(true|false)\(unreach-call\)', last_line)
            if match is None:
                raise exceptions.UnknownSolverAnswerError(
                    "Solver last output line has unknown format")
            lines[-1] = match.group(1)

            is_safe = match.group(2) == 'true'
            trace = None

            if not is_safe:
                # recompile the updated lines to read the counterexample
                trace = self._read_counterexample(StringIO('\n'.join(lines)))
        return EuforiaResult(is_safe, trace=trace)

    def _read_counterexample(self, solver_out):
        trace = Trace('counterexample', self.model.get_state_vars(), env=self.model.get_env())

        parser = SmtLibParser()
        env = self.model.get_env()
        mgr = env.formula_manager

        step_assignments = {}

        script = parser.get_script(solver_out)
        for command in script.commands:
            if len(command.args) != 4:
                raise exceptions.UnknownSolverAnswerError(
                    "Counterexample function format is unknown")
            match = re.match(r'(.+)-(\d+)', command.args[0])
            # symbol_type = command.args[2]
            assignment = command.args[3]
            if match is None:
                raise exceptions.UnknownSolverAnswerError(
                    "Counterexample function format is unknown")
            symbol_name, step_idx = match.groups()
            step_idx = int(step_idx)
            step_assignments.setdefault(step_idx, {})
            symbol = mgr.get_symbol(symbol_name)
            step_assignments[step_idx][symbol] = assignment

        for step_idx in sorted(step_assignments):
            trace.create_step(step_assignments[step_idx])

        return trace

    def check_live_properties(self):
        raise NotImplementedError(
            "Live properties are not supported by this solver")

    def check_live_property(self, formula):
        raise NotImplementedError(
            "Live properties are not supported by this solver")

    def check_ltl_properties(self):
        raise NotImplementedError(
            "Ltl properties are not supported by this solver")

    def check_ltl_property(self, formula):
        raise NotImplementedError(
            "Ltl properties are not supported by this solver")

    def check_property(self, property_type, formula):
        if property_type == INVAR_PROPERTY:
            return self.check_invar_property(formula)
        if property_type == LIVE_PROPERTY:
            return self.check_live_property(formula)
        if property_type == LTL_PROPERTY:
            return self.check_ltl_property(formula)
        raise exceptions.InvalidPropertyTypeError(
            f"Invalid property type {property_type}")

    @classmethod
    def get_supported_logics(cls, options=None):
        return [ QF_AUFBV ]

class EuforiaResult(Result):
    '''Class to store the result from the Euforia solver
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

class EuforiaOptions(Options):
    '''Class containing the options for the Euforia solver
    '''
    def set_print_witness(self, value=True):
        '''Print the invariant/counterexample'''
        self._set_flag('w', value=value)
