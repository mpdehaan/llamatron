# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Arp editor page."""

from llamatron.engine.generators import arp as arp_plugin
from llamatron.engine.generators.arp import model as arp_model, model as arp_settings, schema, strings as arp_strings
from llamatron.engine.generators.arp.model import ArpSetting
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.screens.generators.offsets_editor import OffsetsEditor
from llamatron.interface.tracker.screens.shared import shared
from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, NameField, NumberField
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generator_editor import GeneratorEditor
from llamatron.interface.tracker.screens.shared.restart_field import restart_field
from llamatron.interface.tracker.screens.shared.shared import numbers_text
from llamatron.interface.tracker.screens.shared.time_field import time_field
from llamatron.model.objects.naming import words
from llamatron.model.schema import file_format
from llamatron.user_strings import help as help_text, labels, legends, marks, messages


JUMPS = list(arp_model.OCTAVE_JUMPS)
# How many offsets a new set has, as on a groovebox.
DEFAULT_OFFSET_STEPS = 8
# What a note adds to a register when the arp sets nothing.
NO_ADD = 0


def offsets_text(offsets):
    if offsets is None:
        return marks.MSG_NONE_SHOWN
    return numbers_text(offsets)


class ArpEditor(GeneratorEditor, FieldPage):

    """The page that edits an arpeggiator: the order its notes play in, its rate, its range and its other settings."""

    KEYS = keybindings.ArpEditor
    HELP = help_text.HELP_ARP_EDITOR
    SECTION = arp_plugin.SECTION
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=arp_strings.MSG_LABEL)

    def set_range(self, octaves):
        self.store(setting=ArpSetting.OCTAVE_RANGE, value=None if octaves == schema.MIN_OCTAVE_RANGE else octaves)

    def set_jump(self, jump):
        self.store(setting=ArpSetting.OCTAVE_JUMP, value=None if jump == JUMPS[0] else jump)

    def edit_offsets(self):
        if self.settings().get_offsets() is None:
            self.store(setting=ArpSetting.OFFSETS, value=[arp_settings.NO_OFFSET] * DEFAULT_OFFSET_STEPS)
        self.show_page(OffsetsEditor(holder=self.holder, name=self.item))

    def fields(self):
        arp = self.settings()
        step = arp.get_step()
        order = arp.get_order() or shared.DEFAULT_ORDER
        octaves = arp.get_octave_range() or schema.MIN_OCTAVE_RANGE
        jump = arp.get_octave_jump() or JUMPS[0]
        return [
            NameField(value=lambda: self.item, rename=self.rename),
            time_field(page=self, label=labels.MSG_STEP_LABEL, written=step, first=marks.MSG_PATTERN_STEP_SHOWN, store=lambda value: self.store(setting=ArpSetting.STEP, value=value)),
            ChoiceField(page=self, label=labels.MSG_ORDER_LABEL, choices=shared.ORDERS, current=order, set=lambda value: self.store(setting=ArpSetting.ORDER, value=value)),
            NumberField(page=self, label=labels.MSG_OCTAVE_RANGE_LABEL, number=octaves, lowest=schema.MIN_OCTAVE_RANGE, highest=schema.MAX_OCTAVE_RANGE, set=self.set_range),
            ChoiceField(page=self, label=labels.MSG_OCTAVE_JUMP_LABEL, choices=JUMPS, current=jump, names=[words(name) for name in JUMPS], shown=words(jump), set=self.set_jump),
            Field(label=labels.MSG_OFFSETS_LABEL, value=lambda: offsets_text(arp.get_offsets()), adjust=None, enter=self.edit_offsets, enter_what=legends.What.EDIT,
                  clear=lambda: self.store(setting=ArpSetting.OFFSETS, value=None), clear_what=legends.What.REMOVE),
            *[self.note_add_field(register) for register in file_format.REGISTER_NAMES],
            restart_field(self),
        ]

    def note_add_field(self, register):
        """Return the field for what every note the arp plays adds to a register, within the current song's Allowed Inc Max, nothing being left out of the file."""
        most = self.document().song().get_register(register).get_allowed_inc_max()
        setting = arp_settings.ARP_NOTE_ADDS[register]
        return NumberField(
            page=self, label=labels.MSG_ARP_NOTE_ADD_LABEL.format(name=register), number=self.settings().get_note_add(register) or NO_ADD, lowest=-most, highest=most,
            set=lambda number: self.store(setting=setting, value=number or None), clear=lambda: self.store(setting=setting, value=None),
        )
