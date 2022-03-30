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
'''The environment for PyVmt needs to work with LTL formulae

This module overrides some of the functions offered by PySmt to
create environments that work with LTL and should be used in place
of pysmt.environment
'''

from pysmt.environment import Environment as PysmtEnvironment, pop_env
from pysmt.environment import get_env, push_env as pysmt_push_env
from pyvmt.operators import FormulaManager, HRSerializer
from pyvmt.operators import HasLtlOperatorsWalker, HasNextOperatorWalker, NextPusher

class Environment(PysmtEnvironment):
    '''Extension of pySMT environment.'''
    FormulaManagerClass = FormulaManager
    HRSerializerClass = HRSerializer
    HasLtlOperatorsWalkerClass = HasLtlOperatorsWalker
    HasNextOperatorWalkerClass = HasNextOperatorWalker
    NextPusherClass = NextPusher

    def __init__(self):
        super().__init__()
        self._has_ltlop_walker = self.HasLtlOperatorsWalkerClass(env=self)
        self._has_next_walker = self.HasNextOperatorWalkerClass(env=self)
        self._next_pusher = self.NextPusherClass(env=self)

    @property
    def has_ltl_operators_walker(self):
        '''Walker to check if a formula has any LTL operators'''
        return self._has_ltlop_walker

    @property
    def has_next_operator_walker(self):
        '''Walker to check if a formula has any Next operator'''
        return self._has_next_walker

    @property
    def next_pusher(self):
        '''Walker to push Next operators down to the leaf nodes containing symbols'''
        return self._next_pusher

def push_env(env=None):
    '''Overload push_env to default to the new Environment class.'''
    if env is None:
        env = Environment()
    return pysmt_push_env(env=env)

def reset_env():
    '''
        Overload of pysmt.environment.reset_env
    '''
    pop_env()
    push_env()
    return get_env()

# Create the default environment
reset_env()
