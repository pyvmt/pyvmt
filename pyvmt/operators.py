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
import pysmt.rewritings
import pysmt.formula
import pysmt.printers
import pysmt.operators as op
from pysmt.substituter import MGSubstituter
from pyvmt import exceptions

# All of the required node types

# Future LTL
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
#: LTL operator for Yesterday

# Past LTL
LTL_Y = new_node_type(node_str="LTL_Y")
#: LTL operator for the dual of Yesterday
LTL_Z = new_node_type(node_str="LTL_Z")
#: LTL operator for Once
LTL_O = new_node_type(node_str="LTL_O")
#: LTL operator for Once
LTL_H = new_node_type(node_str="LTL_H")
#: LTL operator for Since
LTL_S = new_node_type(node_str="LTL_S")
#: LTL operator for Triggered
LTL_T = new_node_type(node_str="LTL_T")

#: Next operator, transforms a curr state formula into a next state formula
NEXT = new_node_type(node_str='NEXT')

# Finite LTL operator
#: LTLf operator con weak Next
LTL_N = new_node_type(node_str="LTL_N")

# PySmt does not currently support native extension of bv_width
# This is a workaround to extend the function to work with the Next operator
_pysmt_bv_width = FNode.bv_width
def _bv_width(self):
    if self.node_type() == NEXT:
        return self.arg(0).bv_width()
    return _pysmt_bv_width(self)
FNode.bv_width = _bv_width

FUTURE_LTL = (LTL_X, LTL_N, LTL_F, LTL_G, LTL_U, LTL_R)
PAST_LTL = (LTL_Y, LTL_Z, LTL_O, LTL_H, LTL_S, LTL_T)

ALL_LTL = FUTURE_LTL + PAST_LTL

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

    def Y(self, formula):
        '''Creates an expression of the form:
            Y formula
        '''
        return self.create_node(node_type=LTL_Y, args=(formula,))

    def Z(self, formula):
        '''Creates an expression of the form:
            Z formula
        '''
        return self.create_node(node_type=LTL_Z, args=(formula,))

    def O(self, formula):
        '''Creates an expression of the form:
            O formula
        '''
        return self.create_node(node_type=LTL_O, args=(formula,))

    def H(self, formula):
        '''Creates an expression of the form:
            H formula
        '''
        return self.create_node(node_type=LTL_H, args=(formula,))

    def S(self, left, right):
        '''Creates an expression of the form:
            left S right
        '''
        return self.create_node(node_type=LTL_S, args=(left, right))

    def T(self, left, right):
        '''Creates an expression of the form:
            left T right
        '''
        return self.create_node(node_type=LTL_T, args=(left, right))

    def Next(self, formula):
        '''Creates an expression of the form:
            (formula)'
        '''
        if self.env.has_next_operator_walker.has_next(formula):
            raise exceptions.UnexpectedNextError(
                "Next operator cannot contain a nested Next operator")
        return self.create_node(node_type=NEXT, args=(formula,))

    def N(self, formula):
        '''Creates an expression of the form:
            N formula
        '''
        return self.create_node(node_type=LTL_N, args=(formula,))
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
LTL_TYPE_TO_STR = { LTL_X: "X", LTL_F: "F", LTL_G: "G", LTL_U: "U", LTL_R: "R",\
        LTL_Y: "Y", LTL_Z: "Z", LTL_O: "O", LTL_H: "H", LTL_S: "S", LTL_T: "T",\
        LTL_N: "N"}

class HRPrinter(pysmt.printers.HRPrinter):
    '''Extension of the PySmt HRPrinter, prints formulae in a human readable format
    '''
    #pylint: disable=missing-function-docstring
    @handles(LTL_U, LTL_R, LTL_S, LTL_T)
    def walk_ltl_binary(self, formula):
        # Add spaces between opertor and arguments
        bin_str = " %s " % LTL_TYPE_TO_STR[formula.node_type()]
        return self.walk_nary(formula, bin_str)

    @handles(LTL_X, LTL_N, LTL_F, LTL_G, LTL_Y, LTL_Z, LTL_O, LTL_H)
    def walk_ltl_unary(self, formula):
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
    '''Extension of the PySmt HRSerializer, serializes formulae in a human readable format
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

def _walk_ltl_y(self, formula, args, **kwargs):
    return self.mgr.Y(args[0])

def _walk_ltl_z(self, formula, args, **kwargs):
    return self.mgr.Z(args[0])

def _walk_ltl_s(self, formula, args, **kwargs):
    return self.mgr.S(args[0], args[1])

def _walk_ltl_t(self, formula, args, **kwargs):
    return self.mgr.T(args[0], args[1])

def _walk_ltl_o(self, formula, args, **kwargs):
    return self.mgr.O(args[0])

def _walk_ltl_h(self, formula, args, **kwargs):
    return self.mgr.H(args[0])

def _walk_next(self, formula, args, **kwargs):
    return self.mgr.Next(args[0])

def _walk_ltl_n(self, formula, args, **kwargs):
    return self.mgr.N(args[0])

IdentityDagWalker.set_handler(_walk_ltl_x, LTL_X)
IdentityDagWalker.set_handler(_walk_ltl_u, LTL_U)
IdentityDagWalker.set_handler(_walk_ltl_r, LTL_R)
IdentityDagWalker.set_handler(_walk_ltl_f, LTL_F)
IdentityDagWalker.set_handler(_walk_ltl_g, LTL_G)
IdentityDagWalker.set_handler(_walk_ltl_y, LTL_Y)
IdentityDagWalker.set_handler(_walk_ltl_z, LTL_Z)
IdentityDagWalker.set_handler(_walk_ltl_s, LTL_S)
IdentityDagWalker.set_handler(_walk_ltl_t, LTL_T)
IdentityDagWalker.set_handler(_walk_ltl_o, LTL_O)
IdentityDagWalker.set_handler(_walk_ltl_h, LTL_H)
IdentityDagWalker.set_handler(_walk_next, NEXT)
IdentityDagWalker.set_handler(_walk_ltl_n, LTL_N)

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

class IsSafetyLtl(DagWalker):
    '''Returns whether the formula is in the safetyLTL fragment

        (Assumes that the formula is in nnf)
    '''
    def __init__(self, env=None):
        super().__init__(env=env)

    @handles(*op.ALL_TYPES, LTL_U, LTL_F)
    def walk_live(self, formula, args, **kwargs):
        return True

    @handles(*op.ALL_TYPES, *PAST_LTL, LTL_G, LTL_R, LTL_X, LTL_N, NEXT)
    def walk_other(self, formula, *args, **kwargs):
        '''Any operator which is not U/F will return True if any children nodes returns True'''
        return self.walk_any(formula, *args, **kwargs)

    def is_safety_ltl(self, formula):
        return not self.walk(formula)

class NextPusher(IdentityDagWalker):
    '''Walker to rewrite a formula moving all of the Next operators.

    The _get_children function is overridden to push the Next operator to the leaves.
    '''

    def __init__(self, bound_variables=None, env=None):
        super().__init__(env=env)
        if bound_variables is None:
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

class NNFIzer(pysmt.rewritings.NNFizer):
    '''Extension of pySMT's NNFizer.

    Converts a formula that may contain LTL operators into Negation Normal Form.
    '''

    def _get_children(self, formula):
        mgr = self.mgr
        if formula.is_not():
            s = formula.arg(0)
            if s.node_type() in (LTL_X, LTL_N, LTL_G, LTL_F, LTL_Y, LTL_Z, LTL_H, LTL_O, NEXT):
                return [mgr.Not(s.arg(0))]
            if s.node_type() in (LTL_U, LTL_R, LTL_S, LTL_T):
                return [mgr.Not(s.arg(0)), mgr.Not(s.arg(1))]
        elif formula.node_type() in (*ALL_LTL, NEXT):
            return formula.args()
        return super()._get_children(formula)

    def walk_not(self, formula, args, **kwargs):
        s = formula.arg(0)
        if s.node_type() == LTL_X:
            return self.mgr.N(args[0])
        if s.node_type() == LTL_N:
            return self.mgr.X(args[0])
        if s.node_type() == LTL_G:
            return self.mgr.F(args[0])
        if s.node_type() == LTL_F:
            return self.mgr.G(args[0])
        if s.node_type() == LTL_U:
            return self.mgr.R(args[0], args[1])
        if s.node_type() == LTL_R:
            return self.mgr.U(args[0], args[1])
        if s.node_type() == LTL_Y:
            return self.mgr.Z(args[0])
        if s.node_type() == LTL_Z:
            return self.mgr.Y(args[0])
        if s.node_type() == LTL_H:
            return self.mgr.O(args[0])
        if s.node_type() == LTL_O:
            return self.mgr.H(args[0])
        if s.node_type() == LTL_S:
            return self.mgr.T(args[0], args[1])
        if s.node_type() == LTL_T:
            return self.mgr.S(args[0], args[1])
        if s.node_type() == NEXT:
            return self.mgr.Next(args[0])
        return super().walk_not(formula, args, **kwargs)

    @handles(*ALL_LTL, NEXT)
    def walk_other(self, formula, args, **kwargs):
        return IdentityDagWalker.super(self, formula, args, **kwargs)

class XWeakener(IdentityDagWalker):
    '''Walker to rewrite a formula replacing all X occurrence with N.
    '''

    def __init__(self, env=None):
        super().__init__(env=env)

    def remove_strong_next(self, formula):
        '''Rewrite a formula containing LTL replacing strong next operator (X) with
        weak next (N). It should be noted that the translation alters the semantics
        of the formula when it is interpreted over finite traces. Infite semantics
        is not affected'''
        return self.walk(formula)

    def walk_ltl_x(self, formula, args, **kwargs):
        ''' X phi -> N phi'''
        assert(len(args) == 1)
        return self.mgr.N(args[0])
