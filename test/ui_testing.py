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

"""The base class and helpers for the text UI tests, which run the real program with no terminal and press keys."""

import os
import string
import tempfile
import unittest

from textual import events

from llamatron.composition.file_format import GeneratorKind, NAMED_GENERATORS
from llamatron.tui.app import LlamatronApp
from llamatron.tui.document import Document, new_song


# How the pattern editor shows a row's label at the left of the grid, a key in the key list,
# and a step whose quiet row isn't set.
ROW_SHOWN = '│ {label}'


KEY_SHOWN = '« {label} »'


QUIET_VALUE = '.'
# The name the tests give a chromatic scale they add, to play every degree.
CHROMATIC_SCALE = 'all'


def fixed_text(template):
    """Return the longest piece of a message template that isn't filled in, to look for on screen."""
    pieces = [literal for literal, _, _, _ in string.Formatter().parse(template)]
    return max(pieces, key=len)


def a_song(path=None):
    data = new_song()
    data['auto_ratchets'] = {'rolls': {'counts': [1, 4]}}
    data['patterns'] = {
        'tune': {
            'steps': 4, 'step_size': '1/8', 'degree': [1, 3, None, None], 'gate': ['1/4', '1/4', '1/8', None],
            'octave': [3, 3, None, None],
        },
        'beat': {'steps': 2, 'step_size': '1/8', 'drum': True, 'degree': ['C', None], 'gate': ['1/16', None], 'octave': [1, None]},
        'other': {'steps': 1, 'step_size': '1/2', 'degree': [5]},
    }
    data['tracks'] = {'lead': {}, 'drums': {}}
    data['arps'] = {'up': {'step': '1/8', 'order': 'up'}}
    data['chains'] = {'named': [{'arp': 'up'}, {'auto_ratchet': 'rolls'}], 'empty': []}
    data['scenes'] = [
        {'name': 'one', 'tracks': {'lead': {'pattern': 'tune'}, 'drums': {'pattern': 'beat', 'loop': True}}},
        {'name': 'two', 'tracks': {}},
    ]
    return Document(data, path)


def _key_event(name):
    """Return the event a terminal sends for a key."""
    named = {
        'space': ' ', '+': '+', '-': '-', '*': '*', '/': '/',
        'enter': '\r', 'backspace': '\x7f', 'escape': '\x1b', 'up': None, 'down': None,
        'left': None, 'right': None, 'tab': '\t', 'f5': None,
    }
    words = {'+': 'plus', '-': 'minus', '*': 'asterisk', '/': 'slash'}
    if name in named:
        return events.Key(words.get(name, name), named[name])
    return events.Key(name, name)


def screen_text(app):
    """Return what's on screen, with «» around anything in reverse video."""
    lines = []
    for strip in app.screen._compositor.render_strips():
        line, reverse = '', False
        for segment in strip:
            now = bool(segment.style and segment.style.reverse)
            if now != reverse:
                line += '«' if now else '»'
                reverse = now
            line += segment.text
        lines.append(line + ('»' if reverse else ''))
    return '\n'.join(lines)


class UITest(unittest.IsolatedAsyncioTestCase):
    """Runs the real program with no terminal, pressing keys."""

    SIZE = (100, 40)

    async def asyncSetUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.addCleanup(os.chdir, os.getcwd())
        os.chdir(temporary.name)
        self.folder = temporary.name
        self.document = a_song()
        self.app = LlamatronApp(self.document)
        self.running = self.app.run_test(size=self.SIZE)
        self.pilot = await self.running.__aenter__()
        self.addAsyncCleanup(self.running.__aexit__, None, None, None)
        await self.pilot.pause()

    async def press(self, *keys):
        # Pressing keys through the terminal driver takes a tenth of a second each, so these go
        # straight to the screen. TestRealKeys checks the same keys through the driver.
        for name in keys:
            self.app.screen.on_key(_key_event(name))
            await self.pilot.pause()

    async def type(self, text):
        await self.press(*[{' ': 'space'}.get(letter, letter) for letter in text])

    def empty_the_arrangement(self):
        """Delete every scene and then every track, through the document, as a page would."""
        for index in reversed(range(len(self.document.song().get_scenes()))):
            self.document.delete_scene(index)
        for name in self.document.song().get_track_names():
            self.document.delete_track(name)

    def track(self, name):
        return self.document.song().get_track(name)

    def arp(self, name):
        return self.document.song().get_generator_settings(GeneratorKind.ARP, name)

    def auto_ratchet(self, name):
        return self.document.song().get_generator_settings(GeneratorKind.AUTO_RATCHET, name)

    def chain_steps(self, name):
        return self.document.song().get_chain(name).get_steps()

    def root_and_kind(self, name):
        """Return a named scale's root and type as the file writes them."""
        scale = self.document.song().get_named_scale(name)
        return scale.get_root(), scale.get_kind()

    def add_pattern_with_rows(self, name, steps, rows):
        """Add a pattern through the document and fill its rows, given as {row: [value per step]}."""
        self.document.add_pattern(name, steps)
        for row, values in rows.items():
            for step, value in enumerate(values):
                self.document.set_step_value(name, row, step, value)

    def delete_every_generator(self):
        """Delete every arp and AutoRatchet, which the chains must have stopped using first."""
        song = self.document.song()
        for kind, section in NAMED_GENERATORS.items():
            for name in song.get_generator_names(kind):
                self.document.delete_generator(section, name)

    def text(self):
        return screen_text(self.app)

    async def select_field(self, label):
        """Move a settings page's cursor to the field with this label, wherever the page puts it."""
        labels = [field.label for field in self.app.screen.fields()]
        offset = labels.index(label) - self.app.screen.place
        await self.press(*(['down'] * offset if offset > 0 else ['up'] * -offset))
