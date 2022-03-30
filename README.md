# PyVmt: a python library to interact with transition systems
PyVmt is an extension of [PySmt](https://pysmt.readthedocs.io/en/latest/) providing classes and operators to create and check finite and infinite state transition systems.

It offers a Model class which stores the data of a transition system:
- state variables
- input variables
- init constraints
- trans constraints
- properties to be tested

All the variables used within the model have to be declared using one of the available methods, the Next version of each variable can be produced by wrapping the formula containing it within the Next operator.

## Serialization, parsing, and model checking

The model class can be serialized to [VMT-LIB](https://vmt-lib.fbk.eu/) and can be instantiated from an existing VMT-LIB script using the read function.
The VMT-LIB script can be converted using one of the available tools, or can be used directly with a solver that supports it.

PyVmt offers an interface to interact directly with installed solvers, testing properties of several types:
- invar properties, in the form G(formula)
- live properties, in the form F(G(formula))
- ltl properties

The result from model checking tells if the system is safe or unsafe, and stores the data that was returned by the model checker.

If the property is unsafe the model checker may return a counterexample containing a trace with a finite or infinite number of steps. The trace can be analyzed directly by checking the assignments, and evaluating a formula over a step, with the possibility to use the Next operator.

It is also possible to serialize the steps to VMT-LIB.

## Configuration
PyVmt currently supports 3 solvers:

- ic3ia (https://es-static.fbk.eu/people/griggio/ic3ia/)
- EUForia (https://github.com/dbueno/euforia)
- nuXmv (https://nuxmv.fbk.eu/)

To use any of these solvers, download or build their latest stable release. To use the nuXmv solver you will need a version that includes the command read_vmt_script.

After installing the solver you want to use, you must then configure an environment variable containing the path to the executable:

- PYVMT_IC3IA_PATH containing the path to the ic3ia executable
- PYVMT_EUFORIA_PATH containing the path to the EUForia executable
- PYVMT_NUXMV_PATH containing the path to the nuXmv executable

For example you may add to ~/.bashrc the following lines:

```bash
export PYVMT_IC3IA_PATH="${HOME}/.vmt-solvers/ic3ia/ic3ia"
export PYVMT_EUFORIA_PATH="${HOME}/.vmt-solvers/EUForia/EUForia"
export PYVMT_NUXMV_PATH="${HOME}/.vmt-solvers/nuXmv/nuXmv"
```

And place the solver executables at the specified paths.

## Usage

This simple example shows a transition system containing a state variable called 'a' which is initialized at 0 and incremented at each step by 1. A solver is called to check if the variable always stays below the value of 5.

```python
from pyvmt.model import Model
from pyvmt.solvers.ic3ia import Ic3iaSolver
from pyvmt.shortcuts import Next
from pysmt.shortcuts import Equals, Int, Plus, INT, LT

model = Model()
# the state variable needs to be declared before being used within the model
a = model.create_state_var('a', INT)

# add some constraints to initialization and evolution of the model
model.add_init(Equals(a, Int(0)))
model.add_trans(Equals(Next(a), Plus(a, Int(1))))

# add some property to check, and run the solver
prop = LT(a, Int(5))
prop_idx = model.add_invar_property(prop)
solver = Ic3iaSolver(model)
res = solver.check_property_idx(prop_idx)
assert res.is_unsafe()
assert res.has_trace()

# print the counterexample
print("Found a counterexample to invar prop", prop)
for step in res.get_trace().get_steps():
    print(a, '=', step.get_assignment(a))
```

Using the formula manipulation functionalities offered by PySmt it is possible to create configurable transition systems programmatically depending on parameters, the ferryman example shows how this can be used.

# Other features
Some of the other things that you can do with PyVmt include:
- merging transitions systems by means of synchronous composition
- renaming a transition system's variables by adding or changing a prefix/suffix, or with a customized callback function
- wrap complex formulae with the Next operators to form Next state formulae, then push the Next operators to the leaves containing the state variables
- check if a formula contains LTL or Next operators
