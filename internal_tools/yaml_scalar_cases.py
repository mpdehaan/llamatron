# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""Write src/model/tests/data/yaml_scalar_cases.txt: how PyYAML's safe loader reads each of many plain scalars, which
holds llamatron2's reading of plain scalars (src/model/src/file/data.rs) to PyYAML's YAML 1.1 rules. Each line is the
text, the kind PyYAML gave (null, bool, int, float, str) and the value's repr, tab separated.

    .venv/bin/python internal_tools/yaml_scalar_cases.py
"""

import pathlib

import yaml

OUT = pathlib.Path(__file__).resolve().parent.parent / 'src' / 'model' / 'tests' / 'data' / 'yaml_scalar_cases.txt'
TEXTS = (
    '', '~', 'null', 'Null', 'NULL', 'nULL', 'yes', 'Yes', 'YES', 'yEs', 'no', 'No', 'on', 'On', 'off', 'OFF', 'true', 'True', 'false', 'y', 'n',
    '0', '00', '010', '08', '0_7', '7', '-7', '+7', '1_000', '0b101', '-0b11', '0x1F', '0x1f', '0xg', '1:30', '1:30:05', '1:60', '01:30', '190:20:30',
    '1.5', '-1.5', '+1.5', '.5', '-.5', '1.', '1.e+3', '1.0e+3', '1.0e3', '1e3', '1e+3', '1.0E-2', '1_0.2_5', '1:30.5', '.inf', '-.inf', '+.inf', '.Inf',
    '.nan', '.NaN', '-.nan', 'inf', 'nan', '1/4', '5/16', 'C#4', 'Bb2', 'lead', 'a b', '-', '1.2.3', '12:00', '0.0', '-0', '3:00.5', '1_', '_1',
)


def main():
    lines = []
    for text in TEXTS:
        value = yaml.safe_load('[' + text + ']')[0] if text else yaml.safe_load('[~]')[0]
        lines.append('\t'.join([text, type(value).__name__ if value is not None else 'null', repr(value)]))
    OUT.write_text('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main()
