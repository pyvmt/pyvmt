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
from pyvmt.operators import LTL_X, LTL_F, LTL_G, LTL_R, LTL_U, ALL_LTL, NNFIzer
from pyvmt.model import Model
from pyvmt.environment import get_env

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

def make_single_justice(justice, env=None):
    '''Transforms a list of justice constraints into a single one encapsulating
    all of them.

    :param justice: The list of justice constraints
    :type justice: [pysmt.fnode.FNode]
    :param env: The environment to use, defaults to the global environment
    :type env: pyvmt.environment.Environment, optional
    :return: The new property, the variables used and how they're constrained
        (accept, stvars, init, trans)
    :rtype: (pysmt.fnode.FNode, [pysmt.fnode.FNode], [pysmt.fnode.FNode], \
        [pysmt.fnode.FNode])
    '''
    if env is None:
        env = get_env()
    mgr = env.formula_manager

    stvars = []
    init = []
    trans = []
    for just in justice:
        # add a state variable for each justice, initialized at 0
        just_stvar = mgr.FreshSymbol(template='J_%d')
        stvars.append(just_stvar)
        init.append(mgr.Iff(just_stvar, mgr.FALSE()))
    accept = mgr.And(stvars)

    for i, just in enumerate(justice):
        # add a transition constraint for each justice state variable
        # once every justice is verified reset the state variables
        just_stvar = stvars[i]
        trans.append(
            mgr.Iff(
                mgr.Next(just_stvar),
                mgr.Ite(accept, just, mgr.Or(just, just_stvar))
            )
        )
    return accept, stvars, init, trans

def ltl_encode(model, formula):
    '''Encodes an ltl property into a model and returns the new model

    :param model: The model on which to encode the property
    :type model: pyvmt.model.Model
    :param prop: The property to encode, must be of type LTL
    :type prop: pyvmt.properties.Property
    :return: A new model with the added live property at index 0
    :rtype: pyvmt.model.Model
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

    def make_monitor (self, is_init, activator, formula):
        '''Creates a monitor for the passed formula.

        :param is_init: A variable which is True in the first step, False otherwise
        :type is_init: pysmt.fnode.FNode
        :param activator: The activator for the monitor, corresponding to variable z
        :type activator: pysmt.fnode.FNode
        :param formula: The formula for which to create the monitor
        :type formula: pysmt.fnode.FNode
        :return: A tuple containing the data for the monitor
            (stvars, init, trans, accept, failed, pending)
        :rtype: ([pysmt.fnode.FNode], [pysmt.fnode.FNode], [pysmt.fnode.FNode], \
            pysmt.fnode.FNode, pysmt.fnode.FNode, pysmt.fnode.FNode)
        '''
        mgr = self.mgr
        stvars = []
        init = []
        trans = []
        accept = mgr.TRUE()
        failed = mgr.FALSE()
        pending = mgr.FALSE()

        if formula.is_and() or formula.is_or():
            failed = mgr.And(activator, mgr.Not(formula))
        elif formula.node_type() == LTL_X:
            yz = mgr.FreshSymbol(template='LTL.X.YZ.%d')
            stvars.append(yz)
            pending = activator
            failed = mgr.And(yz, mgr.Not(formula.arg(0)))
            init.append(mgr.Not(yz))
            trans.append(mgr.Iff(mgr.Next(yz), activator))
        elif formula.node_type() == LTL_G:
            y_pending = mgr.FreshSymbol(template='LTL.G.YP.%d')
            stvars.append(y_pending)
            pending = mgr.Or(y_pending, activator)
            failed = mgr.And(pending, mgr.Not(formula.arg(0)))
            init.append(mgr.Not(y_pending))
            trans.append(mgr.Iff(mgr.Next(y_pending), pending))
        elif formula.node_type() == LTL_F:
            y_pending = mgr.FreshSymbol(template='LTL.F.YP.%d')
            stvars.append(y_pending)
            pending = mgr.And(mgr.Or(activator, y_pending), mgr.Not(formula.arg(0)))
            accept = mgr.Not(pending)
            init.append(mgr.Not(y_pending))
            trans.append(mgr.Iff(mgr.Next(y_pending), pending))
        elif formula.node_type() == LTL_U:
            y_pending = mgr.FreshSymbol(template='LTL.U.YP.%d')
            stvars.append(y_pending)
            pending = mgr.And(mgr.Or(activator, y_pending), mgr.Not(formula.arg(1)))
            accept = mgr.Not(pending)
            failed = mgr.And(pending, mgr.Not(formula.arg(0)))
            init.append(mgr.Not(y_pending))
            trans.append(mgr.Iff(mgr.Next(y_pending), pending))
        elif formula.node_type() == LTL_R:
            y_pending = mgr.FreshSymbol(template='LTL.R.YP.%d')
            stvars.append(y_pending)
            pending = mgr.And(mgr.Or(activator, y_pending), mgr.Not(formula.arg(0)))
            accept = mgr.Not(pending)
            failed = mgr.And(pending, mgr.Not(formula.arg(1)))
            init.append(mgr.Not(y_pending))
            trans.append(mgr.Iff(mgr.Next(y_pending), pending))
        else:
            raise NotImplementedError(
                f"Cannot create monitor for formula {formula}")
        return stvars, init, trans, accept, failed, pending

def ltl_circuit_encode (model, formula):
    '''Encodes an ltl property into a model by adding monitor circuits and returns the new model

    :param model: The model on which to encode the property
    :type model: pyvmt.model.Model
    :param prop: The property to encode, must be of type LTL
    :type prop: pyvmt.properties.Property
    :return: A new model with the added live property at index 0
    :rtype: pyvmt.model.Model
    '''
    model = _copy_model(model)
    env = model.get_env()
    mgr = env.formula_manager

    # convert the formula to NNF
    formula = mgr.Not(formula)
    formula = NNFIzer(environment=env).convert(formula)

    # find the subformulae
    walker = LtlCircuitEncodingWalker(formula)
    subf = walker.get_subformulae()

    is_init = mgr.FreshSymbol(template='is_init.%d')
    all_accept = []
    all_failed = []
    all_pending = []

    # replace the initial activator with is_init
    subf[len(subf) - 1] = ( is_init, subf[len(subf) - 1][1] )
    for activator, _ in subf:
        model.add_state_var(activator)
    model.add_init(is_init)
    model.add_trans(mgr.Iff(mgr.Next(is_init), mgr.FALSE()))

    # create the required monitors
    for activator, subformula in subf:
        stvars, init, trans, accept, failed, pending = \
            walker.make_monitor(is_init, activator, subformula)
        for f in stvars:
            model.add_state_var(f)
        for f in init:
            model.add_init(f)
        for f in trans:
            model.add_trans(f)
        all_accept.append(accept)
        all_failed.append(failed)
        all_pending.append(pending)

    has_failed = mgr.FreshSymbol(template='has_failed.%d')
    model.add_state_var(has_failed)
    model.add_init(mgr.Not(has_failed))
    model.add_trans(mgr.Iff(mgr.Next(has_failed), mgr.Or(*all_failed, has_failed)))

    accept, stvars, init, trans = make_single_justice(
        [mgr.And(f, mgr.Not(has_failed)) for f in all_accept]
    )
    for f in stvars:
        model.add_state_var(f)
    for f in init:
        model.add_init(f)
    for f in trans:
        model.add_trans(f)

    model.add_live_property(mgr.Not(accept))
    return model
