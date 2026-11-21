# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""ScaleKind names every scale type the way the file spells it, so it has to match ScaleType exactly."""

import unittest

from llamatron.model.values.scale import ScaleType
from llamatron.model.vocabulary.file_format import ScaleKind


def scale_kind_names():
    """Return the kinds ScaleKind defines, by constant name."""
    return {name: value for name, value in vars(ScaleKind).items() if not name.startswith('_')}


class TestScaleKinds(unittest.TestCase):

    def test_every_scale_type_has_a_kind_and_nothing_else_does(self):
        expected = {name: name.lower() for name in ScaleType.__members__}
        self.assertEqual(scale_kind_names(), expected)
