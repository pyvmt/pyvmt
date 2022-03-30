from sys import stdout
from pysmt.shortcuts import LE, GT, GE, Int, Implies, Equals, Minus
from pysmt import typing
from pyvmt.model import Model

def main():
    """
        Generates the transition model to simulate the GCD algorithm
    """
    model = Model()
    a = model.create_state_var('a', typing.INT)
    b = model.create_state_var('b', typing.INT)

    model.add_init(LE(a, Int(200)))
    model.add_init(GE(a, Int(2)))

    model.add_init(LE(b, Int(200)))
    model.add_init(GE(b, Int(2)))

    model.add_trans(Implies(LE(a, b), Equals(model.next(a), a)))
    model.add_trans(Implies(LE(b, a), Equals(model.next(b), b)))

    model.add_trans(Implies(GT(a, b), Equals(model.next(a), Minus(a, b))))
    model.add_trans(Implies(GT(b, a), Equals(model.next(b), Minus(b, a))))

    model.add_live_property(Equals(a, b))

    model.serialize(stdout, properties=model.get_all_properties())

if __name__ == '__main__':
    main()
