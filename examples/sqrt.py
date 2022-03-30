from sys import stdout
from pysmt.shortcuts import Real, Equals, Plus, LE, GE, Div, Minus, Times, And
from pysmt import typing
from pyvmt.model import Model

def main():
    """
        Generates the transition model to simulate the sqrt algorithm
    """
    model = Model()
    # example of how to use create_frozen_var
    a = model.create_frozen_var('a', typing.REAL)
    model.add_init(LE(a, Real(36)))
    model.add_init(GE(a, Real(9)))

    # variable that stores the sqrt
    sqrta = model.create_state_var('sqrta', typing.REAL)
    model.add_init(Equals(sqrta, Real(1)))

    # assign sqrta to the average between sqrta and a/sqrta
    bound = Div(a, sqrta)
    avg = Div(Plus(sqrta, bound), Real(2))
    model.add_trans(Equals(model.next(sqrta), avg))

    # eventually the error becomes small
    error = Minus(a, Times(sqrta, sqrta))
    model.add_live_property(And(LE(error, Real(0.01)), GE(error, Real(-0.01))))

    model.serialize(stdout, properties=model.get_all_properties())

if __name__ == '__main__':
    main()
