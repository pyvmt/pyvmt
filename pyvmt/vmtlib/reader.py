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
    Exports a reader for VMT-LIB scripts
'''

from pyvmt.vmtlib.parser import VmtLibParser
from pyvmt.environment import get_env
from pyvmt.model import Model
from pyvmt.vmtlib.annotations import NEXT, INIT, TRANS, ANNOTS_PROPERTIES_MAP
from pyvmt import exceptions

def read(stream, env=None):
    '''Reads a VMT-LIB script and returns the Model

    :param stream: The stream to read from
    :type stream: TextIOWrapper
    :param env: the environment to use to store the variables, defaults to the global environment
    :type env: pyvmt.environment.Environment, optional
    :return: A Model generated from the VMT-LIB script
    :rtype: pyvmt.model.Model
    '''
    if env is None:
        env = get_env()
    mgr = env.formula_manager
    substituter = env.substituter

    model = Model(env=env)

    parser = VmtLibParser(environment=env)
    smt_script = parser.get_script(stream)
    extra_declarations = smt_script.get_declared_symbols()
    ann = smt_script.annotations

    next_replacements = {}

    # find all 'next' annotations
    for formula in ann.all_annotated_formulae(NEXT):
        annotations = ann.annotations(formula)[NEXT]
        # check if there there is exactly one next annotation for the formula

        for annotation in annotations:
            next_variable = mgr.get_symbol(annotation)
            model.add_state_var(formula)

            # remove the state variable curr and next from the extra declarations
            extra_declarations.remove(formula)
            extra_declarations.remove(next_variable)
            next_replacements[next_variable] = mgr.Next(formula)

        # there should only be one annotation
        # if multiple annotations are found a DuplicateDeclarationError
        # should have been raised
        assert len(annotations) == 1

    for formula in extra_declarations:
        # remaining declarations can be treated as inputs
        model.add_input_var(formula)

    # find all the init annotations
    for formula in ann.all_annotated_formulae(INIT):
        annotations = ann.annotations(formula)[INIT]
        # check the value of the annotations
        if not all(x == 'true' for x in annotations):
            raise exceptions.InvalidAnnotationValueError(
                "Init annotations can only evaluate to true")
        formula = substituter.substitute(formula, subs=next_replacements)
        model.add_init(formula)

    # find all the trans annotations
    for formula in ann.all_annotated_formulae(TRANS):
        annotations = ann.annotations(formula)[TRANS]
        # check the value of the annotations
        if not all(x == 'true' for x in annotations):
            raise exceptions.InvalidAnnotationValueError(
                "Trans annotations can only evaluate to true")
        formula = substituter.substitute(formula, subs=next_replacements)
        model.add_trans(formula)

    # find all the invar-property annotations
    for prop_annotation, prop_type in ANNOTS_PROPERTIES_MAP.items():
        for formula in ann.all_annotated_formulae(prop_annotation):
            annotations = ann.annotations(formula)[prop_annotation]

            for annotation in annotations:
                try:
                    property_idx = int(annotation)
                except ValueError:
                    # the property index is not a valid integer
                    raise exceptions.InvalidPropertyIdxError(
                        f"Annotation {annotation} is not a valid property idx") from ValueError
                formula = substituter.substitute(formula, subs=next_replacements)
                model.add_property(prop_type, formula, property_idx=property_idx)

    return model
