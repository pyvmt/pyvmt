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
import sys
import argparse
from pyvmt.vmtlib.reader import read
from pyvmt.model import Model
from pyvmt.ltl_encoder import ltl_encode, ltl_circuit_encode, ltlf_encode, safetyltl_encode
from pyvmt import exceptions
from pyvmt.solvers.ic3ia import Ic3iaSolver

def parse_args ():
    '''Defines and parses the arguments'''
    encoding_algs = {
        'ltl2smv': ltl_encode,
        'safetyltl2smv' : safetyltl_encode,
        'ltlf2smv' : ltlf_encode,
        'circuit': ltl_circuit_encode,
    }
    parser = argparse.ArgumentParser(description="""Encode a model with an LTL property into a new
        model where the property has been encoded into a liveness property.
        Two types of encoding are available,
        circuit encodes the property by adding monitor circuits,
        ltl2smv encodes the property into a tableau which is added to the model.
    """)
    parser.add_argument('-a', '--alg', choices=encoding_algs.keys(), default='ltl2smv',
        help="The algorithm to use for encoding")
    parser.add_argument('-i', type=argparse.FileType('r'), default=sys.stdin, metavar='input',
        help="The input file, defaults to the standard input", dest='input')
    parser.add_argument('-o', type=argparse.FileType('w'), default=sys.stdout, metavar='output',
        help="The output file, defaults to the standard output", dest='output')
    parser.add_argument('-n', '--idx', type=int, default=0, metavar='property_idx',
        help="The index of the property to encode")
    parser.add_argument('-c', '--check-prop', action='store_true')
    res = parser.parse_args()
    res.alg = encoding_algs[res.alg]
    return res

def main():
    '''Reads a model, encodes the specified LTL property into the model either
    with the ltl2smv or the circuit encoder, and outputs it.
    '''
    args = parse_args()
    model = read(args.input)
    prop = model.get_property(args.idx)
    if not prop.is_ltl() and not prop.is_ltlf():
        raise exceptions.InvalidPropertyTypeError(f"Expected LTL Property, found {prop.prop_type}")

    model = args.alg(model, prop.formula)
    model.serialize(args.output)

    if args.check_prop:
        ic3ia = Ic3iaSolver(model)
        res = ic3ia.check_property_idx(0)

        if res.is_safe():
            inv = res.get_invar()
            print(f"Property {args.idx} is safe.")
            print("Ic3ia returns the inductive invariant: %s" % inv.serialize())
        else:
            print(f"Property {args.idx} is unsafe.")

if __name__ == '__main__':
    main()
