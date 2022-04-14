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
'''Wrapper for nuXmv solver
'''

import os
from enum import Enum
import re
from subprocess import run, CalledProcessError
from pathlib import Path
import tempfile
from pysmt.logics import LIA, LRA, QF_AUFBVLIRA, QF_AUFBV
from pyvmt.solvers.solver import Solver, Result, Options
from pyvmt import exceptions
from pyvmt.properties import VmtProperty, LTL_PROPERTY, INVAR_PROPERTY, LIVE_PROPERTY
from pyvmt.solvers.traces import Trace

class NuxmvSolver(Solver):
    '''Class that wraps the nuXmv solver
    '''

    def __init__(self, model):
        super().__init__(model)
        self.options = NuxmvOptions()

        # find the executable
        env_var = 'PYVMT_NUXMV_PATH'
        solver_path = os.getenv(env_var)
        if solver_path is None:
            raise exceptions.SolverNotConfiguredError('nuXmv', env_var)
        self._solver_path = Path(solver_path)
        if not self._solver_path.is_file():
            raise exceptions.SolverNotFoundError(
                f"NuXmv executable not found in {self._solver_path}")
        if not self.supports_logic(self.model.get_logic()):
            raise exceptions.NoLogicAvailableError(
                "The model's logic is not supported by the solver")

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
        # FIXME the bmc interpolants algorithm cannot run with mixed LIA/LRA
        if not self.supports_logic(self.model.get_logic(extra_formulae=[formula]),
            options=self.options):
            raise exceptions.NoLogicAvailableError(
                "This logic is not supported by the solver")
        alg = self.options.get_algorithm()
        if alg == 'bmc':
            return self._check_invar_bmc(formula)
        if alg == 'bmc_cegar_implabs':
            return self._check_invar_bmc_cegar_implabs(formula)
        if alg == 'inc_coi':
            return self._check_invar_inc_coi(formula)
        if alg == 'bmc_implabs':
            return self._check_invar_bmc_implabs(formula)
        raise exceptions.InvalidSolverOption(
            f"Invar algorithm {alg} is not supported")

    def check_live_properties(self):
        results_map = {}
        for property_idx, prop in self.model.get_live_properties().items():
            results_map[property_idx] = self.check_live_property(prop.formula)
        return results_map

    def check_live_property(self, formula):
        return None #FIXME add possibility to check live property

    def check_ltl_properties(self):
        results_map = {}
        for property_idx, prop in self.model.get_ltl_properties().items():
            results_map[property_idx] = self.check_ltl_property(prop.formula)
        return results_map

    def check_ltl_property(self, formula):
        return self._run_solver(LTL_PROPERTY, formula, 'msat_check_ltlspec_inc_coi')

    def check_property(self, property_type, formula):
        if property_type == INVAR_PROPERTY:
            return self.check_invar_property(formula)
        if property_type == LIVE_PROPERTY:
            return self.check_live_property(formula)
        if property_type == LTL_PROPERTY:
            return self.check_ltl_property(formula)
        raise exceptions.InvalidPropertyTypeError(
            f"Invalid property type {property_type}")

    def _check_invar_inc_coi(self, formula):
        lines = self._run_solver(INVAR_PROPERTY, formula, self.options.get_invar_algorithm())

        is_safe = None
        trace = None

        assert re.match(r'^-- Using COI\(0\) variables$', lines[0])
        lines = self._clean_no_counterexample_found(lines[1:])
        if re.match(r'^-- invariant .+ is true$', lines[0]):
            assert len(lines) == 2
            is_safe = True
            assert re.match(r'^-- Property .+  is true$', lines[1])
        elif re.match(r'^-- invariant .+ is false, a counter-example of size '\
            r'\d+ exists$', lines[0]):
            is_safe = False
            assert lines[1] == '-- as demonstrated by the following execution sequence'
            i = 2
            trace_end = r'^-- Trace (was successfully|could not be) completed.$'
            while i < len(lines) and re.match(trace_end, lines[i]) is None:
                i+= 1
            if i >= len(lines):
                assert False
            trace = self._read_trace(lines[2:i])
            #TODO this could return both:
            # - Property .+ is false and
            # - Counterexample is SPURIOUS at bound 0
        elif re.match(r'SMT based model-checking could not determine if the property'\
            r' is either true or false up to bound \d+', lines[0]):
            if len(lines) == 2:
                assert lines[1] == '-- Cannot verify the property at COI(0)'
            else:
                assert len(lines) == 1
        else:
            assert False
        return NuxmvResult(is_safe, trace=trace)

    def _check_invar_bmc_implabs(self, formula):

        lines = self._run_solver(INVAR_PROPERTY, formula, self.options.get_invar_algorithm())

        trace = None
        is_safe = None

        if self.options.get_algorithm() == '':
            assert re.match(r'^Searching for a counterexample with bound \d+$', lines[0])
            if re.match(r'^Cannot say if the property is true or false: '\
                r'abstract counterexample found with bound \d+$', lines[1]):
                assert len(lines) == 2
            else:
                assert len(lines) == 3
                assert re.match(r'^No counterexample with bound \d+$', lines[1])
                assert re.match(r'^Abstract backward k-induction proves the '\
                    r'invariant holds at k=\d+$', lines[2])
                is_safe = True

        return NuxmvResult(is_safe, trace=trace)

    def _check_invar_bmc(self, formula):
        lines = self._run_solver(INVAR_PROPERTY, formula, self.options.get_invar_algorithm())

        trace = None
        is_safe = None

        if self.options.get_bmc_invar_alg() == NuxmvBmcInvarAlg.CLASSIC:
            # this returns either "-- cannot prove the invariant ... is true or false :
            # the induction failed" or "-- invariant is true/false"

            if re.match(r'^-- cannot prove the invariant .+ is true or '\
                r'false : the induction failed$', lines[0]) is not None:
                assert lines[1] == '-- as demonstrated by the following induction step sequence'
                # read the induction sequence
                trace = self._read_trace(lines[2:])
            elif (match := re.match(r'^-- invariant .+ is (true|false)$', lines[0])) is not None:
                assert len(lines) == 1
                is_safe = match.group(1) == 'true'
            else:
                # not yet handled
                assert False
        else:
            # tries to find a counterexample or proof
            # then prints whether the invariant is true or false
            lines = self._clean_no_counterexample_found(lines)
            if len(lines) == 0:
                # no counterexample found
                # is_safe = None
                pass
            elif re.match(r'^-- invariant .+ is true.*$', lines[0]) is not None:
                is_safe = True
            elif re.match(r'^-- invariant .+ is false.*$', lines[0]) is not None:
                assert lines[1] == '-- as demonstrated by the following execution sequence'
                trace = self._read_trace(lines[2:])
                is_safe = False
            else:
                # not yet handled
                assert False
        return NuxmvResult(is_safe, trace=trace)

    def _check_invar_bmc_cegar_implabs(self, formula):
        lines = self._run_solver(INVAR_PROPERTY, formula, self.options.get_invar_algorithm())

        is_safe = None

        if (match := re.match(r'^-- invariant .+ is (false|unknown).*$', lines[0])) is not None:
            if match.group(1) == 'false':
                is_safe = False
        else:
            assert len(lines) == 5
            assert re.match(r'^K-Induction (?:F|B)WD is unsat. No bugs. \d+$', lines[0])
            assert re.match(r'^Last bound: \d+$', lines[1])
            assert re.match(r'^Number of predicates final: \d+$', lines[2])
            assert re.match(r'^Number of mirrors final: \d+$', lines[3])
            assert re.match(r'^-- invariant .+ is true$', lines[4])
            is_safe = True

        return NuxmvResult(is_safe)

    def _run_solver(self, property_type, formula, algorithm):
        # write model to temporary file
        with tempfile.NamedTemporaryFile('w') as out_file:
            self.model.serialize(out_file, properties={ 0: VmtProperty(property_type, formula) })
            out_file.flush()

            args = [self._solver_path, '-int', out_file.name]

            solver_in = "\n".join([
                'read_vmt_model',
                'go_msat',
                algorithm, #FIXME better algorithm handling is required
                'quit',
                ''
            ])

            try:
                # this may raise a CalledProcessError if the subprocess
                # returns a non-zero returncode since check is True
                solver = run(args, capture_output=True, text=True, check=True, input=solver_in)
            except CalledProcessError as err:
                raise exceptions.UnknownSolverAnswerError(
                    f"Solver returned code {err.returncode}") from err
            if len(solver.stderr) > 0:
                err_lines = solver.stderr.strip().split('\n')
                err_lines = self._clean_no_counterexample_found(err_lines)
                if len(err_lines) > 0:
                    raise exceptions.UnknownSolverAnswerError(
                        f"Solver printed errors `{solver.stderr}`")
            lines = solver.stdout.split('\n')
            lines = self._clean_info_and_prompts(lines)

        return lines

    def _clean_info_and_prompts(self, lines):
        # discard the info printed at the start
        i = 0
        while i < len(lines) and lines[i] == '' or lines[i].startswith('***'):
            i+= 1

        # the first line should contain the prompts followed by some info
        prompt = 'nuXmv > '
        match = re.match(f'^(?:{prompt})+(.+)$', lines[i])
        if match is None:
            raise exceptions.UnknownSolverAnswerError(
                "Expected prompts after the info")

        # discard the input prompts
        lines[i] = match.group(1)

        # last line should contain a final input prompt
        j = len(lines) - 1
        while j > i and lines[j] == prompt or lines[j] == '':
            j-= 1
        return lines[i:j + 1]

    def _clean_no_counterexample_found(self, lines):
        i = 0
        no_counterexample_re = re.compile(r'^(?:'\
            r'(?:-- no counterexample or proof found for invariant .+ up to \d+)|'\
            r'(?:-- no proof or counter-?example found with bound \d+)|'\
            r'(?:-- no counterexample found with bound \d+))$')
        while i < len(lines) and no_counterexample_re.match(lines[i]) is not None:
            i+= 1
        if i + 1 == len(lines) and lines[i] == '':
            return []
        return lines[i:]

    def _read_trace(self, lines):
        mgr = self.model.get_env().formula_manager

        match = re.match(r'^Trace Description: (.+)$', lines[0])
        assert match is not None
        # trace_description = match.group(1)

        match = re.match(r'^Trace Type: (.+)$', lines[1])
        assert match is not None
        trace_type = match.group(1).strip()
        trace = Trace(trace_type, self.model.get_state_vars(), env=self.model.get_env())

        i = 2
        curr_values = {}
        step_re = re.compile(r'^\s*-> (State|Input): \d+\.\d+ <-$')
        #TODO deal with Input
        assignment_re = re.compile(r'^\s*(.+)\s=\s(.+)$')
        while i < len(lines):
            is_loopback = (lines[i] == '  -- Loop starts here')
            if is_loopback:
                i+= 1
            match = step_re.match(lines[i])
            assert match is not None
            i+= 1
            while i < len(lines) and step_re.match(lines[i]) is None:
                match = assignment_re.match(lines[i])
                assert match is not None
                varname, value = match.groups()
                curr_values[mgr.get_symbol(varname)] = self._parse_constant(value)
                i+= 1
            trace.create_step(curr_values, is_loopback=is_loopback)
        return trace

    def _parse_constant(self, value):
        mgr = self.model.get_env().formula_manager

        # boolean constant
        if value == 'TRUE':
            return mgr.TRUE()
        if value == 'FALSE':
            return mgr.FALSE()

        # integer constant
        try:
            value = int(value)
            return mgr.Int(value)
        except ValueError:
            pass

        # real constant
        try:
            value = float(value)
            return mgr.Real(value)
        except ValueError:
            pass
        if (match := re.match(r'[fF]\'(\d+)/(\d+)', value)) is not None:
            # real constant in fraction form
            num, den = (int(x) for x in match.groups())
            return mgr.Real(num/den)

        #TODO add different types if required, raise exception on unmatched
        # word constant
        # range constant
        # symbolic constant
        return value

    @classmethod
    def get_supported_logics(cls, options=None):
        if options is not None:
            if options.get_bmc_invar_alg in [ NuxmvBmcInvarAlg.INTERP_SEQ,
                NuxmvBmcInvarAlg.INTERPOLANTS ]:
                return [ LIA, LRA, QF_AUFBV ]
        return [ QF_AUFBVLIRA ]

class NuxmvResult(Result):
    '''
        Class to store an nuXmv result
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

class NuxmvBmcInvarAlg(Enum):
    '''Possible values for the bmc invar algorithm
    '''
    CLASSIC = 'classic'
    EEN_SORENSSON = 'een-sorensson'
    FALSIFICATION = 'falsification'
    DUAL = 'dual'
    ZIGZAG = 'zigzag'
    INTERP_SEQ = 'interp_seq'     # cannot handle mixed LIA/LRA
    INTERPOLANTS = 'interpolants' # cannot handle mixed LIA/LRA

class NuxmvOptions(Options):
    '''Options for NuXmv, these options are passed to the process while it's running
        instead of passing them as command line options
    '''
    def __init__(self):
        super().__init__()
        self._alg = 'bmc'
        self._bmc_invar_alg = NuxmvBmcInvarAlg.CLASSIC
        self._bmc_len = None

    def set_algorithm(self, algorithm):
        '''
            Set the algorithm for model checking, currently supported:
            for invar:
            - bmc_cegar_implabs
            - bmc_implabs
            - bmc
            - inc_coi
        '''
        if algorithm not in ['bmc_cegar_implabs', 'bmc_implabs', 'bmc', 'inc_coi']:
            #TODO add more algorithms
            raise exceptions.InvalidSolverOption(
                f"Algorithm {algorithm} is not currently supported")
        self._alg = algorithm
        # supported algorithms:
        # for invar:
        # - bmc_cegar_implabs
        # - bmc_implabs
        # - bmc
        # - inc_coi

        # for ltl:
        # - bmc
        # - inc_coi
        # - sbmc_inc

    def get_algorithm(self):
        return self._alg

    def set_bmc_invar_alg(self, algorithm):
        '''
            Set the algorithm to use to prove invariants while using the bmc algorithm

            Possible values are:
            - classic (it is k-induction with k=1)
            - een-sorensson -e (extra step to find the proof)
            - falsification -K step_size -i (incremental version)
            - dual
            - zigzag
            - interp_seq
            - interpolants

            This will pass the option to the model checking command since the variable only accepts
            classic and een-sorensson
        '''
        try:
            algorithm = NuxmvBmcInvarAlg(algorithm)
        except ValueError as err:
            raise exceptions.InvalidSolverOption(
                "Invalid option, valid options are found in NuxmvBmcInvarAlg") from err
        self._bmc_invar_alg = algorithm

    def get_bmc_invar_alg(self):
        return self._bmc_invar_alg

    def set_bmc_len(self, bmc_len):
        '''Set the length for bmc algorithm'''
        if not isinstance(bmc_len, int) or bmc_len <= 0:
            raise exceptions.InvalidSolverOption(
                f"Bmc length must be a positive integer {bmc_len} found")
        self._bmc_len = bmc_len

    def get_invar_algorithm(self):
        '''returns the invar algorithm with the related options'''
        command_segments = None
        if self._alg == 'bmc':
            # check the bmc algorithm to use
            command_segments = ['msat_check_invar_bmc']
            if self._bmc_len is not None and self._bmc_invar_alg != NuxmvBmcInvarAlg.CLASSIC:
                command_segments.append(f'-k {self._bmc_len}')
            if self._bmc_invar_alg is not None:
                command_segments.append(f'-a {self._bmc_invar_alg.value}')
            # TODO add more of options, check validity
        elif self._alg == 'bmc_cegar_implabs':
            command_segments = ['msat_check_invar_bmc_cegar_implabs']
        elif self._alg == 'bmc_implabs':
            command_segments = ['msat_check_invar_bmc_implabs', '-n', 0]
        elif self._alg == 'inc_coi':
            command_segments = ['msat_check_invar_inc_coi']
        else:
            # unsupported algorithm for invar
            assert False
        return ' '.join(str(x) for x in command_segments)
