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
    The subset of commands used in VMT-LIB scripts
'''

from pysmt.smtlib.commands import SET_LOGIC, SET_OPTION, DECLARE_SORT, DECLARE_FUN, DEFINE_FUN, \
    ASSERT

#: List of commands used in VMT-LIB
VMT_COMMANDS = frozenset([
    SET_LOGIC,
    SET_OPTION,
    DECLARE_SORT,
    DECLARE_FUN,
    DEFINE_FUN,
    ASSERT
    # 'set-info'
    # 'declare-const'
])
