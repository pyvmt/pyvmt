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
    The annotations used in VMT-LIB
'''

from pyvmt import properties

#: Annotation for next relation
NEXT = 'next'

#: Annotation for init constraint
INIT = 'init'

#: Annotation for trans relation
TRANS = 'trans'

#: Annotation to define an invariant property
INVAR_PROPERTY = 'invar-property'

#: Annotation to define a live property
LIVE_PROPERTY = 'live-property'

#: Annotation to define an LTL property
LTL_PROPERTY = 'ltl-property'

#: Complete list of VMT-LIB annotations
VMT_ANNOTATIONS = frozenset([
    NEXT,
    INIT,
    TRANS,
    INVAR_PROPERTY,
    LIVE_PROPERTY,
    LTL_PROPERTY
])

#: Complete list of VMT-LIB property annotations
PROPERTY_TYPES = frozenset([
    INVAR_PROPERTY,
    LIVE_PROPERTY,
    LTL_PROPERTY
])

#: A map between property annotations and the corresponding PyVmt property type
ANNOTS_PROPERTIES_MAP = {
    INVAR_PROPERTY: properties.INVAR_PROPERTY,
    LIVE_PROPERTY: properties.LIVE_PROPERTY,
    LTL_PROPERTY: properties.LTL_PROPERTY,
}

#: A map between PyVmt property types and the corresponding VMT-LIB annotation
PROPERTIES_ANNOTS_MAP = { v: k for k, v in ANNOTS_PROPERTIES_MAP.items() }
