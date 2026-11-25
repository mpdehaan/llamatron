# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write native/math/tests/data/python_random_cases.txt: CPython's random.Random drawing every call llamatron's generators
make, from whole and text seeds, so that the Rust port of it (native/math/src/python_random.rs) is held to CPython number for
number. Each line is a seed's kind, the seed, the call, its arguments and what it gave, tab separated, a fresh generator a
line, its call made three times; floats are written by repr, which reads back exactly.

    .venv/bin/python internal_tools/python_random_cases.py
"""

import pathlib
import random

OUT = pathlib.Path(__file__).resolve().parent.parent / 'native' / 'math' / 'tests' / 'data' / 'python_random_cases.txt'
WHOLE_SEEDS = (0, 1, 42, 2 ** 40 + 7, -99, 2 ** 100 + 3)
TEXT_SEEDS = ('', '7/1/lead', '12345/3/bass/direction/take 2', 'é and ü', 'x' * 300)
CALLS = (
    ('random', ()), ('getrandbits', (5,)), ('getrandbits', (32,)), ('getrandbits', (70,)), ('randrange', (10,)),
    ('randrange', (3, 40, 1)), ('randrange', (10, -20, -3)), ('randint', (-5, 5)), ('choice', (7,)), ('shuffle', (12,)),
    ('uniform', (-2.5, 7.0)), ('choices', (5, 6)), ('weighted', (6,)), ('sample', (10, 4)), ('sample', (100, 8)), ('gauss', (0.0, 1.0)),
)
WEIGHTS = (1.0, 2.0, 3.0, 0.5)


def drawn(generator, call, arguments):
    """Return what one call gives, as text: numbers joined by commas."""
    if call == 'choice':
        return str(generator.choice(range(arguments[0])))
    if call == 'shuffle':
        items = list(range(arguments[0]))
        generator.shuffle(items)
        return ','.join(map(str, items))
    if call == 'choices':
        return ','.join(map(str, generator.choices(range(arguments[0]), k=arguments[1])))
    if call == 'weighted':
        return ','.join(map(str, generator.choices(range(len(WEIGHTS)), weights=WEIGHTS, k=arguments[0])))
    if call == 'sample':
        return ','.join(map(str, generator.sample(range(arguments[0]), arguments[1])))
    return repr(getattr(generator, call)(*arguments))


def main():
    lines = []
    for kind, seeds in (('whole', WHOLE_SEEDS), ('text', TEXT_SEEDS)):
        for seed in seeds:
            for call, arguments in CALLS:
                generator = random.Random(seed)
                results = [drawn(generator, call, arguments) for _ in range(3)]
                lines.append('\t'.join([kind, str(seed), call, ','.join(map(repr, arguments)), ';'.join(results)]))
    OUT.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
