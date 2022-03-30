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
    Module for model composition
'''

from pyvmt.model import Model
from pyvmt import exceptions

def compose(model_a, model_b):
    '''Compose two models by means of synchronous composition.
    Creates a new model based on the two transition systems modeled to make them evolve in parallel.

    The new init and trans constraints will be formed by combining the
    constraints present in the two models.

    If properties are used within the two models the indexes must be distinct
    to avoid overlapping.

    If inputs from one model are state variables from the other, those inputs
    will be removed and only the state variable will be left, this allows
    the two models to exchange informations.

    The two models must be within the same environment for the composition to work.

    :param model_a: The first model
    :type model_a: pyvmt.model.Model
    :param model_b: The second model
    :type model_b: pyvmt.model.Model
    :return: A new model formed by composing the two models
    :rtype: pyvmt.model.Model
    '''
    if model_a.get_env() != model_b.get_env():
        raise exceptions.MismatchedEnvironmentError(
            "The two models being composed do not belong to the same environment")
    env = model_a.get_env()
    new_model = Model(env)

    # deal with variables
    all_inputs = set()
    all_state_variables = set()

    for model in (model_a, model_b):
        for state_var in model.get_state_vars():
            new_model.add_state_var(state_var)
            all_state_variables.add(state_var)

        # the inputs must be added after computing the actual
        # set of inputs by removing state variables
        all_inputs.update(model.get_input_vars())

    all_inputs.difference_update(new_model.get_state_vars())
    # add all the remaining inputs
    for input_var in all_inputs:
        new_model.add_input_var(input_var)

    # now that the variables are initialized all the other formulas can be
    # added to the model without the risk of undeclared variable errors
    for model in (model_a, model_b):
        for formula in model.get_init_constraints():
            new_model.add_init(formula)
        for formula in model.get_trans_constraints():
            new_model.add_trans(formula)
        for idx, prop in model.get_all_properties().items():
            new_model.add_property(prop.prop_type, prop.formula, property_idx=idx)

    return new_model
