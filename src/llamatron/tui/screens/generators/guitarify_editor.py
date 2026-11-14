# llamatron: a music program
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

"""The Guitarify editor: Shape, the fretting hand, and Strokes, the other hand, each a section with a switch of its own."""

from llamatron.composition.file_format import GeneratorKind, GuitarifySetting, Section, SINGLE_NOTES, TUNINGS, SingleNotes, Tuning
from llamatron.composition.generator_settings import (
    DEFAULT_GUITAR_CAPO, DEFAULT_GUITAR_FADE, DEFAULT_GUITAR_LOOSE_TIMING, DEFAULT_GUITAR_POSITION, DEFAULT_GUITAR_SPREAD, DEFAULT_GUITAR_STRINGS, DEFAULT_GUITAR_UPSTROKE,
    EVERY_STRING, MAX_GUITAR_FRET, MAX_GUITAR_PERCENT, MAX_GUITAR_SPREAD, MAX_GUITAR_STRINGS, MIN_GUITAR_STRINGS,
)
from llamatron.composition.guitar_bars import ready_bar_matching
from llamatron.strings.help import HELP_GUITARIFY_EDITOR
from llamatron.strings.labels import (
    Crumb, MSG_GUITAR_BAR_LABEL, MSG_GUITAR_CAPO_LABEL, MSG_GUITAR_FADE_LABEL, MSG_GUITAR_LET_RING_LABEL, MSG_GUITAR_LOOSE_TIMING_LABEL, MSG_GUITAR_POSITION_LABEL,
    MSG_GUITAR_SHAPE_LABEL, MSG_GUITAR_SHAPE_SECTION, MSG_GUITAR_SINGLE_NOTES_LABEL, MSG_GUITAR_SINGLE_NOTES_NAMES, MSG_GUITAR_SPREAD_LABEL, MSG_GUITAR_STRINGS_LABEL,
    MSG_GUITAR_STROKES_LABEL, MSG_GUITAR_STROKES_SECTION, MSG_GUITAR_TUNING_LABEL, MSG_GUITAR_TUNING_NAMES, MSG_GUITAR_UPSTROKE_LABEL, MSG_GUITARIFY_LABEL, MSG_OWN_BAR,
    MSG_READY_BAR_NAMES,
)
from llamatron.strings.legends import What
from llamatron.strings.marks import MSG_GUITAR_BAR_SHOWN, MSG_GUITAR_EVERY_STRING, MSG_GUITAR_FRET, MSG_GUITAR_MILLISECONDS, MSG_GUITAR_NO_CAPO, MSG_GUITAR_OPEN_POSITION
from llamatron.strings.messages import MSG_RENAME_GENERATOR_PROMPT
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.guitar_bar_editor import GuitarBarEditor
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem

SHAPE_SETTINGS = (GuitarifySetting.SHAPE, GuitarifySetting.TUNING, GuitarifySetting.POSITION, GuitarifySetting.CAPO, GuitarifySetting.STRINGS, GuitarifySetting.SINGLE_NOTES)
STROKE_SETTINGS = (
    GuitarifySetting.STROKES, GuitarifySetting.BAR, GuitarifySetting.ACCENTS, GuitarifySetting.CELL, GuitarifySetting.LET_RING, GuitarifySetting.SPREAD, GuitarifySetting.FADE,
    GuitarifySetting.LOOSE_TIMING, GuitarifySetting.UPSTROKE,
)
NO_FRET = 0


def bar_shown(guitar):
    """Return a Guitarify's bar on one line: its ready-made name, or that it is someone's own, how many cells and how long each."""
    ready = ready_bar_matching(cell=guitar.get_cell(), strokes=guitar.get_bar(), accents=guitar.get_accents())
    name = MSG_OWN_BAR if ready is None else MSG_READY_BAR_NAMES[ready]
    return MSG_GUITAR_BAR_SHOWN.format(name=name, count=len(guitar.get_bar()), cell=guitar.get_cell())


class GuitarifyEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.GuitarifyEditor
    HELP = HELP_GUITARIFY_EDITOR
    SECTION = Section.GUITARIFIES
    CRUMBS_BEFORE = (Crumb.GENERATORS,)
    RENAME_PROMPT = MSG_RENAME_GENERATOR_PROMPT.format(label=MSG_GUITARIFY_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def guitar(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.GUITARIFY, name=self.item)

    def store(self, *, setting, value):
        self.document().set_generator_setting(section=Section.GUITARIFIES, name=self.item, setting=setting, value=value)

    def any_written(self, settings):
        written = self.guitar().to_data()
        return any(setting in written for setting in settings)

    def number(self, *, label, setting, current, default, lowest, highest, shown=None):
        """Return a whole number's field, left out of the file while it is the default."""
        return NumberField(
            page=self, label=label, number=current, lowest=lowest, highest=highest, shown=shown,
            set=lambda number: self.store(setting=setting, value=None if number == default else number), clear=lambda: self.store(setting=setting, value=None),
        )

    def choice(self, *, label, setting, current, default, choices, names):
        """Return a choice's field, left out of the file while it is the default."""
        return ChoiceField(
            page=self, label=label, choices=list(choices), current=current, names=[names[choice] for choice in choices], shown=names[current],
            set=lambda chosen: self.store(setting=setting, value=None if chosen == default else chosen),
        )

    def switch(self, *, label, setting, on, default):
        """Return a toggle, left out of the file while it is the default."""
        return Toggle(label=label, on=on, set=lambda chosen: self.store(setting=setting, value=None if chosen == default else chosen))

    def fields(self):
        guitar = self.guitar()
        position = guitar.get_position()
        capo = guitar.get_capo()
        upstroke = guitar.get_upstroke()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            self.heading(label=MSG_GUITAR_SHAPE_SECTION, is_set=lambda: self.any_written(SHAPE_SETTINGS)),
            self.switch(label=MSG_GUITAR_SHAPE_LABEL, setting=GuitarifySetting.SHAPE, on=guitar.shapes(), default=True),
            self.choice(label=MSG_GUITAR_TUNING_LABEL, setting=GuitarifySetting.TUNING, current=guitar.get_tuning(), default=Tuning.STANDARD, choices=TUNINGS, names=MSG_GUITAR_TUNING_NAMES),
            self.number(
                label=MSG_GUITAR_POSITION_LABEL, setting=GuitarifySetting.POSITION, current=position, default=DEFAULT_GUITAR_POSITION, lowest=NO_FRET, highest=MAX_GUITAR_FRET,
                shown=MSG_GUITAR_OPEN_POSITION if position == NO_FRET else MSG_GUITAR_FRET.format(fret=position),
            ),
            self.number(
                label=MSG_GUITAR_CAPO_LABEL, setting=GuitarifySetting.CAPO, current=capo, default=DEFAULT_GUITAR_CAPO, lowest=NO_FRET, highest=MAX_GUITAR_FRET,
                shown=MSG_GUITAR_NO_CAPO if capo == NO_FRET else MSG_GUITAR_FRET.format(fret=capo),
            ),
            self.number(label=MSG_GUITAR_STRINGS_LABEL, setting=GuitarifySetting.STRINGS, current=guitar.get_strings(), default=DEFAULT_GUITAR_STRINGS, lowest=MIN_GUITAR_STRINGS, highest=MAX_GUITAR_STRINGS),
            self.choice(
                label=MSG_GUITAR_SINGLE_NOTES_LABEL, setting=GuitarifySetting.SINGLE_NOTES, current=guitar.get_single_notes(), default=SingleNotes.LEAVE, choices=SINGLE_NOTES,
                names=MSG_GUITAR_SINGLE_NOTES_NAMES,
            ),
            self.heading(label=MSG_GUITAR_STROKES_SECTION, is_set=lambda: self.any_written(STROKE_SETTINGS)),
            self.switch(label=MSG_GUITAR_STROKES_LABEL, setting=GuitarifySetting.STROKES, on=guitar.strikes(), default=True),
            Field(label=MSG_GUITAR_BAR_LABEL, value=lambda: bar_shown(self.guitar()), enter=lambda: self.show_page(GuitarBarEditor(holder=self.holder, name=self.item)), enter_what=What.EDIT),
            self.switch(label=MSG_GUITAR_LET_RING_LABEL, setting=GuitarifySetting.LET_RING, on=guitar.lets_ring(), default=False),
            self.number(
                label=MSG_GUITAR_SPREAD_LABEL, setting=GuitarifySetting.SPREAD, current=guitar.get_spread(), default=DEFAULT_GUITAR_SPREAD, lowest=0, highest=MAX_GUITAR_SPREAD,
                shown=MSG_GUITAR_MILLISECONDS.format(milliseconds=guitar.get_spread()),
            ),
            self.number(label=MSG_GUITAR_FADE_LABEL, setting=GuitarifySetting.FADE, current=guitar.get_fade(), default=DEFAULT_GUITAR_FADE, lowest=0, highest=MAX_GUITAR_PERCENT),
            self.number(label=MSG_GUITAR_LOOSE_TIMING_LABEL, setting=GuitarifySetting.LOOSE_TIMING, current=guitar.get_loose_timing(), default=DEFAULT_GUITAR_LOOSE_TIMING, lowest=0, highest=MAX_GUITAR_PERCENT),
            self.number(
                label=MSG_GUITAR_UPSTROKE_LABEL, setting=GuitarifySetting.UPSTROKE, current=upstroke, default=DEFAULT_GUITAR_UPSTROKE, lowest=EVERY_STRING, highest=MAX_GUITAR_STRINGS,
                shown=MSG_GUITAR_EVERY_STRING if upstroke == EVERY_STRING else None,
            ),
            restart_field(self),
        ]
