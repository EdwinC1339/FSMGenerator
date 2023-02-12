# Edwin Camuy 2-8-23
import numpy as np
import re
import math
import itertools


class Output:
    def __init__(self, name, address):
        self.name = name
        self.address = address


class Var:
    def __init__(self, name: str, truth: bool):
        self.name = name
        self.truth = truth

    def inverted(self):
        return Var(self.name, not self.truth)


class Control(Var):
    def __init__(self, name: str, truth: bool, address: int):
        super().__init__(name, truth)
        self.address = address

    def inverted(self):
        return Control(self.name, not self.truth, self.address)


class VarGroup:
    def __init__(self, variables: set[Var]):
        self.variables = variables

    def add(self, v: Var):
        new_set = self.variables.copy()
        new_set.add(v)
        return VarGroup(new_set)

    def address(self):
        addresses_map = map(lambda v: (2 ** v.address) * v.truth, self.variables)
        x = sum(addresses_map)

        return x

    def invert_var(self, var):
        for v in self.variables:
            if v.name == var.name:
                self.variables.remove(v)
                self.variables.add(v.inverted())

    def __copy__(self):
        return VarGroup(self.variables.copy())

    def copy(self):
        return self.__copy__()


class State:
    def __init__(self, name: str, output: list[Output], address: int):
        self.name = name
        self.output = output
        self.address = address

    def hex_output(self):
        out = 0
        for ov in self.output:
            out += 2 ** ov.address
        return hex(out)

    def output_address(self):
        out = 0
        for o in self.output:
            out += 2 ** o.address

        return out


class Transition:
    def __init__(self, start: State, dest: State, conditions: VarGroup):
        self.start = start
        self.dest = dest
        self.conditions = conditions

    def explicit(self, controls: VarGroup):
        unused = {c for c in controls.variables if c.name not in list(map(lambda c: c.name, self.conditions.variables))}
        if unused == set():
            return [self]
        else:
            unused_cpy = unused.copy()
            uc = next(iter(unused))
            unused_cpy.remove(uc)
            set_p = self.conditions.variables.copy()
            set_p.add(uc)
            group_p = VarGroup(set_p)
            tp = Transition(self.start, self.dest, group_p)
            set_n = self.conditions.variables.copy()
            set_n.add(uc.inverted())
            group_n = VarGroup(set_n)
            tn = Transition(self.start, self.dest, group_n)

            sub_group = VarGroup(unused_cpy)

            return tp.explicit(sub_group) + tn.explicit(sub_group)


def parse(path):
    with open(path, 'r') as file:
        data = file.read().strip() + '\n'

    groups = list(map(lambda g: g.split('\n')[1:-1], re.split(r'-+\w+-+', data)[1:]))

    outputs = [Output(n, i) for i, n in enumerate(groups[0])]

    n_states = len(groups[1])
    states_power = math.ceil(math.log2(n_states))
    empty_states = 2**states_power - n_states
    for i in range(empty_states):
        groups[1].append(f"EMPTY{i}")
    states = []
    for i in range(2**states_power):
        fields = groups[1][i].split(' ->')
        name = fields[0].strip()
        if len(fields) == 1:
            outputs_string = ""
        else:
            outputs_string = fields[1]
        out = [o for o in outputs if outputs_string.find(o.name) != -1]
        states.append(State(name, out, i))

    controls_li = [Control(n, True, i) for i, n in enumerate(groups[2])]
    controls_li_all = controls_li + [Control(n, False, i) for i, n in enumerate(groups[2])]
    controls_set = set(controls_li)
    controls = VarGroup(controls_set)
    controls_all = VarGroup(set(controls_li_all))

    transitions = []
    for line in groups[3]:
        start_name, remainder = line.split('->')
        start_name = start_name.strip()
        dest_name, remainder = remainder.split(':')
        dest_name = dest_name.strip()
        conditions_names_p = [i.strip() for i in remainder.split(' ') if not i.startswith('!')]
        conditions_names_n = [i.strip()[1:] for i in remainder.split(' ') if i.startswith('!')]

        start = State('i should probably make an empty constructor', [Output('but i cant be bothered', 1917)], 8008135)
        dest = start
        for s in states:
            if s.name == start_name:
                start = s
            if s.name == dest_name:
                dest = s

        assert(start.address != 8008135)

        conditions_p = {c for c in controls.variables if c.name in conditions_names_p}
        conditions_n = {c.inverted() for c in controls.variables if c.name in conditions_names_n}

        conditions = VarGroup(conditions_n.union(conditions_p))

        transitions.append(Transition(start, dest, conditions))

    return states, controls, controls_all, transitions, outputs


def fsm_truth_table(states, controls, transitions):
    n_states = len(states)
    n_controls = len(controls.variables)

    shape = [n_states, 2 ** n_controls]
    te = np.zeros(shape, 'int')
    for t in transitions:
        condition_address = t.conditions.address()
        te[t.start.address, condition_address] = t.dest.address
    flattened = te.flatten()
    return flattened


def decoder(states: list[State]):
    shape = [len(states)]
    te = np.zeros(shape, dtype='int')
    for s in states:
        te[s.address] = s.output_address()
    return te


def format_rom(rom: np.ndarray):
    out = ""
    acc = -1
    count = 1
    n = 0
    flag = False
    for i in rom:
        if n % 8 == 0 and not flag:
            out += '\n'
            flag = True
        if i == acc:
            count += 1
        elif count > 1:
            n += 1
            flag = False
            out += f"{int(count)}*{hex(int(acc))[2:]} "
            count = 1
        elif acc != -1:
            n += 1
            flag = False
            out += hex(int(acc))[2:] + ' '

        acc = i

    if count > 1:
        out += f"{int(count)}*{hex(int(acc))[2:]} "
    else:
        out += hex(int(acc))[2:]

    return out


def main():
    states, controls, controls_all, transitions_implicit, outputs = parse("input.txt")

    transitions_explicit = list(itertools.chain.from_iterable([t.explicit(controls) for t in transitions_implicit]))

    rom1 = fsm_truth_table(states, controls, transitions_explicit)
    rom2 = decoder(states)

    np.set_printoptions(formatter={'int': lambda x: hex(int(x))[2:]})

    with open("output1.txt", 'w') as file:
        text = "v2.0 raw"
        text += format_rom(rom1)
        file.write(text)

    with open("output2.txt", 'w') as file:
        text = "v2.0 raw"
        text += format_rom(rom2)
        file.write(text)

    data1 = math.floor(math.log2(len(states)))
    data2 = len(outputs)

    address1 = math.floor(math.log2(len(states))) + len(controls.variables)
    address2 = data1

    print(f"""
    Job done! Processed {len(states)} states, with {len(transitions_implicit)} transitions.
    Now to import to Logisim, do the following:
        1. Create a new ROM with a data bit width of {data1} and an address bit width of {address1}. We'll call it ROM 1.
        2. Create a new ROM with a data bit width of {data2} and an address bit width of {address2}. We'll call it ROM 2.
        3. Create a new register with {data1} bits.
        4. Create a new splitter with data bit width of {address1} and fan out of 2.
        5. Connect the splitter's wide end to the ROM 1's A input.
        6. Connect the splitter's least significant bits to your control signals.
        7. Connect the splitter's most significant  bits to the register's Q output.
        8. Connect the register's D input to ROM 1's Output. 
        9. Connect the register's Q output to ROM 2's A input.
        10. Connect a clock signal to the register.
        11. Connect a 1 signal to the Register's enable, as well as both ROM's select signals.
        12. Set ROM1 to output1.txt.
        13. Set ROM2 to output2.txt.
        14. ROM2's outputs are your final outputs.""")

    input("Press enter to exit.")


if __name__ == "__main__":
    main()
