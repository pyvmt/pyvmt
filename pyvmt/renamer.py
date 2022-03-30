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
    Exports utility functions to change the name of variables within a model
'''

from pysmt.substituter import MGSubstituter
from pyvmt.model import Model
from pyvmt import exceptions

def _replace_prefix_callback(prefix, replacement, check_prefixes):
    def resf(name):
        if name.startswith(prefix):
            return replacement + name.removeprefix(prefix)
        if check_prefixes:
            raise exceptions.IncorrectSymbolNameError(
                f"Symbol {name} does not have prefix {prefix}")
        return name
    return resf

def _replace_suffix_callback(suffix, replacement, check_suffixes):
    def resf(name:str):
        if name.endswith(suffix):
            return name.removesuffix(suffix) + replacement
        if check_suffixes:
            raise exceptions.IncorrectSymbolNameError(
                f"Symbol {name} does not have suffix {suffix}")
        return name
    return resf

def _rename_symbol(symbol, callback, env):
    res = callback(symbol.symbol_name())
    if not isinstance(res, str):
        raise exceptions.PyvmtTypeError(
            f"Renamer callback type is invalid, expected {str}, {type(res)} found")
    return env.formula_manager.Symbol(res, symbol.get_type())

def add_prefix(model, prefix):
    '''Rename the model by adding a prefix to the variables of the model.

    :param model: The model to rename
    :type model: pyvmt.model.Model
    :param prefix: The prefix to add
    :type prefix: str
    :return: The renamed model
    :rtype: pyvmt.model.Model
    '''
    return replace_prefix(model, '', prefix)

def replace_prefix(model, prefix, replacement, strict = True):
    '''Rename the model by replacing the prefix of all the variables with a new prefix.

    If strict is True all the original variable names must have the
    prefix being replaced otherwise an exception will be raised.

    :param model: The model to rename
    :type model: pyvmt.model.Model
    :param prefix: The prefix to replace
    :type prefix: str
    :param replacement: The replacement for the prefix
    :type replacement: str
    :param strict: Whether to check if the prefix is always present, defaults to True
    :type strict: bool, optional
    :return: The renamed model
    :rtype: pyvmt.model.Model
    '''
    return rename(model, _replace_prefix_callback(prefix, replacement,
        check_prefixes=strict))

def add_suffix(model, suffix):
    '''Rename the model by adding a suffix to the variables of the model.

    :param model: The model to rename
    :type model: pyvmt.model.Model
    :param suffix: The suffix to add
    :type suffix: str
    :return: The renamed model
    :rtype: pyvmt.model.Model
    '''
    return replace_suffix(model, '', suffix)

def replace_suffix(model, suffix, replacement, strict = True):
    '''Rename the model by replacing the suffix of all the variables with a new suffix.

    If strict is True all the original variable names must have the
    suffix being replaced otherwise an exception will be raised.

    :param model: The model to rename
    :type model: pyvmt.model.Model
    :param suffix: The suffix to replace
    :type suffix: str
    :param replacement: The replacement for the suffix
    :type replacement: str
    :param strict: Whether to check if the suffix is always present, defaults to True
    :type strict: bool, optional
    :return: The renamed model
    :rtype: pyvmt.model.Model
    '''
    return rename(model, _replace_suffix_callback(suffix, replacement,
        check_suffixes=strict))

def rename(model, callback):
    '''Rename all the variables within the model using a callback function.
    The callback function must take as parameter a string and return a string.

    :param model: The model to rename
    :type model: pyvmt.model.Model
    :param callback: The callback that defines how to rename the variables
    :type callback: Callable[[str], str]
    :return: The renamed model
    :rtype: pyvmt.model.Model
    '''
    env = model.get_env()
    new_model = Model(env=env)
    subs = {}

    # since the same formulas are used for substitution
    # there's no need to invalidate the memoization
    substituter = MGSubstituter(env)
    substituter.invalidate_memoization = False

    # get the new names for the state variables and the inputs
    for state_var in model.get_state_vars():
        new_state_var = _rename_symbol(state_var, callback, env)
        subs[state_var] = new_state_var

        # add the state variable
        new_model.add_state_var(new_state_var)

    for input_var in model.get_input_vars():
        new_input = _rename_symbol(input_var, callback, env)
        new_model.add_input_var(new_input)

        # add the input variable
        subs[input_var] = new_input

    # all the other formulas need to be have the symbols replaced accordingly
    for formula in model.get_init_constraints():
        new_model.add_init(substituter.substitute(formula, subs=subs))
    for formula in model.get_trans_constraints():
        new_model.add_trans(substituter.substitute(formula, subs=subs))
    for idx, prop in model.get_all_properties().items():
        new_formula = substituter.substitute(prop.formula, subs=subs)
        new_model.add_property(prop.prop_type, new_formula, property_idx=idx)
    return new_model
