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
    The Model class, which can be used to store a transition model,
    offers a variety of utility functions to interact with the model,
    and can be serialized to VMT-LIB
'''

from pysmt.smtlib.parser import Annotations, SmtLibCommand
from pysmt import typing
from pysmt.logics import Theory, Logic, get_closer_pysmt_logic
from pyvmt.environment import Environment, get_env
from pyvmt.vmtlib.commands import DECLARE_FUN, ASSERT, DEFINE_FUN
from pyvmt.vmtlib import annotations as vmt_annotations
from pyvmt.substituters import VmtLibSubstituter
from pyvmt import exceptions
from pyvmt.vmtlib.printers import VmtDagPrinter, VmtPrinter
from pyvmt.properties import VmtProperty, INVAR_PROPERTY, LIVE_PROPERTY, LTL_PROPERTY

class Model:
    '''
        Class to hold the information about a transition model
    '''

    _state_vars: list
    _inputs: set
    _init: list
    _trans: list
    _properties: dict
    _next_property_idx: int
    _environment: Environment

    def __init__(self, env = None):
        self._init = []
        self._state_vars = set()
        self._trans = []
        self._properties = {}
        self._next_property_idx = 0
        self._inputs = set()

        # if no environment is passed to the class the global environment is used by default
        if env is None:
            env = get_env()
        self._environment = env

    def _is_declared(self, formula):
        return self.is_input_variable(formula) or \
               self.is_state_variable(formula)

    def _check_duplicate_variable(self, formula):
        if self._is_declared(formula):
            raise exceptions.DuplicateDeclarationError(
                f"Cannot redeclare symbol {formula}")

    def _check_all_symbols_declared(self, formula):
        # check that all variables are declared
        for variable in formula.get_free_variables():
            if not self._is_declared(variable):
                raise exceptions.UndeclaredSymbolError(
                    f"{variable} is undeclared")

    def get_env(self):
        '''Retrieve the environment for the model

        :return: The environment of the model
        :rtype: pyvmt.environment.Environment
        '''
        return self._environment

    def add_input_var(self, symbol):
        '''Adds a new input to the model.
        The symbol can then be used as part of properties and transition constraints,
        but it cannot be used as part of an init constraint.

        :param symbol: The symbol to add as input, the same symbol cannot be
            used as a state variable
        :type symbol: pysmt.fnode.FNode
        '''
        if not symbol.is_symbol():
            raise exceptions.NotSymbolError(
                "Only symbols can be added as inputs")
        self._check_duplicate_variable(symbol)

        self._inputs.add(symbol)

    def add_state_var(self, variable):
        '''Adds a new state variable to the model.
        The variable can then be used as part of properties and transition constraints.
        The variable in the next state can be generated using the Next operator or
        the next method of the model.

        :param variable: The curr state variable
        :type variable: pysmt.fnode.FNode
        '''
        # variables must be symbols
        if not variable.is_symbol():
            raise exceptions.NotSymbolError(
                "State variables must be symbols")
        self._check_duplicate_variable(variable)
        self._state_vars.add(variable)

    def create_state_var(self, variable_name, variable_type):
        '''Create a new state variable from the name and the type.
        The variables will be added to the list of state variables.
        The variable in the next state can be generated using the Next operator or
        the next method of the model.

        :param variable_name: The name of the curr state variable
        :type variable_name: str
        :param variable_type: The type of the state variable
        :type variable_type: pysmt.typing.PySMTType
        :return: The symbol of the newly generated variable
        :rtype: pysmt.fnode.FNode
        '''
        mgr = self.get_env().formula_manager
        variable = mgr.Symbol(variable_name, variable_type)
        self.add_state_var(variable)
        return variable

    def create_frozen_var(self, variable_name, variable_type):
        '''Create a new frozen state variable from name and type.
        This function works similarly to create_state_var, but it also adds
        a transition constraint to ensure that the variable never changes once initialized.

        :param variable_name: The name of the curr state variable
        :type variable_name: str
        :param variable_type: The type of the state variable
        :type variable_type: pysmt.typing.PySMTType
        :return: The symbol corresponding to the frozen variable
        :rtype: pysmt.fnode.FNode
        '''
        variable = self.create_state_var(variable_name, variable_type)

        mgr = self._environment.formula_manager

        self.add_trans(mgr.EqualsOrIff(variable, mgr.Next(variable)))
        return variable

    def get_state_vars(self):
        '''Returns a list of the model's state variables

        :return: A list containing the model state variables
        :rtype: List[pysmt.fnode.FNode]
        '''
        return list(self._state_vars)

    def create_input_var(self, variable_name, variable_type):
        '''Create a new input from name and type.
        The new variable will be added to the list of inputs.

        :param variable_name: The name of the input
        :type variable_name: str
        :param variable_type: The type of the input
        :type variable_type: pysmt.typing.PySMTType
        :return: The symbol corresponding to the input
        :rtype: pysmt.fnode.FNode
        '''
        mgr = self._environment.formula_manager
        variable = mgr.Symbol(variable_name, variable_type)
        self.add_input_var(variable)
        return variable

    def get_input_vars(self):
        '''Returns a copy of the model input variables

        :return: A list containing the model input variables
        :rtype: List[pysmt.fnode.FNode]
        '''
        return list(self._inputs)

    def get_all_vars(self):
        '''Returns a list of the model's variables

        :return: A list containing the model variables
        :rtype: List[pysmt.fnode.FNode]
        '''
        return self.get_state_vars() + self.get_input_vars()

    def add_invar(self, formula):
        '''Add a new invariant to the model.
        Since an invariant adds both an init and a trans constraint,
        the formula can only contain curr state variables.

        :param formula: The new invariant
        :type formula: pysmt.fnode.FNode
        '''
        self.add_init(formula)
        self.add_trans(formula)
        self.add_trans(self.next(formula))

    def add_init(self, formula):
        '''Add a new init constraint to the model.
        This defines how the initial state for the model can be built.
        An init constraint can only contain curr state variables.
        The formula must be of boolean type.

        :param formula: The init constraint to add
        :type formula: pysmt.fnode.FNode
        '''
        for variable in formula.get_free_variables():
            # an init constraint can only contain curr state variables
            if not self.is_state_variable(variable):
                raise exceptions.StateVariableError(
                    f"Init constraints cannot contain {variable} "
                    "since it's not a curr state variable")
        if self.get_env().has_ltl_operators_walker.has_ltl(formula):
            raise exceptions.UnexpectedLtlError(
                "Init constraints cannot contain LTL")
        if self.get_env().has_next_operator_walker.has_next(formula):
            raise exceptions.UnexpectedNextError(
                "Init constraints cannot contain the Next operator")

        if formula.get_type() != typing.BOOL:
            raise exceptions.PyvmtTypeError(
                f"Init constraints must be of type {typing.BOOL}, {formula.get_type()} found")
        self._init.append(formula)

    def add_trans(self, formula):
        '''Add a new trans constraint to the model.
        This defines how the model can transition from one state to the next.
        All the variables in the formula must be declared as either inputs or state variables.
        The formula must be of boolean type.

        :param formula: The trans constraint to add
        :type formula: pysmt.fnode.FNode
        '''
        self._check_all_symbols_declared(formula)

        if formula.get_type() != typing.BOOL:
            raise exceptions.PyvmtTypeError(
                f"Trans constraints must be of type {typing.BOOL}, {formula.get_type()} found")
        if self.get_env().has_ltl_operators_walker.has_ltl(formula):
            raise exceptions.UnexpectedLtlError(
                "Trans constraints cannot contain LTL")
        self._trans.append(formula)

    def _is_property_idx_free(self, property_idx):
        return property_idx not in self._properties

    def _get_free_property_idx(self):
        while not self._is_property_idx_free(self._next_property_idx):
            self._next_property_idx+= 1
        property_idx = self._next_property_idx
        self._next_property_idx+= 1
        return property_idx

    def _check_property_idx(self, property_idx):
        if not isinstance(property_idx, int) or property_idx < 0:
            raise exceptions.InvalidPropertyIdxError(
                f"{property_idx} is not a valid property index")
        if not self._is_property_idx_free(property_idx):
            raise exceptions.DuplicatePropertyIdxError(
                f"Duplicate property index {property_idx}")
        return True

    def add_property(self, property_type, formula, property_idx=None):
        '''Add a new property to the model.
        This property can then be used as part of verification.
        The formula must be of boolean type.

        :param formula: The property to check
        :type formula: pysmt.fnode.FNode
        :param property_type: The type of the property
        :type property_type: One of pyvmt.properties.PROPERTY_TYPES
        :param property_idx: The index of the property, if None is passed a new one is generated
        :type property_idx: int, optional
        :return: The index of the property, can be used to retrieve the property
        :rtype: int
        '''
        if property_idx is None:
            property_idx = self._get_free_property_idx()

        self._check_property_idx(property_idx)
        self._check_all_symbols_declared(formula)

        self._properties[property_idx] = VmtProperty(property_type, formula)
        return property_idx

    def add_invar_property(self, formula, property_idx=None):
        '''Add a new invar property to the model.
        This property can then be used as part of verification.
        The form of an invar property in LTL is G (formula).
        The formula must be of boolean type.

        :param formula: The invariant property to check
        :type formula: pysmt.fnode.FNode
        :param property_idx: The index of the property, if None is passed a new one is generated
        :type property_idx: int, optional
        :return: The index of the property, can be used to retrieve the property
        :rtype: int
        '''
        return self.add_property(INVAR_PROPERTY, formula, property_idx=property_idx)

    def add_live_property(self, formula, property_idx=None):
        '''Add a new live property to the model.
        This property can then be used as part of verification.
        The form of an live property in LTL is F G (formula).
        The formula must be of boolean type.

        :param formula: The live property to check
        :type formula: pysmt.fnode.FNode
        :param property_idx: The index of the property, if None is passed a new one is generated
        :type property_idx: int, optional
        :return: The index of the property, can be used to retrieve the property
        :rtype: int
        '''
        return self.add_property(LIVE_PROPERTY, formula, property_idx=property_idx)

    def add_ltl_property(self, formula, property_idx=None):
        '''Add a new LTL property to the model.
        This property can then be used as part of verification.
        This kind of property can contain LTL operators.
        The formula must be of boolean type.

        :param formula: The LTL property to check
        :type formula: pysmt.fnode.FNode
        :param property_idx: The index of the property, if None is passed a new one is generated
        :type property_idx: int, optional
        :return: The index of the property, can be used to retrieve the property
        :rtype: int
        '''
        return self.add_property(LTL_PROPERTY, formula, property_idx=property_idx)

    def add_ltlf_property(self, formula, property_idx=None):
        '''Add a new LTLf property to the model.
        This property can then be used as part of verification.
        This kind of property can contain LTLf operators.
        The formula must be of boolean type.

        :param formula: The LTLf property to check
        :type formula: pysmt.fnode.FNode
        :param property_idx: The index of the property, if None is passed a new one is generated
        :type property_idx: int, optional
        :return: The index of the property, can be used to retrieve the property
        :rtype: int
        '''
        return self.add_property(LTLF_PROPERTY, formula, property_idx=property_idx)

    def get_property(self, property_idx):
        '''Get the property identified by property_idx

        :param property_idx: The index of the property
        :type property_idx: int
        :return: The property identified by property_idx
        :rtype: pyvmt.properties.VmtProperty
        '''
        try:
            return self._properties[property_idx]
        except KeyError:
            raise exceptions.PropertyNotFoundError(
                f"Property with index {property_idx} not found"
            ) from KeyError

    def get_invar_properties(self):
        '''Get a dict with all the model invar properties.

        :return: A dict containing the invar properties,
            where the key is the property index and the value is the property
        :rtype: Dict[int, pyvmt.properties.VmtProperty]
        '''
        return { k: x for k, x in self._properties.items() if x.is_invar() }

    def get_live_properties(self):
        '''Get a dict with all the model live properties.

        :return: A dict containing the live properties,
            where the key is the property index and the value is the property
        :rtype: Dict[int, pyvmt.properties.VmtProperty]
        '''
        return { k: x for k, x in self._properties.items() if x.is_live() }

    def get_ltl_properties(self):
        '''Get a dict with all the model LTL properties.

        :return: A dict containing the LTL properties,
            where the key is the property index and the value is the property
        :rtype: Dict[int, pyvmt.properties.VmtProperty]
        '''
        return { k: x for k, x in self._properties.items() if x.is_ltl() }

    def get_ltlf_properties(self):
        '''Get a dict with all the model LTLf properties.

        :return: A dict containing the LTLf properties,
            where the key is the property index and the value is the property
        :rtype: Dict[int, pyvmt.properties.VmtProperty]
        '''
        return { k: x for k, x in self._properties.items() if x.is_ltlf() }

    def get_all_properties(self):
        '''Get a dict with all the model properties.

        :return: A dict containing all the properties,
            where the key is the property index and the value is the property
        :rtype: Dict[int, pyvmt.properties.VmtProperty]
        '''
        return self._properties.copy()

    def is_input_variable(self, formula):
        '''Determines if a formula is an input variable

        :param formula: The variable to check
        :type formula: pysmt.fnode.FNode
        :return: True if the formula corresponds to an input variable, False otherwise
        :rtype: bool
        '''
        #TODO this could raise an exception if the passed variable is not a symbol
        return formula.is_symbol() and formula in self._inputs

    def is_state_variable(self, formula):
        '''Determines if a formula is a state variable

        :param formula: The variable to check
        :type formula: pysmt.fnode.FNode
        :return: True if the formula corresponds to a state variable, False otherwise
        :rtype: bool
        '''
        #TODO this could raise an exception if the passed variable is not a symbol
        return formula.is_symbol() and formula in self._state_vars

    def get_init_constraints(self):
        '''Get the list of init constraints

        :return: The list of init constraints
        :rtype: List[pysmt.fnode.FNode]

        .. warning::
            To save memory this function does not create a copy of the init constraints.

            To avoid unwanted side effects the list should be considered immutable.
            If changes need to be made, a copy should be created by using the list.copy function.
        '''
        return self._init

    def get_init_constraint(self):
        '''Get a single formula containing all of the init constraints.
        Obtained by performing the conjunction of all the init constraints.

        :return: The init constraint for the model
        :rtype: pysmt.fnode.FNode
        '''
        mgr = self.get_env().formula_manager
        return mgr.And(self._init)

    def get_trans_constraints(self):
        '''Get the list of trans constraints

        :return: The list of trans constraints
        :rtype: List[pysmt.fnode.FNode]

        .. warning::
            To save memory this function does not create a copy of the trans constraints.

            To avoid unwanted side effects the list should be considered immutable.
            If changes need to be made, a copy should be created by using the list.copy function.
        '''
        return self._trans

    def get_trans_constraint(self):
        '''Get a single formula containing all of the trans constraints.
        Obtained by performing the conjunction of all the trans constraints.

        :return: The trans constraint for the model
        :rtype: pysmt.fnode.FNode
        '''
        mgr = self.get_env().formula_manager
        return mgr.And(self._trans)

    def next(self, formula):
        '''Returns a formula corresponding to the current formula in the next state.
        The formula cannot contain next state variables.

        :param formula: The formula in the curr state
        :type formula: pysmt.fnode.FNode
        :return: The formula in the next state
        :rtype: pysmt.fnode.FNode
        '''
        mgr = self.get_env().formula_manager
        return mgr.Next(formula)

    def get_theory(self, extra_formulae=None):
        '''Get the theory for the whole model, currently ignores properties.

        :param extra_formulae: Extra formulae to add, can be used to check the theory
            for the model with the properties, defaults to None
        :type extra_formulae: Iterable[pysmt.fnode.FNode], optional
        :return: The theory for the model.
        :rtype: pysmt.logics.Theory
        '''
        #TODO should this deal with properties as well?
        theoryo = self.get_env().theoryo
        all_formulae = [
            *self.get_init_constraints(),
            *self.get_trans_constraints(),
            *self.get_input_vars(),
            *self.get_state_vars()
        ]
        if extra_formulae is not None:
            all_formulae.extend(extra_formulae)
        theory_out = Theory()

        for formula in all_formulae:
            formula_th = theoryo.get_theory(formula)
            theory_out = theory_out.combine(formula_th)
        return theory_out

    def get_logic(self, extra_formulae=None):
        '''Get the closest pysmt logic for the whole model, currently ignores properties.

        :param extra_formulae: Extra formulae to add, can be used to check the logic
            for the model with the properties, defaults to None
        :type extra_formulae: Iterable[pysmt.fnode.FNode], optional
        :return: The theory for the model.
        :rtype: pysmt.logics.Theory
        '''
        #TODO should this deal with properties as well?
        qfo = self.get_env().qfo

        is_qf = qfo.is_qf(self.get_init_constraint()) and \
                qfo.is_qf(self.get_trans_constraint())
        if extra_formulae is not None:
            is_qf = is_qf and all(qfo.is_qf(x) for x in extra_formulae)

        theory = self.get_theory(extra_formulae=extra_formulae)
        logic = Logic("Detected Model Logic", "", quantifier_free=is_qf, theory=theory)
        return get_closer_pysmt_logic(logic)

    def serialize(self, outstream, daggify=True, properties=None):
        '''Serialize the model to a VMT-LIB script.
        An equivalent model is created by adding declarations for all the variables,
        and functions containing the annotations for init, trans, invar-property,
        and live-property.

        :param outstream: The outstream to use for serialization
        :param daggify: Whether the output should be daggified, defaults to True
        :type daggify: bool, optional
        '''
        # This function was originally implemented by creating a script, adding the required
        # commands and annotations, and serializing it.
        # This was changed to avoid printing the same annotation twice, for example redeclaring
        # a next state variable relation, to avoid potential issues with solvers that treat
        # this as a redeclaration

        mgr = self.get_env().formula_manager
        # define a next state variable for each curr state variable
        next_symbols = {
            x: mgr.FreshSymbol(x.symbol_type(), x.symbol_name().replace('%', '%%') + '.__next%d')
            for x in self._state_vars
        }
        vmt_lib_subs = VmtLibSubstituter(next_symbols, env=self.get_env())
        printed_functions = {}

        if daggify:
            printer = VmtDagPrinter(outstream)
        else:
            printer = VmtPrinter(outstream)

        def serialize_command(name, args, annotations=None):
            # function to serialize a command to the printer, specifying the annotations
            # that have to be passed to the printer
            printer.annotations = annotations
            SmtLibCommand(name, args).serialize(printer=printer)
            printer.write('\n')

        def serialize_ann(formula, annotation_type, value):
            # function to serialize an annotated formula, creates the Annotations object, defines
            # the function arguments and calls the serialization function
            printed_functions.setdefault(annotation_type, 0)
            formula = vmt_lib_subs.replace(formula)
            ann = Annotations()
            ann.add(formula, annotation_type, value=value)

            serialize_command(DEFINE_FUN, [
                f'{annotation_type}{printed_functions[annotation_type]}',
                [],
                formula.get_type(),
                formula
            ], annotations=ann)
            printed_functions[annotation_type]+= 1

        # serialize all of the inputs
        for variable in self._inputs:
            serialize_command(DECLARE_FUN, [variable])

        # serialize all of the state variables
        for variable, next_var in next_symbols.items():
            serialize_command(DECLARE_FUN, [variable])
            serialize_command(DECLARE_FUN, [next_var])
            serialize_ann(variable, vmt_annotations.NEXT, next_var.to_smtlib())

        # serialize the init constraint
        serialize_ann(self.get_init_constraint(), vmt_annotations.INIT, 'true')

        # serialize the trans constraint
        serialize_ann(self.get_trans_constraint(), vmt_annotations.TRANS, 'true')

        # check that all the passed properties are valid within the model
        if properties is not None:
            for idx, prop in properties.items():
                self._check_all_symbols_declared(prop.formula)
        else:
            # by default serialize all of the properties
            properties = self.get_all_properties()

        # serialize the properties
        for idx, prop in properties.items():
            serialize_ann(prop.formula, vmt_annotations.PROPERTIES_ANNOTS_MAP[prop.prop_type], idx)

        # add ASSERT true at the end of the script
        serialize_command(ASSERT, [mgr.TRUE()])

    def __str__(self):
        # HR serialization, useful for debugging
        res = []
        mgr = self._environment.formula_manager
        res.append('--- State variables ---')
        for cur in self.get_state_vars():
            res.append(f'{cur.get_type()} {cur}, next({cur}) = {mgr.Next(cur)}')
        res.append('')
        res.append('--- Input variables ---')
        for var in self.get_input_vars():
            res.append(f'{var.get_type()} {var}')
        res.append('')
        res.append('--- Init constraints ---')
        for formula in self.get_init_constraints():
            res.append(f'{formula}')
        res.append('')
        res.append('--- Trans constraints ---')
        for formula in self.get_trans_constraints():
            res.append(f'{formula}')
        res.append('')
        res.append('--- Properties ---')
        for idx, prop in self.get_all_properties().items():
            res.append(f'{idx}) {prop}')
        res.append('')
        return '\n'.join(res)
