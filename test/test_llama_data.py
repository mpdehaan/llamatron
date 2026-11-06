# llamatron: a Python language and framework for producing MIDI clips.
# Copyright (C) 2026  Michael DeHaan
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

"""LlamaData, the base class of everything a song file stores, and its rule that subclasses
define both to_data() and from_data()."""

import importlib
import pkgutil
import unittest

import llamatron.composition
from llamatron.composition.llama_data import LlamaData


def every_subclass():
    """Return every LlamaData subclass in the composition package, importing all of it first."""
    for module in pkgutil.iter_modules(llamatron.composition.__path__):
        importlib.import_module(f'llamatron.composition.{module.name}')
    found, waiting = [], list(LlamaData.__subclasses__())
    while waiting:
        subclass = waiting.pop()
        found.append(subclass)
        waiting += subclass.__subclasses__()
    return found


class TestLlamaData(unittest.TestCase):

    def test_the_base_class_says_what_is_missing(self):
        with self.assertRaisesRegex(NotImplementedError, 'LlamaData needs a to_data'):
            LlamaData().to_data()
        with self.assertRaisesRegex(NotImplementedError, 'LlamaData needs a from_data'):
            LlamaData.from_data({}, 'the file')

    def test_a_subclass_without_its_own_methods_is_caught(self):
        class Incomplete(LlamaData):
            pass
        with self.assertRaisesRegex(NotImplementedError, 'Incomplete needs a to_data'):
            Incomplete().to_data()

    def test_every_subclass_defines_both_methods(self):
        for subclass in every_subclass():
            if subclass.__module__ == __name__:
                continue
            with self.subTest(subclass=subclass.__name__):
                self.assertIsNot(subclass.to_data, LlamaData.to_data)
                self.assertIsNot(subclass.from_data.__func__, LlamaData.from_data.__func__)


if __name__ == '__main__':
    unittest.main()
