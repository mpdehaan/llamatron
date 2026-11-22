# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""No two classes of the program share a name, so that a name says which class it means wherever it is read or searched for.

The names shared when the rule was made are listed, the key bindings' classes named after their pages and a few of the text
UI's own, which the Interface's part of the subsystem moves renames; the list only shrinks.
"""

import ast
import collections
import pathlib
import unittest

SOURCE = pathlib.Path(__file__).resolve().parent.parent.parent / 'src' / 'llamatron'
PYTHON_FILES = '*.py'
# The class names more than one class had when the rule was made.
ALLOWED = (
    'AboutDialog',
    'AccentRow',
    'AccidentalRow',
    'AddRow',
    'ArrangePage',
    'CcRow',
    'ChainEditor',
    'ChainStatementsPage',
    'ChoiceDialog',
    'ChordDialog',
    'ChordRow',
    'ChordScaleRow',
    'ChordsEditor',
    'ClipPage',
    'ConfirmDialog',
    'ControlRow',
    'CorrectionsDialog',
    'CycleRow',
    'DegreeRow',
    'Dialog',
    'DotRow',
    'DrawResetRow',
    'DrawsPage',
    'DriftEditor',
    'FieldPage',
    'FilePage',
    'GateRow',
    'GeneratorListPage',
    'GeneratorsPage',
    'GlideRow',
    'GrabRow',
    'GridChoiceDialog',
    'GrooveEditor',
    'GroovesPage',
    'GroupedChoiceDialog',
    'GuitarBarEditor',
    'Heading',
    'HelpDialog',
    'HocketEditor',
    'ImportDialog',
    'ImportedDialog',
    'InstrumentEditor',
    'InstrumentsPage',
    'InversionRow',
    'KeyswitchDialog',
    'KeyswitchMapDialog',
    'KeyswitchSlotRow',
    'ListPage',
    'Listed',
    'MainPage',
    'MessageDialog',
    'MusicianEditor',
    'NamedListPage',
    'NewPatternDialog',
    'NewRiffDialog',
    'NotesPage',
    'NumberRow',
    'OctaveRow',
    'OffsetsEditor',
    'OneRowEditor',
    'OpenPage',
    'Page',
    'PatternEditor',
    'PatternRow',
    'PatternRows',
    'PatternsPage',
    'PianoRoll',
    'PickManyDialog',
    'PluginEditor',
    'PromptDialog',
    'QuitDialog',
    'RegisterRow',
    'RegistersPage',
    'RowDialog',
    'ScalePage',
    'ScalesPage',
    'ScenePage',
    'SectionRow',
    'SetRow',
    'SlideRow',
    'SongPage',
    'SongsPage',
    'SoundDialog',
    'StartScreen',
    'StatementRow',
    'StepEditor',
    'StepRowEditor',
    'TensionRow',
    'TieRow',
    'ToggleRow',
    'TrackEditor',
    'WizardPage',
)
MSG_SHARED = 'class names shared by more than one class: {names}'
MSG_GONE = 'names on the allowed list are no longer shared, so they come off it: {names}'


def shared_class_names():
    """Return every class name the program defines more than once, in order."""
    places = collections.defaultdict(list)
    for path in sorted(SOURCE.rglob(PYTHON_FILES)):
        for node in ast.walk(ast.parse(path.read_text())):
            if isinstance(node, ast.ClassDef):
                places[node.name].append(path)
    return sorted(name for name, found in places.items() if len(found) > 1)


class TestUniqueClassNames(unittest.TestCase):

    def test_no_new_class_name_is_shared(self):
        shared = shared_class_names()
        new = [name for name in shared if name not in ALLOWED]
        self.assertEqual(new, [], MSG_SHARED.format(names=new))

    def test_the_allowed_list_only_shrinks(self):
        shared = shared_class_names()
        gone = [name for name in ALLOWED if name not in shared]
        self.assertEqual(gone, [], MSG_GONE.format(names=gone))


if __name__ == '__main__':
    unittest.main()
