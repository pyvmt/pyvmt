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
    Module for all PyVmt exceptions
'''

class PyvmtException(Exception):
    '''
        Base exception for pyvmt
    '''

class UnexpectedStateVariableError(PyvmtException):
    '''
        Raised when a formula which shouldn't have next/prev state variables has one
    '''

class StateVariableError(PyvmtException):
    '''
        Raised when a formula which should be a state variable isn't
    '''

class UnexpectedInputVariableError(PyvmtException):
    '''
        Raised when a formula which shouldn't have an input variable has one
    '''

class MismatchedTypeError(PyvmtException):
    '''
        Raised when two types mismatch, like the types for a state variable
    '''

class NotSymbolError(PyvmtException):
    '''
        Raised when a formula which is expected to be a symbol is not
    '''

class DuplicateDeclarationError(PyvmtException):
    '''
        Raised when a symbol is being declared twice
    '''

class UndeclaredSymbolError(PyvmtException):
    '''
        Raised when a symbol is being declared twice
    '''

class PyvmtTypeError(PyvmtException, TypeError):
    '''
        Raised when the type of a formula is incorrect
    '''

class InvalidPropertyIdxError(PyvmtException):
    '''
        Raised when creating a property with an invalid index
    '''

class DuplicatePropertyIdxError(PyvmtException):
    '''
        Raised when creating a property with a duplicate index
    '''

class PropertyNotFoundError(PyvmtException):
    '''
        Raised when the searched property doesn't exist
    '''

class InvalidAnnotationValueError(PyvmtException):
    '''
        Raised when an annotation has an invalid value
    '''

class UnknownSolverAnswerError(PyvmtException):
    '''
        Raised when a solver returns an invalid response
    '''

class InvalidSolverOption(PyvmtException):
    '''
        Raised when an invalid option or option value is used
    '''

class IncorrectSymbolNameError(PyvmtException):
    '''
        Raised when a symbol has an invalid name,
        for example when trying to replace a prefix and
        the symbol is missing that prefix
    '''

class MismatchedEnvironmentError(PyvmtException):
    '''
        Raised when an operation is working on different environments
        at the same time, for example a composition on two models
        which don't belong to the same environment
    '''

class DuplicateLoopbackStepError(PyvmtException):
    '''
        Raised when trying to create a loopback step for a trace which already has one
    '''

class MissingLoopbackStepError(PyvmtException):
    '''
        Raised when trying to get a loopback step for a trace which doesn't have one
    '''

class UnexpectedLtlError(PyvmtException):
    '''
        Raised when a formula which shouldn't contain LTL operators does
    '''

class UnexpectedNextError(PyvmtException):
    '''
        Raised when a formula which shouldn't contain Next operators does
    '''

class InvalidPropertyTypeError(PyvmtException):
    '''
        Raised when the type of a property is invalid.
        Valid property types are found in pyvmt.properties.PROPERTY_TYPES
    '''

class TraceStepNotFoundError(PyvmtException):
    '''
        Raised when a trace step is not found, for example while requesting
        the step after a last one in a trace with no loopback.
    '''

class SolverNotConfiguredError(PyvmtException):
    '''
        Raised when a solver that is not configured is used.
    '''
    def __init__(self, solver_name, env_var):
        super().__init__(f'Solver {solver_name} configuration not found, '\
            f'please add the variable {env_var} to your environment file, '\
            'look at the documentation for a detailed explanation')

class SolverNotFoundError(PyvmtException):
    '''
        Raised when a solver is not found at the specified path.
    '''

class NoLogicAvailableError(PyvmtException):
    '''
        Raised when no logic is available for a solver.
    '''
