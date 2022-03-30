'''
    The ferryman problem is a logic puzzle where a ferryman has to carry across a river
    several entities but being only able to carry a limited amount together.

    Some of the entities cannot be left unattended alone, for example the sheep would
    eat the cabbage if the ferryman isn't with them.

    This example creates a model for the ferryman problem and uses a solver to find a
    possible solution.
'''

from itertools import combinations
from pysmt.shortcuts import FALSE, Iff, And, Not, Implies, Symbol
from pyvmt.model import Model
from pyvmt.solvers.ic3ia import Ic3iaSolver
from pyvmt.exceptions import TraceStepNotFoundError

def entity_to_txt(entity):
    '''Represents an FNode corresponding to an entity in text form'''
    return entity.symbol_name()[0:2].upper()

def build_model(ferryman, others, enemies, boat_capacity):
    '''Build a model for the problem based on the Symbols representing
    the ferryman, all the other entities, and which entities can't be left unattended together.
    '''
    entities = set(others).union([ferryman])
    model = Model()

    for entity in entities:
        model.add_state_var(entity)

    def unattended(entity):
        return Iff(entity, Not(ferryman))

    def moving(entity):
        return Iff(entity, Not(model.next(entity)))

    def at_most_n(lst, n):
        conditions = (Not(And(comb)) for comb in combinations(lst, r=(n + 1)))
        return And(conditions)

    # entities start on the left side
    for entity in entities:
        model.add_init(Iff(entity, FALSE()))

    # enemies should never be left unattended
    for entity_a, entity_b in enemies:
        enemies_unattended = And(Iff(entity_a, entity_b), unattended(entity_a))
        model.add_trans(Not(model.next(enemies_unattended)))

    # the ferryman has the boat, so an entity that is not
    # in the same spot as the ferryman cannot move
    for entity in entities:
        model.add_trans(Implies(unattended(entity), Not(moving(entity))))

    # the boat has a limited capacity
    model.add_trans(at_most_n([moving(entity) for entity in entities], boat_capacity))

    solved = And(entities)
    # when solved all the variables should stay equal
    for entity in entities:
        model.add_trans(Implies(solved, Not(moving(entity))))
    # the ferryman moves as long as the problem is not solved
    model.add_trans(Implies(Not(solved), moving(ferryman)))

    # create a property to find a counterexample that solves the problem
    model.add_invar_property(Not(solved))

    return model

def print_trace(trace):
    '''Pretty print a trace with all the steps'''
    entities = trace.get_state_vars()
    for step in trace.get_steps():
        try:
            changing = step.get_changing_variables()
        except TraceStepNotFoundError:
            changing = {}

        step_type = 'loopback ' if step.is_loopback else ''
        print(f';; {step_type}step {step.step_idx}')
        for entity, value in step.get_assignments().items():
            # pretty print the movement
            l_movement = '  '
            r_movement = '  '
            l_entity = '  '
            r_entity = '  '
            if value.constant_value():
                r_entity = entity_to_txt(entity)
                if entity in changing:
                    r_movement = '<-'
            else:
                l_entity = entity_to_txt(entity)
                if entity in changing:
                    l_movement = '->'
            print(f'{l_entity}{l_movement} ~~ {r_movement}{r_entity}')

        # print(step.get_formula())
        # print(step.serialize_to_string())
        print()
    final_step = trace.get_step(-1)
    assert final_step.evaluate_formula(And(entities)).is_true(), \
        "Not all entities made it across"
    print("All entities are now across")
    print()

def ferryman_3():
    '''ferryman problem with 3 other entities'''
    # variables defining if the entities are across
    cabbage = Symbol('cabbage')
    wolf = Symbol('wolf')
    ferryman = Symbol('ferryman')
    sheep = Symbol('sheep')

    enemies = [
        (sheep, cabbage),
        (sheep, wolf)
    ]

    model = build_model(ferryman, [wolf, sheep, cabbage], enemies, 2)
    return model

def ferryman_4():
    '''ferryman problem with 4 other entities'''
    # variables defining if the entities are across
    ferryman = Symbol('ferryman')
    chicken = Symbol('chicken')
    caterpillar = Symbol('caterpillar')
    fox = Symbol('fox')
    lettuce = Symbol('lettuce')

    enemies = [
        (chicken, fox),
        (chicken, caterpillar),
        (lettuce, caterpillar)
    ]

    model = build_model(ferryman, [chicken, caterpillar, fox, lettuce], enemies, 3)
    return model

def main():
    """
        Generates the transition model to solve the ferryman problem
    """

    model = ferryman_3()
    solver = Ic3iaSolver(model)
    res = solver.check_property_idx(0)
    assert res.is_unsafe()
    assert res.has_trace()
    print_trace(res.get_trace())

    model = ferryman_4()
    solver = Ic3iaSolver(model)
    res = solver.check_property_idx(0)
    assert res.is_unsafe()
    assert res.has_trace()
    print_trace(res.get_trace())

if __name__ == '__main__':
    main()
