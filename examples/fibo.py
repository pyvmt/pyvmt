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
from sys import stdout
from pysmt.shortcuts import Int, Equals, Plus
from pysmt import typing
from pyvmt.model import Model

def main():
    """
        Generates the transition model to calculate the fibonacci sequence
    """
    model = Model()
    a = model.create_state_var('a', typing.INT)
    b = model.create_state_var('b', typing.INT)

    model.add_init(Equals(a, Int(1)))
    model.add_init(Equals(b, Int(1)))

    model.add_trans(Equals(model.next(b), Plus(a, b)))
    model.add_trans(Equals(model.next(a), b))

    model.serialize(stdout)

if __name__ == '__main__':
    main()
