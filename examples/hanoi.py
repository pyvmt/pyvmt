from pysmt.shortcuts import Not, LE, GE, And, Int, Implies, Equals, NotEquals, ExactlyOne
from pysmt import typing
from pyvmt.model import Model
from pyvmt.solvers.ic3ia import Ic3iaSolver

NUM_DISKS = 4
NUM_STACKS = 3

def print_trace(trace):
    '''Print the trace in a human readable way'''
    disks = list(trace.get_state_vars())
    for step in trace.get_steps():
        stacks = [[] for _ in range(NUM_STACKS)]
        for disk in reversed(disks):
            pos = step.get_assignment(disk).constant_value()
            stacks[pos].append(disk)

        for height in range(NUM_DISKS - 1, -1, -1):
            for stack in stacks:
                if height < len(stack):
                    print(stack[height], end='')
                else:
                    print('|', end='')
                print('', end='\t')
            print()
        print('_______'.join('|' for _ in range(NUM_STACKS)), '\n\n')
    final_step = trace.get_step(-1)
    assert final_step.evaluate_formula(
        And(Equals(disk, Int(1))
            for disk in disks)
    ).is_true(), "Not all disks reached the final position"
    print("All disks moved to the correct place")

def main():
    """
        Generates the transition model to simulate hanoi
    """
    model = Model()

    disks = []

    # add the state variables
    for sz in range(NUM_DISKS):
        disk = model.create_state_var(f'd{sz}', typing.INT)
        disks.append(disk)
    # set the possible values for the disks, the position the disk is in
    for disk in disks:
        # initial position
        model.add_init(Equals(disk, Int(0)))
        model.add_trans(And(GE(model.next(disk), Int(0)),
                            LE(model.next(disk), Int(NUM_STACKS - 1))))

    def moving(disk):
        # returns whether the disk is moving between this step and the next
        return NotEquals(disk, model.next(disk))

    for i in range(NUM_DISKS):
        for j in range(i + 1, NUM_DISKS):
            same_spot = Equals(disks[i], disks[j])
            bigger_disk_moving = moving(disks[j])
            # if the disks are in the same spot the bigger one is underneath and cannot move
            model.add_trans(Implies(same_spot, Not(bigger_disk_moving)))
            # don't move the bigger disk on top of the smaller disk
            model.add_trans(Implies(bigger_disk_moving, model.next(Not(same_spot))))

    solved = And(
        Equals(disk, Int(1))
        for disk in disks
    )

    # exactly one disk should move at each step as long as a solution has not been found
    model.add_trans(Implies(Not(solved), ExactlyOne(
        moving(disk)
        for disk in disks
    )))
    # leave the disks where they are after the problem has been solved
    model.add_trans(Implies(solved, model.next(solved)))

    # to find the solution negate the solution condition
    model.add_invar_property(Not(solved))

    # try to find the solution to the problem
    solver = Ic3iaSolver(model)
    results = solver.check_properties()
    res = results[0]
    assert res.is_unsafe()
    assert res.has_trace()

    trace = res.get_trace()

    # print the found solution
    print_trace(trace)

if __name__ == '__main__':
    main()
