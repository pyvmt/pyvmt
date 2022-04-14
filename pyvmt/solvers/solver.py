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
    Exports the base solver interface for a VMT problem
'''

from abc import ABCMeta, abstractmethod

class Solver(metaclass=ABCMeta):
    '''
        Interface for a solver for a VMT problem
    '''

    def __init__(self, model):
        '''Initialize the solver with a model

        :param model: The model to check
        :type model: pyvmt.model.Model
        '''
        self.model = model

    def check_properties(self):
        '''Check all the model properties

        :param model: The model to check
        :type model: pyvmt.model.Model
        :return: { int: pyvmt.solvers.solver.Result }
        '''
        raise NotImplementedError

    def check_property_idx(self, property_idx):
        '''Check the model property identified by the index

        :param model: The model to check
        :type model: pyvmt.model.Model
        :param property_idx: The property index to check
        :type property_idx: int
        :return: pyvmt.solvers.solver.Result
        '''
        raise NotImplementedError

    def check_invar_properties(self):
        '''Check the model invar properties

        :param model: The model to check
        :type model: pyvmt.model.Model
        :return: { int: pyvmt.solvers.solver.Result }
        '''
        raise NotImplementedError

    def check_invar_property(self, formula):
        '''Check the invar property against the model

        :param model: The model to check
        :type model: pyvmt.model.Model
        :param formula: The property to check
        :type formula: pysmt.fnode.FNode
        :return: pyvmt.solvers.solver.Result
        '''
        raise NotImplementedError

    def check_live_properties(self):
        '''Check the model live properties

        :param model: The model to check
        :type model: pyvmt.model.Model
        :return: { int: pyvmt.solvers.solver.Result }
        '''
        raise NotImplementedError

    def check_live_property(self, formula):
        '''Check the live property against the model

        :param model: The model to check
        :type model: pyvmt.model.Model
        :param formula: The property to check
        :type formula: pysmt.fnode.FNode
        :return: Dict[int, pyvmt.solvers.solver.Result]
        '''
        raise NotImplementedError

    def check_ltl_properties(self):
        '''Check the model LTL properties

        :param model: The model to check
        :type model: pyvmt.model.Model
        :return: { int: pyvmt.solvers.solver.Result }
        '''
        raise NotImplementedError

    def check_ltl_property(self, formula):
        '''Check the LTL property against the model

        :param model: The model to check
        :type model: pyvmt.model.Model
        :param formula: The property to check
        :type formula: pysmt.fnode.FNode
        :return: pyvmt.solvers.solver.Result
        '''
        raise NotImplementedError

    def check_property(self, property_type, formula):
        '''Check a property with a specified type

        :param model: The model to check
        :type model: pyvmt.model.Model
        :param property_type: The type of type property
        :type property_type: One of pyvmt.properties.PROPERTY_TYPES
        :param formula: The property to check
        :type formula: pysmt.fnode.FNode
        '''
        raise NotImplementedError

    @classmethod
    @abstractmethod
    def get_supported_logics(cls, options=None):
        '''Returns a List containing the logics supported by the solver'''
        raise NotImplementedError

    @classmethod
    def supports_logic(cls, logic, options=None):
        '''Check if the solver supports a specific logic'''
        supported_logics = cls.get_supported_logics(options=options)
        for supported_logic in supported_logics:
            if logic <= supported_logic:
                return True
        return False

class Result:
    '''
        Interface for the result of a VMT solver
    '''
    def is_safe(self):
        '''Returns whether the property is safe

        :return: True if the property is safe, False otherwise
        :rtype: bool
        '''
        raise NotImplementedError


    def is_unsafe(self):
        '''Returns whether the property is unsafe

        :return: True if the property is unsafe, False otherwise
        :rtype: bool
        '''
        return not self.is_safe()

    def get_trace(self):
        '''Returns the trace generated by the solver.

        The trace can represent a counterexample to a property.

        :return: The trace contained in the result if any
        :rtype: pyvmt.solvers.traces.Trace
        '''
        raise NotImplementedError

    def has_trace(self):
        '''Return whether the result from the solver has a trace.

        :return: True if the result has a trace, False otherwise
        :rtype: bool
        '''
        raise NotImplementedError


class Options:
    '''
        Interface for the options of a VMT solver
    '''

    def __init__(self):
        self._options = {}
        self._flags = set()

    def to_array(self):
        '''Convert the options to an array of arguments

        :return: An equivalent array of arguments
        :rtype: List[str]
        '''
        res = []
        for option, value in self._options.items():
            res.append(f'-{option}')
            res.append(str(value))
        res.extend(f'-{flag}' for flag in self._flags)
        return res

    def _set_flag(self, flag, value = True):
        if value:
            self._flags.add(flag)
        else:
            self._flags.remove(flag)
