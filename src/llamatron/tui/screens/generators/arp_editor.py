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

"""The Arp editor page."""

from llamatron.tui.screens.generators.restart_field import restart_field
from llamatron.tui.screens.generators.time_field import time_field
from llamatron.composition import file_format
from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition import generator_settings
from llamatron.composition.generator_settings import ArpSetting, written_name
from llamatron.generators.arp import MAX_OCTAVE_RANGE, MIN_OCTAVE_RANGE, OctaveJump
from llamatron.composition.naming import words
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui.screens.shared.field import ChoiceField, Field, NameField, NumberField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.generators.offsets_editor import OffsetsEditor
from llamatron.tui.screens.shared.shared import DEFAULT_ORDER, NO_SEED, numbers_text, ORDERS
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui import keybindings


JUMPS = [written_name(jump) for jump in OctaveJump]
# How many offsets a new set has, as on a groovebox.
DEFAULT_OFFSET_STEPS = 8
# What a note adds to a register when the arp sets nothing.
NO_ADD = 0


def offsets_text(offsets):
    if offsets is None:
        return marks.MSG_NONE_SHOWN
    return numbers_text(offsets)


class ArpEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.ArpEditor
    HELP = help_text.HELP_ARP_EDITOR
    SECTION = Section.ARPS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_ARP_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def arp(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.ARP, name=self.item)

    def set_value(self, *, setting, value):
        """Set one of the arp's settings, or None to leave it out and use its default."""
        self.document().set_generator_setting(section=Section.ARPS, name=self.item, setting=setting, value=value)

    def set_range(self, octaves):
        self.set_value(setting=ArpSetting.OCTAVE_RANGE, value=None if octaves == MIN_OCTAVE_RANGE else octaves)

    def set_jump(self, jump):
        self.set_value(setting=ArpSetting.OCTAVE_JUMP, value=None if jump == JUMPS[0] else jump)

    def edit_offsets(self):
        if self.arp().get_offsets() is None:
            self.set_value(setting=ArpSetting.OFFSETS, value=[generator_settings.NO_OFFSET] * DEFAULT_OFFSET_STEPS)
        self.show_page(OffsetsEditor(holder=self.holder, name=self.item))

    def fields(self):
        arp = self.arp()
        step = arp.get_step()
        order = arp.get_order() or DEFAULT_ORDER
        octaves = arp.get_octave_range() or MIN_OCTAVE_RANGE
        jump = arp.get_octave_jump() or JUMPS[0]
        seed = arp.get_seed()
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(page=self, label=labels.MSG_STEP_LABEL, written=step, first=marks.MSG_PATTERN_STEP_SHOWN, store=lambda value: self.set_value(setting=ArpSetting.STEP, value=value)),
            ChoiceField(page=self, label=labels.MSG_ORDER_LABEL, choices=ORDERS, current=order, set=lambda value: self.set_value(setting=ArpSetting.ORDER, value=value)),
            NumberField(page=self, label=labels.MSG_OCTAVE_RANGE_LABEL, number=octaves, lowest=MIN_OCTAVE_RANGE, highest=MAX_OCTAVE_RANGE, set=self.set_range),
            ChoiceField(page=self, label=labels.MSG_OCTAVE_JUMP_LABEL, choices=JUMPS, current=jump, names=[words(name) for name in JUMPS], shown=words(jump), set=self.set_jump),
            Field(label=labels.MSG_OFFSETS_LABEL, value=lambda: offsets_text(arp.get_offsets()), adjust=None, enter=self.edit_offsets, enter_what=legends.What.EDIT,
                  clear=lambda: self.set_value(setting=ArpSetting.OFFSETS, value=None), clear_what=legends.What.REMOVE),
            NumberField(
                page=self, label=labels.MSG_SEED_LABEL, number=seed, start=NO_SEED, shown=marks.MSG_SONG_SEED_SHOWN if seed is None else None,
                set=lambda number: self.set_value(setting=ArpSetting.SEED, value=number),
                clear=lambda: self.set_value(setting=ArpSetting.SEED, value=None), clear_what=legends.MSG_USE_SONG_SEED_WHAT,
            ),
            *[self.note_add_field(register) for register in file_format.REGISTER_NAMES],
            restart_field(self),
        ]

    def note_add_field(self, register):
        """Return the field for what every note the arp plays adds to a register, within the current song's Allowed Inc Max, nothing being left out of the file."""
        most = self.document().song().get_register(register).get_allowed_inc_max()
        setting = generator_settings.ARP_NOTE_ADDS[register]
        return NumberField(
            page=self, label=labels.MSG_ARP_NOTE_ADD_LABEL.format(name=register), number=self.arp().get_note_add(register) or NO_ADD, lowest=-most, highest=most,
            set=lambda number: self.set_value(setting=setting, value=number or None), clear=lambda: self.set_value(setting=setting, value=None),
        )
