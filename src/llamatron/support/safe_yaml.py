# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""Reading YAML so that a song file can never run code, with PyYAML's C parser when it's installed.

Only the safe loaders are ever used: they build plain data and nothing else. CSafeLoader is the
same safe loader on top of libyaml's parser, about ten times faster than the pure-Python one,
and it only exists when PyYAML was built with libyaml, so SafeLoader is the fallback. Everything
in the program that reads YAML comes through load_safely, which test_yaml_safety.py checks.
"""

import yaml

# The parser in use: libyaml's when PyYAML was built with it, otherwise the pure-Python one.
SAFE_LOADER = getattr(yaml, 'CSafeLoader', yaml.SafeLoader)


def load_safely(stream):
    """Return the plain data in a YAML file or text, never running anything it says."""
    return yaml.load(stream, Loader=SAFE_LOADER)


def uses_c_parser():
    """Return whether YAML is read with libyaml's parser, which is the faster of the two."""
    return SAFE_LOADER is not yaml.SafeLoader
