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
'''Module containing the available property types in PyVmt

It also exports the VmtProperty class which is a wrapper around a formula
'''

from pyvmt import exceptions
from pyvmt.environment import get_env
from pysmt import typing

# Types of properties available in PyVmt

#: Invar property, property in the form G (formula)
INVAR_PROPERTY = 'invar'

#: Live property, property in the form F G (formula)
LIVE_PROPERTY = 'live'

#: LTL property, can contain LTL operators within the formula
LTL_PROPERTY = 'ltl'

LTLF_PROPERTY = 'ltlf'
#: Complete list of available property types
PROPERTY_TYPES = frozenset([
    INVAR_PROPERTY,
    LIVE_PROPERTY,
    LTL_PROPERTY,
    LTLF_PROPERTY,
])

class VmtProperty:
    '''Class to contain a VMT property.

    The type must be one of the available property types:
    INVAR_PROPERTY, LIVE_PROPERTY, or LTL_PROPERTY.

    The formula must be of boolean type.
    It can only contain LTL operators if the type of the formula is LTL_PROPERTY.
    '''

    def __init__(self, prop_type, formula):
        # the property type must be valid
        if prop_type not in PROPERTY_TYPES:
            raise exceptions.InvalidPropertyTypeError(
                f"Property type must be one of {', '.join(PROPERTY_TYPES)}")

        # the formula must be boolean
        if formula.get_type() != typing.BOOL:
            raise exceptions.PyvmtTypeError(
                f"LTL properties must be of type {typing.BOOL}, {formula.get_type()} found")

        # the formula cannot contain LTL, unless it's an LTL_PROPERTY
        ltlop_walker = get_env().has_ltl_operators_walker
        if prop_type != LTL_PROPERTY and prop_type != LTLF_PROPERTY and ltlop_walker.has_ltl(formula):
            raise exceptions.UnexpectedLtlError(
                f"{prop_type} properties cannot contain LTL, use {LTL_PROPERTY} properties instead")
        self._prop_type = prop_type
        self._formula = formula

    @property
    def formula(self):
        '''The formula of the property

        :rtype: pysmt.fnode.FNode
        '''
        return self._formula

    @property
    def prop_type(self):
        '''The type of the property

        :return: One of pyvmt.properties.PROPERTY_TYPES
        :rtype: str
        '''
        return self._prop_type

    def __str__(self):
        return f'{self.prop_type} prop: {self.formula}'

    def is_invar(self):
        '''Returns True if the property is an invar property, False otherwise
        '''
        return self.prop_type == INVAR_PROPERTY

    def is_live(self):
        '''Returns True if the property is a live property, False otherwise
        '''
        return self.prop_type == LIVE_PROPERTY

    def is_ltl(self):
        '''Returns True if the property is an ltl property, False otherwise
        '''
        return self.prop_type == LTL_PROPERTY

    def is_ltlf(self):
        '''Returns True if the property is an ltlf property, False otherwise
        '''
        return self.prop_type == LTLF_PROPERTY
