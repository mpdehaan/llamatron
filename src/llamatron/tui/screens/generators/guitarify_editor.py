# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Guitarify editor: Shape, the fretting hand, and Strokes, the other hand, each a section with a switch of its own."""

from llamatron.composition import file_format, generator_settings
from llamatron.composition.file_format import Approach, ChordColor, GuitarifySetting, Section, SingleNotes, Tuning
from llamatron.composition.guitar_bars import ready_bar_matching
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.generators.guitar_bar_editor import GuitarBarEditor
from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.shared.field import ChoiceField, Field, NameField, Toggle
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.generator_editor import GeneratorEditor

SHAPE_SETTINGS = (GuitarifySetting.SHAPE, GuitarifySetting.TUNING, GuitarifySetting.POSITION, GuitarifySetting.CAPO, GuitarifySetting.STRINGS, GuitarifySetting.SINGLE_NOTES, GuitarifySetting.COLOR)
STROKE_SETTINGS = (
    GuitarifySetting.STROKES, GuitarifySetting.BAR, GuitarifySetting.ACCENTS, GuitarifySetting.CELL, GuitarifySetting.LET_RING, GuitarifySetting.SPREAD, GuitarifySetting.FADE,
    GuitarifySetting.LOOSE_TIMING, GuitarifySetting.UPSTROKE, GuitarifySetting.APPROACH,
)
NO_FRET = 0


def bar_shown(guitar):
    """Return a Guitarify's bar on one line: its ready-made name, or that it is someone's own, how many cells and how long each."""
    ready = ready_bar_matching(cell=guitar.get_cell(), strokes=guitar.get_bar(), accents=guitar.get_accents())
    name = labels.MSG_OWN_BAR if ready is None else labels.MSG_READY_BAR_NAMES[ready]
    return marks.MSG_GUITAR_BAR_SHOWN.format(name=name, count=len(guitar.get_bar()), cell=guitar.get_cell())


class GuitarifyEditor(GeneratorEditor, FieldPage):

    """The page that edits a Guitarify generator, which voices and strums a part as a guitar would."""

    KEYS = keybindings.GuitarifyEditor
    HELP = help_text.HELP_GUITARIFY_EDITOR
    SECTION = Section.GUITARIFIES
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_GUITARIFY_LABEL)

    def any_written(self, settings):
        written = self.settings().to_data()
        return any(setting in written for setting in settings)

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
        guitar = self.settings()
        position = guitar.get_position()
        capo = guitar.get_capo()
        upstroke = guitar.get_upstroke()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            self.heading(label=labels.MSG_GUITAR_SHAPE_SECTION, is_set=lambda: self.any_written(SHAPE_SETTINGS)),
            self.switch(label=labels.MSG_GUITAR_SHAPE_LABEL, setting=GuitarifySetting.SHAPE, on=guitar.shapes(), default=True),
            self.choice(label=labels.MSG_GUITAR_TUNING_LABEL, setting=GuitarifySetting.TUNING, current=guitar.get_tuning(), default=Tuning.STANDARD, choices=file_format.TUNINGS, names=labels.MSG_GUITAR_TUNING_NAMES),
            self.number_field(
                label=labels.MSG_GUITAR_POSITION_LABEL, setting=GuitarifySetting.POSITION, current=position, default=generator_settings.DEFAULT_GUITAR_POSITION,
                shown=marks.MSG_GUITAR_OPEN_POSITION if position == NO_FRET else marks.MSG_GUITAR_FRET.format(fret=position),
            ),
            self.number_field(
                label=labels.MSG_GUITAR_CAPO_LABEL, setting=GuitarifySetting.CAPO, current=capo, default=generator_settings.DEFAULT_GUITAR_CAPO,
                shown=marks.MSG_GUITAR_NO_CAPO if capo == NO_FRET else marks.MSG_GUITAR_FRET.format(fret=capo),
            ),
            self.number_field(label=labels.MSG_GUITAR_STRINGS_LABEL, setting=GuitarifySetting.STRINGS, current=guitar.get_strings(), default=generator_settings.DEFAULT_GUITAR_STRINGS),
            self.choice(
                label=labels.MSG_GUITAR_SINGLE_NOTES_LABEL, setting=GuitarifySetting.SINGLE_NOTES, current=guitar.get_single_notes(), default=SingleNotes.LEAVE, choices=file_format.SINGLE_NOTES,
                names=labels.MSG_GUITAR_SINGLE_NOTES_NAMES,
            ),
            self.choice(label=labels.MSG_GUITAR_COLOR_LABEL, setting=GuitarifySetting.COLOR, current=guitar.get_color(), default=ChordColor.AS_WRITTEN, choices=file_format.CHORD_COLORS, names=labels.MSG_GUITAR_COLOR_NAMES),
            self.heading(label=labels.MSG_GUITAR_STROKES_SECTION, is_set=lambda: self.any_written(STROKE_SETTINGS)),
            self.switch(label=labels.MSG_GUITAR_STROKES_LABEL, setting=GuitarifySetting.STROKES, on=guitar.strikes(), default=True),
            Field(label=labels.MSG_GUITAR_BAR_LABEL, value=lambda: bar_shown(self.settings()), enter=lambda: self.show_page(GuitarBarEditor(holder=self.holder, name=self.item)), enter_what=legends.What.EDIT),
            self.switch(label=labels.MSG_GUITAR_LET_RING_LABEL, setting=GuitarifySetting.LET_RING, on=guitar.lets_ring(), default=False),
            self.number_field(
                label=labels.MSG_GUITAR_SPREAD_LABEL, setting=GuitarifySetting.SPREAD, current=guitar.get_spread(), default=generator_settings.DEFAULT_GUITAR_SPREAD,
                shown=marks.MSG_GUITAR_MILLISECONDS.format(milliseconds=guitar.get_spread()),
            ),
            self.number_field(label=labels.MSG_GUITAR_FADE_LABEL, setting=GuitarifySetting.FADE, current=guitar.get_fade(), default=generator_settings.DEFAULT_GUITAR_FADE),
            self.number_field(label=labels.MSG_GUITAR_LOOSE_TIMING_LABEL, setting=GuitarifySetting.LOOSE_TIMING, current=guitar.get_loose_timing(), default=generator_settings.DEFAULT_GUITAR_LOOSE_TIMING),
            self.number_field(
                label=labels.MSG_GUITAR_UPSTROKE_LABEL, setting=GuitarifySetting.UPSTROKE, current=upstroke, default=generator_settings.DEFAULT_GUITAR_UPSTROKE,
                shown=marks.MSG_GUITAR_EVERY_STRING if upstroke == generator_settings.EVERY_STRING else None,
            ),
            self.choice(label=labels.MSG_GUITAR_APPROACH_LABEL, setting=GuitarifySetting.APPROACH, current=guitar.get_approach(), default=Approach.OFF, choices=file_format.APPROACHES, names=labels.MSG_GUITAR_APPROACH_NAMES),
            restart_field(self),
        ]
