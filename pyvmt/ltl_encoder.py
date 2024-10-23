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
from pyvmt.operators import (
    LTL_F, LTL_G, LTL_R, LTL_U, LTL_X, LTL_N, FUTURE_LTL,
    LTL_O, LTL_H, LTL_T, LTL_S, LTL_Y, LTL_Z, PAST_LTL,
    ALL_LTL, NNFIzer, XWeakener
)
from pyvmt.model import Model
from pyvmt.environment import get_env
from pyvmt.operators import IsSafetyLtl

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

    def walk_ltl_z(self, formula, args, **kwargs):
        '''Zf -> ¬(Y¬f)'''
        assert len(args) == 1
        return self.mgr.Not(self.mgr.Y(self.mgr.Not(args[0])))

    def walk_ltl_t(self, formula, args, **kwargs):
        '''fTg -> ¬(¬f S ¬g)'''
        assert len(args) == 2
        return self.mgr.Not(self.mgr.S(self.mgr.Not(args[0]), self.mgr.Not(args[1])))

    def walk_ltl_o(self, formula, args, **kwargs):
        '''Of -> T S f'''
        assert len(args) == 1
        return self.mgr.S(self.mgr.TRUE(), args[0])

    def walk_ltl_h(self, formula, args, **kwargs):
        '''Hf -> ¬(F ¬f)'''
        assert len(args) == 1
        return self.mgr.Not(self.mgr.S(self.mgr.TRUE(), self.mgr.Not(args[0])))

    def walk_ltl_n(self, formula, args, **kwargs):
        '''Nf -> ¬(X¬f)'''
        assert len(args) == 1
        return self.mgr.Not(self.mgr.X(self.mgr.Not(args[0])))

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

    @handles(LTL_F, LTL_G, LTL_R, LTL_Z, LTL_O, LTL_H, LTL_T, LTL_N)
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

    def walk_ltl_y(self, formula, args, **Kwargs):
        '''
        el(Y f) = el(f) union { Y f}
        sat(Y f) = el(Y f)
        '''
        assert len(args) == 1
        if formula not in self._el_map:
            self._el_map[formula] = self.mgr.FreshSymbol(formula.get_type(), 'el_y_%d')
        return self._el_map[formula]

    def walk_ltl_s(self, formula, args, **kwargs):
        '''
        el(f S g) = el(f) union el(g) union { Y(f S g) }
        sat(f S g) = sat(g) | (sat(f) & el(Y(f S g)))
        '''
        assert len(args) == 2
        y_formula = self.mgr.Y(formula)
        if y_formula not in self._el_map:
            stvar = self.mgr.FreshSymbol(formula.get_type(), 'el_s_%d')
            self._el_map[y_formula] = stvar
        return self.mgr.Or(args[1], self.mgr.And(args[0], self._el_map[y_formula]))

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
    formula = LtlRewriter(env=model.get_env()).rewrite(mgr.Not(formula))

    # get the elementary subformulae
    el_walker = LtlEncodingWalker(formula, env=model.get_env())
    el_map = el_walker.get_el_map()

    # create a new model with the same variables and constraints
    model = _copy_model(model)
    justice = []
    for el_, stvar in el_map.items():
        # add variables for the tableau
        model.add_state_var(stvar)
        sat = el_walker.get_sat(el_.arg(0))
        if el_.node_type() in FUTURE_LTL:
            # define how the variables evolve
            model.add_trans(mgr.EqualsOrIff(stvar, mgr.Next(sat)))
            if el_.arg(0).node_type() == LTL_U:
                # add the required justice
                justice.append(mgr.Or(mgr.Not(sat), el_walker.get_sat(el_.arg(0).arg(1))))
        else:
            # Past case: monitor is updated with the current value
            assert(el_.node_type() in PAST_LTL)
            model.add_trans(mgr.EqualsOrIff(mgr.Next(stvar), sat))

    model.add_init(el_walker.get_sat(formula))

    accept, stvars, init, trans = make_single_justice(justice)
    for f in stvars:
        model.add_state_var(f)
    for f in init:
        model.add_init(f)
    for f in trans:
        model.add_trans(f)

    model.add_live_property(mgr.Not(accept))
    return model

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
        :rtype: [( pysmt.fnode.FNode, pysmt.fnode.FNode )]
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
        elif formula.node_type() == LTL_Y:
            yarg = mgr.FreshSymbol(template='LTL.Y.arg.%d')
            stvars.append(yarg)
            init.append(mgr.Not(yarg))
            trans.append(mgr.Iff(mgr.Next(yarg), formula.arg(0)))
            failed = mgr.And(activator, mgr.Not(yarg))
        elif formula.node_type() == LTL_Z:
            zarg = mgr.FreshSymbol(template='LTL.Z.arg.%d')
            stvars.append(zarg)
            init.append(zarg)
            trans.append(mgr.Iff(mgr.Next(zarg), formula.arg(0)))
            failed = mgr.And(activator, mgr.Not(zarg))
        elif formula.node_type() == LTL_H:
            ynt = mgr.FreshSymbol(template='LTL.H.ynt.%d')
            stvars.append(ynt)
            init.append(mgr.Not(ynt))
            nt = mgr.Or(ynt, mgr.Not(formula.arg(0)))
            trans.append(mgr.Iff(mgr.Next(ynt), nt))
            failed = mgr.And(activator, nt)
        elif formula.node_type() == LTL_O:
            yt = mgr.FreshSymbol(template='LTL.O.yt.%d')
            stvars.append(yt)
            init.append(mgr.Not(yt))
            t = mgr.Or(yt, formula.arg(0))
            trans.append(mgr.Iff(mgr.Next(yt), t))
            failed = mgr.And(activator, mgr.Not(t))
        elif formula.node_type() == LTL_S:
            yt = mgr.FreshSymbol(template='LTL.S.yt.%d')
            stvars.append(yt)
            init.append(mgr.Not(yt))
            t = mgr.Or(formula.arg(1), mgr.And(yt, formula.arg(0)))
            trans.append(mgr.Iff(mgr.Next(yt), t))
            failed = mgr.And(activator, mgr.Not(t))
        elif formula.node_type() == LTL_T:
            ynt = mgr.FreshSymbol(template='LTL.T.ynt.%d')
            stvars.append(ynt)
            init.append(mgr.Not(ynt))
            nt = mgr.Or(mgr.Not(formula.arg(1)), mgr.And(ynt, mgr.Not(formula.arg(0))))
            trans.append(mgr.Iff(mgr.Next(ynt), nt))
            failed = mgr.And(activator, nt)
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

class LtlfEncodingWalker(LtlEncodingWalker):
    '''Walker to find the elementary formulae composing an LTLf formula, and
    the associated sat values.

    The walker assumes that the formula has already been rewritten in terms
    of X, Y, U, and Not, using the LtlRewriter and then NNFized with NNFizer.
    '''

    def __init__(self, formula, env=None):
        super().__init__(formula, env=env)

    @handles(LTL_F, LTL_G, LTL_O, LTL_H)
    def walk_ltl_unsupported(self, formula, args, **kwargs):
        '''Raise an error on use of unsupported operator'''
        raise NotImplementedError(
            f"Formula must not contain {formula.node_type} operators, "\
            "please, use the LtlRewriter to leave only U and X LTL operators.")

    def walk_ltl_n(self, formula, args, **kwargs):
        '''
        el(X f) = el(f) union { X f }
        sat(X f) = el(X f)
        '''
        assert len(args) == 1
        if formula not in self._el_map:
            self._el_map[formula] = self.mgr.FreshSymbol(formula.get_type(), 'el_n_%d')
        return self._el_map[formula]

    def walk_ltl_z(self, formula, args, **Kwargs):
        '''
        el(Z f) = el(f) union { Z f}
        sat(Z f) = el(Z f)
        '''
        assert len(args) == 1
        if formula not in self._el_map:
            self._el_map[formula] = self.mgr.FreshSymbol(formula.get_type(), 'el_z_%d')
        return self._el_map[formula]

    def walk_ltl_r(self, formula, args, **kwargs):
        '''
        el(f R g) = el(f) union el(g) union { N(f R g) }
        sat(f R g) = sat(g) & (sat(f) | el(N(f R g)))
        '''
        assert len(args) == 2
        n_formula = self.mgr.N(formula)
        if n_formula not in self._el_map:
            stvar = self.mgr.FreshSymbol(formula.get_type(), 'el_r_%d')
            self._el_map[n_formula] = stvar
        return self.mgr.And(args[1], self.mgr.Or(args[0], self._el_map[n_formula]))

    def walk_ltl_t(self, formula, args, **kwargs):
        '''
        el(f T g) = el(f) union el(g) union { Z(f T g) }
        sat(f T g) = sat(g) & (sat(f) | el(Z(f T g)))
        '''
        assert len(args) == 2
        z_formula = self.mgr.Z(formula)
        if y_formula not in self._el_map:
            stvar = self.mgr.FreshSymbol(formula.get_type(), 'el_t_%d')
            self._el_map[y_formula] = stvar
        return self.mgr.And(args[1], self.mgr.Or(args[0], self._el_map[z_formula]))

def ltlf_encode(model, formula):
    '''Encodes an ltlf property into a model and returns the new model

    :param model: The model on which to encode the property
    :type model: pyvmt.model.Model
    :param prop: The property to encode, must be of type LTL
    :type prop: pyvmt.properties.Property
    :return: A new model with the added invar property at index 0
    :rtype: pyvmt.model.Model
    '''
    env = model.get_env()
    mgr = env.formula_manager
    # rewrite the formula in terms of X and U operators
    formula = LtlRewriter(env=model.get_env()).rewrite(mgr.Not(formula))
    # Use negative normal form on the resulting formula
    formula = NNFIzer(environment=env).convert(formula)

    # get the elementary subformulae
    el_walker = LtlfEncodingWalker(formula, env=model.get_env())
    el_map = el_walker.get_el_map()

    # create a new model with the same variables and constraints
    model = _copy_model(model)

    x_vars = []
    for el_, stvar in el_map.items():
        # add variables for the tableau
        model.add_state_var(stvar)
        sat = el_walker.get_sat(el_.arg(0))
        if el_.node_type() in FUTURE_LTL:
            # define how the variables evolve using implication
            model.add_trans(mgr.Implies(stvar, mgr.Next(sat)))
            # Strong proof obligations must be falsified to reach the counter-example
            if el_.node_type() == LTL_X:
                x_vars.append(stvar)
        else:
            # Past case: monitor is updated with the current value
            assert(el_.node_type() in PAST_LTL)
            # TODO[AB]: Check this!!
            model.add_trans(mgr.EqualsOrIff(mgr.Next(stvar), sat))

    model.add_init(el_walker.get_sat(formula))

    # compute invariant (bigvee_{v_{X phi}} v_{X phi})
    invar = mgr.FALSE()
    for v_x in x_vars:
        invar = mgr.Or(invar, v_x)

    model.add_invar_property(invar)

    return model

def safetyltl_encode(model, formula):
    '''Encodes a safety ltl property into a model and returns the new model

    We assume that formula does not contain U/F operators occuring positively

    :param model: The model on which to encode the property
    :type model: pyvmt.model.Model
    :param prop: The property to encode, must be of type LTL
    :type prop: pyvmt.properties.Property
    :return: A new model with the added invar property at index 0. None if the
    property is not in safetyLTL
    :rtype: pyvmt.model.Model
    '''
    env = model.get_env()

    # Use negative normal form on the resulting formula
    formula = NNFIzer(environment=env).convert(formula)
    # If the formula is NOT safetyLTL the encoding is not correct
    if not IsSafetyLtl().is_safety_ltl(formula):
        return None

    # Weaken next from safety formula
    formula = XWeakener(env).remove_strong_next(formula)

    # Do the actual encoding using LTLf encoder
    return ltlf_encode(model, formula)
