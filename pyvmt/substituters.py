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
    Module that exports substituters used in pyvmt
'''

from pysmt.walkers import IdentityDagWalker

class VmtLibSubstituter(IdentityDagWalker):
    '''
        Some of the operators used in PyVmt are not supported in VMT-LIB,
        these operators need to be replaced with a combination of different operators
    '''
    # pylint: disable=unused-argument

    def __init__(self, next_substitutions, bound_variables=None, env=None):
        super().__init__(env=env)
        self._next_substitutions = next_substitutions
        if bound_variables is None:
            bound_variables = set()
        self._bound_variables = bound_variables

    def _push_with_children_to_stack(self, formula, **kwargs):
        # deal with quantifiers
        if formula.is_quantifier():
            # recalculate bound variables
            bound_variables = set(self._bound_variables)
            bound_variables.update(formula.quantifier_vars())

            # apply the substitution with the bound variables
            sub = self.__class__(self._next_substitutions, bound_variables, env=self.env)
            res_formula = sub.walk(formula.arg(0), **kwargs)

            # call the function and memoize the result
            fun = sub.functions[formula.node_type()]
            res = fun(formula, args=[res_formula], **kwargs)
            self.memoization[self._get_key(formula, **kwargs)] = res
        else:
            super()._push_with_children_to_stack(formula, **kwargs)

    def replace(self, formula):
        '''Execute the replacement of unsupported LTL operators for VMT-LIB

        :param formula: The formula to perform the replacements on
        :type formula: pysmt.fnode.FNode
        :return: The formula after the replacements
        :rtype: pysmt.fnode.FNode
        '''
        # Next operators need to be pushed to the leaves
        formula = self.env.next_pusher.push_next(formula)

        # Now all of the Next operators contain leaf node symbols which
        # will be replaced if they're an unbound state variable
        return self.walk(formula)

    def walk_next(self, formula, args, **kwargs):
        '''Replace all the next state variables with new ones'''
        # this should contain a single node, being the symbol that could be
        # an unbound state variable that needs to be replaced
        assert len(args) == 1
        assert args[0].is_symbol()

        if args[0] in self._next_substitutions and args[0] not in self._bound_variables:
            return self._next_substitutions[args[0]]
        return args[0]

    def walk_ltl_r(self, formula, args, **kwargs):
        '''Rewrite the R operator in terms of the U operator'''
        assert len(args) == 2
        return self.mgr.Not(self.mgr.U(self.mgr.Not(args[0]), self.mgr.Not(args[1])))
