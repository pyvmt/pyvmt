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
'''Implements linear temporal logic in PyVmt

Also implements the 'next' operator, used to generate next state variables.

This module creates nodes for the LTL operators and extends
parts of PySmt to work with them
'''

# pylint: disable=invalid-name
# pylint: disable=unused-argument

from pysmt.fnode import FNode
from pysmt.operators import new_node_type
from pysmt.type_checker import SimpleTypeChecker
from pysmt.oracles import FreeVarsOracle, TheoryOracle, QuantifierOracle
from pysmt.walkers import handles, IdentityDagWalker, DagWalker
import pysmt.formula
import pysmt.printers
import pysmt.operators as op
from pysmt.substituter import MGSubstituter
from pyvmt import exceptions

# All of the required node types

#: LTL operator for neXt
LTL_X = new_node_type(node_str="LTL_X")
#: LTL operator for eventually (Future)
LTL_F = new_node_type(node_str="LTL_F")
#: LTL operator for Globally
LTL_G = new_node_type(node_str="LTL_G")
#: LTL operator for Until
LTL_U = new_node_type(node_str="LTL_U")
#: LTL operator for Releases
LTL_R = new_node_type(node_str="LTL_R")

#: Next operator, transforms a curr state formula into a next state formula
NEXT = new_node_type(node_str='NEXT')

# PySmt does not currently support native extension of bv_width
# This is a workaround to extend the function to work with the Next operator
_pysmt_bv_width = FNode.bv_width
def _bv_width(self):
    if self.node_type() == NEXT:
        return self.arg(0).bv_width()
    return _pysmt_bv_width(self)
FNode.bv_width = _bv_width

ALL_LTL = (LTL_X, LTL_F, LTL_G, LTL_U, LTL_R)

class FormulaManager(pysmt.formula.FormulaManager):
    '''An extension of the PySmt formula manager
    which includes LTL operators and the Next operator
    '''

    def X(self, formula):
        '''Creates an expression of the form:
            X formula
        '''
        return self.create_node(node_type=LTL_X, args=(formula,))

    def F(self, formula):
        '''Creates an expression of the form:
            F formula
        '''
        return self.create_node(node_type=LTL_F, args=(formula,))

    def G(self, formula):
        '''Creates an expression of the form:
            G formula
        '''
        return self.create_node(node_type=LTL_G, args=(formula,))

    def U(self, left, right):
        '''Creates an expression of the form:
            left U right
        '''
        return self.create_node(node_type=LTL_U, args=(left, right))

    def R(self, left, right):
        '''Creates an expression of the form:
            left R right
        '''
        return self.create_node(node_type=LTL_R, args=(left, right))

    def Next(self, formula):
        '''Creates an expression of the form:
            (formula)'
        '''
        if self.env.has_next_operator_walker.has_next(formula):
            raise exceptions.UnexpectedNextError(
                "Next operator cannot contain a nested Next operator")
        return self.create_node(node_type=NEXT, args=(formula,))

# set handlers for SimpleTypeChecker for the new operators

def _type_walk_next(self, formula, args, **kwargs):
    assert formula is not None
    return args[0]

SimpleTypeChecker.set_handler(SimpleTypeChecker.walk_bool_to_bool, *ALL_LTL)
SimpleTypeChecker.set_handler(_type_walk_next, NEXT)

TheoryOracle.set_handler(TheoryOracle.walk_combine, NEXT)

QuantifierOracle.set_handler(DagWalker.walk_all, NEXT, *ALL_LTL)

# set handlers for FreeVarsOracle for the new operators
FreeVarsOracle.set_handler(FreeVarsOracle.walk_simple_args, *ALL_LTL)
FreeVarsOracle.set_handler(FreeVarsOracle.walk_simple_args, NEXT)

# Extend the classes required for HR printing and serialization
LTL_TYPE_TO_STR = { LTL_X: "X", LTL_F: "F", LTL_G: "G"}

class HRPrinter(pysmt.printers.HRPrinter):
    '''Extension of the PySmt HRPrinter, prints formuale in a human readable format
    '''
    #pylint: disable=missing-function-docstring

    def walk_ltl_r(self, formula):
        return self.walk_nary(formula, " R ")

    def walk_ltl_u(self, formula):
        return self.walk_nary(formula, " U ")

    @handles(LTL_X, LTL_F, LTL_G)
    def walk_ltl(self, formula):
        node_type = formula.node_type()
        op_symbol = LTL_TYPE_TO_STR[node_type]
        self.stream.write("(")
        self.stream.write(f"{op_symbol} ")
        yield formula.arg(0)
        self.stream.write(")")

    def walk_next(self, formula):
        yield formula.arg(0)
        self.stream.write("'")

class HRSerializer(pysmt.printers.HRSerializer):
    '''Extension of the PySmt HRSerializer, serializes formuale in a human readable format
    '''
    PrinterClass = HRPrinter

# create the new methods required by IdentityDagWalker

def _walk_ltl_x(self, formula, args, **kwargs):
    return self.mgr.X(args[0])

def _walk_ltl_u(self, formula, args, **kwargs):
    return self.mgr.U(args[0], args[1])

def _walk_ltl_r(self, formula, args, **kwargs):
    return self.mgr.R(args[0], args[1])

def _walk_ltl_f(self, formula, args, **kwargs):
    return self.mgr.F(args[0])

def _walk_ltl_g(self, formula, args, **kwargs):
    return self.mgr.G(args[0])

def _walk_next(self, formula, args, **kwargs):
    return self.mgr.Next(args[0])

IdentityDagWalker.set_handler(_walk_ltl_x, LTL_X)
IdentityDagWalker.set_handler(_walk_ltl_u, LTL_U)
IdentityDagWalker.set_handler(_walk_ltl_r, LTL_R)
IdentityDagWalker.set_handler(_walk_ltl_f, LTL_F)
IdentityDagWalker.set_handler(_walk_ltl_g, LTL_G)
IdentityDagWalker.set_handler(_walk_next, NEXT)

# Set handlers for the MGSubstituter for the new operators
MGSubstituter.set_handler(MGSubstituter.walk_identity_or_replace, NEXT, *ALL_LTL)

class HasLtlOperatorsWalker(DagWalker):
    '''Walker to check if a formula contains LTL operators
    '''
    def __init__(self, env=None):
        super().__init__(env=env)

    @handles(*ALL_LTL)
    def walk_ltl(self, formula, args, **kwargs):
        '''All LTL operators will return True'''
        return True

    @handles(*op.ALL_TYPES, NEXT)
    def walk_other(self, formula, *args, **kwargs):
        '''Any operator which is not LTL will return True if any children nodes returns True'''
        return self.walk_any(formula, *args, **kwargs)

    def has_ltl(self, formula):
        '''Returns whether the formula contains LTL operators

        :param formula: The formula to check
        :type formula: pysmt.fnode.FNode
        :return: True if the formula contains LTL operators, False otherwise
        :rtype: bool
        '''
        return self.walk(formula)

class HasNextOperatorWalker(DagWalker):
    '''Walker to check if a formula contain the Next operator
    '''
    def __init__(self, env=None):
        super().__init__(env=env)

    def walk_next(self, formula, args, **kwargs):
        '''The next operator returns True'''
        return True

    @handles(*op.ALL_TYPES, *ALL_LTL)
    def walk_other(self, formula, *args, **kwargs):
        '''Any operator which is not Next will return True if any children nodes returns True'''
        return self.walk_any(formula, *args, **kwargs)

    def has_next(self, formula):
        '''Returns whether the formula contains the Next operator

        :param formula: The formula to check
        :type formula: pysmt.fnode.FNode
        :return: True if the formula contains the Next operator, False otherwise
        :rtype: bool
        '''
        return self.walk(formula)

class NextPusher(IdentityDagWalker):
    '''Walker to rewrite a formula moving all of the Next operators.

    The _get_children function is overridden to push the Next operator to the leaves.
    '''

    def __init__(self, bound_variables=None, env=None):
        super().__init__(env=env)
        if bound_variables == None:
            bound_variables = set()
        self._bound_variables = bound_variables

    def _push_with_children_to_stack(self, formula, **kwargs):
        # deal with quantifiers
        if formula.is_quantifier():
            # recalculate bound variables
            bound_variables = set(self._bound_variables)
            bound_variables.update(formula.quantifier_vars())

            # apply the function with the bound variables
            sub = self.__class__(bound_variables, env=self.env)
            res_formula = sub.walk(formula.arg(0), **kwargs)

            # call the function and memoize the result
            fun = sub.functions[formula.node_type()]
            res = fun(formula, args=[res_formula], **kwargs)
            self.memoization[self._get_key(formula, **kwargs)] = res
        else:
            super()._push_with_children_to_stack(formula, **kwargs)

    def _get_children(self, formula):
        mgr = self.mgr
        if formula.node_type() == NEXT:
            sub = formula.arg(0)
            if sub.node_type() == NEXT:
                raise exceptions.UnexpectedNextError(
                    "Next operator must not contain a Next operator")
            try:
                f = self.functions[sub.node_type()]
            except KeyError:
                f = self.walk_error

            args = tuple(mgr.Next(x) for x in sub.args())
            return [f(sub, args)]
        return super()._get_children(formula)

    def walk_next(self, formula, args, **kwargs):
        '''If a leaf node is reached and it's a Symbol then the result is the Next
        of that symbol, otherwise the Next operator should have already been pushed
        to the leaves and is no longer necessary.
        '''
        assert len(args) == 1
        mgr = self.mgr
        if args[0].is_symbol() and args[0] not in self._bound_variables:
            return mgr.Next(args[0])
        return args[0]

    def push_next(self, formula):
        '''Push all of the Next operators to the leaf nodes containing symbols.

        Example: (a | b)' becomes (a' | b')

        :param formula: The formula before pushing next operators to the leaves
        :type formula: pysmt.fnode.FNode
        :return: The formula after pushing next operators to the leaves
        :rtype: pysmt.fnode.FNode
        '''
        return self.walk(formula)
