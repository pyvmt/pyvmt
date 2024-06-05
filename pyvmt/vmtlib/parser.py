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
'''Exports an extension of the SmtLibParser with support to LTL operators used in VMT-LIB
'''

from pysmt.smtlib.parser import SmtLibParser

class VmtLibParser(SmtLibParser):
    # pylint: disable=abstract-method
    '''Extension of SmtLibParser, adds the interpretation of LTL operators.

    This parser can handle VMT-LIB scripts containing any LTL property.
    '''

    def __init__(self, environment=None, interactive=False):
        super().__init__(environment=environment, interactive=interactive)
        mgr = self.env.formula_manager
        ltl_interpreted = { 'ltl.G': self._operator_adapter(mgr.G),
                            'ltl.U': self._operator_adapter(mgr.U),
                            'ltl.F': self._operator_adapter(mgr.F),
                            'ltl.X': self._operator_adapter(mgr.X),
                            'ltl.H': self._operator_adapter(mgr.H),
                            'ltl.S': self._operator_adapter(mgr.S),
                            'ltl.O': self._operator_adapter(mgr.O),
                            'ltl.Y': self._operator_adapter(mgr.Y),
                            'ltl.Z': self._operator_adapter(mgr.Z),
                           }

        for key, val in ltl_interpreted.items():
            self.interpreted[key] = val
