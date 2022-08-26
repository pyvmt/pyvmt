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
    Classes and functions used to encode an LTL property.
'''
from pysmt.walkers import handles, IdentityDagWalker
import pysmt.operators as op
from pyvmt.operators import LTL_F, LTL_G, LTL_R, LTL_U, ALL_LTL, NNFIzer
from pyvmt.model import Model
from pyvmt import exceptions

# pylint: disable=unused-argument

class LtlRewriter(IdentityDagWalker):
    '''Walker to normalize an LTL formulae to only the LTL operators X and U'''

    def rewrite(self, formula):
        '''Rewrite a formula containing LTL to only contain the operators
        X and U'''
        return self.walk(formula)

    def walk_ltl_r(self, formula, args, **kwargs):
        '''fRg -> ¬(¬f U ¬g)'''
        assert len(args) == 2
        return self.mgr.Not(self.mgr.U(self.mgr.Not(args[0]), self.mgr.Not(args[1])))

    def walk_ltl_f(self, formula, args, **kwargs):
        '''Ff -> T U f'''
        assert len(args) == 1
        return self.mgr.U(self.mgr.TRUE(), args[0])

    def walk_ltl_g(self, formula, args, **kwargs):
        '''Gf -> ¬(F ¬f)'''
        assert len(args) == 1
        return self.mgr.Not(self.mgr.U(self.mgr.TRUE(), self.mgr.Not(args[0])))

class LtlEncodingWalker(IdentityDagWalker):
    '''Walker to find the elementary formulae composing an LTL formula, and
    the associated sat values.

    The walker assumes that the formula has already been rewritten in terms
    of X, U, and Not, using the LtlRewriter.
    '''

    def __init__(self, formula, env=None):
        super().__init__(env=env)
        self._el_map = {}
        self._formula = formula

    def get_el_map(self):
        '''Get the elementary subformulae for the formula.'''
        self.walk(self._formula)
        return self._el_map.copy()

    def get_sat(self, formula):
        '''Get the sat value for a formula.'''
        return self.walk(formula)

    @handles(LTL_F, LTL_G, LTL_R)
    def walk_ltl_unsupported(self, formula, args, **kwargs):
        '''Raise an error on use of unsupported operator'''
        raise NotImplementedError(
            f"Formula must not contain {formula.node_type} operators, "\
            "please, use the LtlRewriter to leave only U and X LTL operators.")

    def walk_ltl_x(self, formula, args, **kwargs):
        '''
        el(X f) = el(f) union { X f }
        sat(X f) = el(X f)
        '''
        assert len(args) == 1
        if formula not in self._el_map:
            self._el_map[formula] = self.mgr.FreshSymbol(formula.get_type(), 'el_x_%d')
        return self._el_map[formula]

    def walk_ltl_u(self, formula, args, **kwargs):
        '''
        el(f U g) = el(f) union el(g) union { X(f U g) }
        sat(f U g) = sat(g) | (sat(f) & el(X(f U g)))
        '''
        assert len(args) == 2
        x_formula = self.mgr.X(formula)
        if x_formula not in self._el_map:
            stvar = self.mgr.FreshSymbol(formula.get_type(), 'el_u_%d')
            self._el_map[x_formula] = stvar
        return self.mgr.Or(args[1], self.mgr.And(args[0], self._el_map[x_formula]))

def _copy_model(model):
    new_model = Model(env=model.get_env())
    for state_var in model.get_state_vars():
        new_model.add_state_var(state_var)
    for input_var in model.get_input_vars():
        new_model.add_input_var(input_var)
    for trans in model.get_trans_constraints():
        new_model.add_trans(trans)
    for init in model.get_init_constraints():
        new_model.add_init(init)
    return new_model

def ltl_encode(model, formula):
    '''Encodes an ltl property into a model and returns the new model

    :param model: The model on which to encode the property
    :type model: pyvmt.model.Model
    :param prop: The property to encode, must be of type LTL
    :type prop: pyvmt.properties.Property
    '''
    env = model.get_env()
    mgr = env.formula_manager
    # rewrite the formula in terms of X and U operators
    rewriter = LtlRewriter(env=model.get_env())
    formula = rewriter.rewrite(mgr.Not(formula))

    # get the elementary subformulae
    el_walker = LtlEncodingWalker(formula, env=model.get_env())
    el_map = el_walker.get_el_map()

    # create a new model with the same variables and constraints
    new_model = _copy_model(model)
    justice = []
    for el_, stvar in el_map.items():
        # add variables for the tableau
        new_model.add_state_var(stvar)
        sat = el_walker.get_sat(el_.arg(0))
        # define how the variables evolve
        new_model.add_trans(mgr.EqualsOrIff(stvar, mgr.Next(sat)))
        if el_.arg(0).node_type() == LTL_U:
            # add the required justice
            justice.append(mgr.Or(mgr.Not(sat), el_walker.get_sat(el_.arg(0).arg(1))))
    new_model.add_init(el_walker.get_sat(formula))

    if len(justice) != 1:
        # make single justice
        just_stvars = {}
        for just in justice:
            # add a state variable for each justice, initialized at 0
            just_stvar = mgr.FreshSymbol(template='J_%d')
            just_stvars[just] = just_stvar
            new_model.add_state_var(just_stvar)
            new_model.add_init(mgr.Iff(just_stvar, mgr.FALSE()))
        accept = mgr.And(just_stvars.values())

        for just in justice:
            # add a transition constraint for each justice state variable
            # once every justice is verified reset the state variables
            just_stvar = just_stvars[just]
            new_model.add_trans(
                mgr.Iff(
                    mgr.Next(just_stvar),
                    mgr.Ite(accept, just, mgr.Or(just, just_stvar))
                )
            )
        new_model.add_live_property(mgr.Not(accept))
    else:
        new_model.add_live_property(justice[0])

    return new_model

# LTL circuit encoder

class LtlCircuitEncodingWalker(IdentityDagWalker):
    '''Walker to facilitate the LTL circuit encoding procedure.

    Visits the formula and extracts subformulae, reconstructs the formula
    with newly created symbols.
    '''
    def __init__(self, formula, env=None):
        super().__init__(env=env)
        self._formula = formula
        self._subformulae = []

    def get_subformulae(self):
        '''Run the encoder and get the resulting subformulae.

        :return: The list of tuples containing the labels and the subformulae they represent.
        :rtype: [( pysmt.fnode.FNode: pysmt.fnode.FNode )]
        '''
        # Run the encoder if it wasn't already done
        if len(self.memoization) == 0:
            self.walk(self._formula)
            if len(self._subformulae) == 0:
                # Create a subformula to have at least one monitor
                self.store_subformula(
                    self.mgr.And(self._formula, self.mgr.TRUE()),
                    [ self._formula, self.mgr.TRUE() ]
                )
        return self._subformulae

    @handles(*ALL_LTL, op.AND, op.OR)
    def store_subformula(self, formula, args, **kwargs):
        formula = IdentityDagWalker.super(self, formula, args, **kwargs)
        z = self.mgr.FreshSymbol(template='LTL.Z.%d')
        self._subformulae.append((z, formula))
        return z
