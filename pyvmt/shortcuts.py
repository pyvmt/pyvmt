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
'''This module provides utility functions to create formulae in the global environment.
'''

import pyvmt.environment

def get_env():
    '''Get the global environment'''
    return pyvmt.environment.get_env()

def reset_env():
    '''Recreate the global environment and return the new one'''
    return pyvmt.environment.reset_env()

#pylint: disable=invalid-name

def Next(formula):
    '''Creates an expression of the form:
        (formula)'
    '''
    return get_env().formula_manager.Next(formula)

def X(formula):
    '''Creates an expression of the form:
        X formula
    '''
    return get_env().formula_manager.X(formula)

def F(formula):
    '''Creates an expression of the form:
        F formula
    '''
    return get_env().formula_manager.F(formula)

def G(formula):
    '''Creates an expression of the form:
        G formula
    '''
    return get_env().formula_manager.G(formula)

def U(left, right):
    '''Creates an expression of the form:
        left U right
    '''
    return get_env().formula_manager.U(left, right)

def R(left, right):
    '''Creates an expression of the form:
        left R right
    '''
    return get_env().formula_manager.R(left, right)

def Y(formula):
    '''Creates an expression of the form:
        Y formula
    '''
    return get_env().formula_manager.Y(formula)

def Z(formula):
    '''Creates an expression of the form:
        Z formula
    '''
    return get_env().formula_manager.Z(formula)

def O(formula):
    '''Creates an expression of the form:
        O formula
    '''
    return get_env().formula_manager.O(formula)

def H(formula):
    '''Creates an expression of the form:
        H formula
    '''
    return get_env().formula_manager.H(formula)

def S(left, right):
    '''Creates an expression of the form:
        left S right
    '''
    return get_env().formula_manager.S(left, right)

def T(left, right):
    '''Creates an expression of the form:
        left T right
    '''
    return get_env().formula_manager.T(left, right)

def has_ltl(formula):
    '''Returns whether the formula contains any of the LTL operators'''
    return get_env().has_ltl_operators_walker.has_ltl(formula)

def has_next(formula):
    '''Returns whether the formula contains the Next operator'''
    return get_env().has_next_operator_walker.has_next(formula)

def push_next(formula):
    '''Rewrites the formula by pushing the Next operator down to the leaf nodes
    that contain Symbols'''
    return get_env().next_pusher.push_next(formula)
