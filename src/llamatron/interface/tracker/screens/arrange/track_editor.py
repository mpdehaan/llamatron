# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Track editor page: one track's settings, which apply to every clip on it."""

import functools
from rich.text import Text

from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.arrange.generators_field import generators_field
from llamatron.interface.tracker.screens.arrange.groove_choice import groove_choice_field
from llamatron.interface.tracker.screens.generators.euclid_fields import euclid_section, pick_rhythm
from llamatron.interface.tracker.screens.generators.strum_fields import strum_section
from llamatron.interface.tracker.screens.shared import statements
from llamatron.interface.tracker.screens.shared.field import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.octave_field import octave_field
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.interface.tracker.screens.shared.statements import statement_section
from llamatron.interface.tracker.text import sorted_names
from llamatron.model.schema import defaults, file_format, limits
from llamatron.model.schema.file_format import EuclidPart, Section, TrackSetting
from llamatron.model.values import midi
from llamatron.user_strings import help as help_text, labels, legends, marks, messages



class TrackEditor(ShowsNamedItem, FieldPage):
    """One track's settings, which apply to every clip on it."""

    KEYS = keybindings.TrackEditor

    HELP = help_text.HELP_TRACK_EDITOR
    SECTION = Section.TRACKS
    CRUMBS_BEFORE = (labels.Crumb.ARRANGE,)
    ITEM_CRUMB = labels.MSG_TRACK_CRUMB
    RENAME_PROMPT = messages.MSG_RENAME_TRACK_PROMPT

    def track(self):
        return self.document().song().get_track(self.item)

    def numbers(self):
        return self.track().get_cc_numbers()

    def set_cc(self, *, lane, number):
        self.document().change_set(self.document().song().get_track(self.item).set_cc_number, lane=lane, number=number)

    def set_transpose(self, transpose):
        self.document().change_set(self.document().song().get_track(self.item).set_transpose, transpose)

    def transpose_text(self):
        transpose = self.track().get_transpose()
        return marks.MSG_SIGNED_NUMBER.format(number=transpose) if transpose else str(defaults.DEFAULT_TRANSPOSE)

    def cc_text(self, lane):
        number = self.numbers()[lane]
        return marks.MSG_NONE_SHOWN if number is None else str(number)

    def cc_field(self, lane):
        """Return the field for one of the four CC lanes, numbered from 1 on screen."""
        label = labels.MSG_CC_LABEL.format(number=lane + 1)
        return NumberField(
            page=self, label=label, number=self.numbers()[lane], start=midi.MIN_CC_NUMBER, shown=self.cc_text(lane), lowest=midi.MIN_CC_NUMBER, highest=midi.MAX_CC_NUMBER,
            title=messages.MSG_CC_PROMPT.format(number=lane + 1), set=lambda number: self.set_cc(lane=lane, number=number),
            clear=lambda: self.set_cc(lane=lane, number=None), clear_what=legends.MSG_NO_CC_WHAT,
        )

    def groove_field(self):
        """Return the Groove field: the scene's or the song's by default, off to play straight, or one by name."""
        return groove_choice_field(
            page=self, title=messages.MSG_TRACK_GROOVE_TITLE, choice=self.track().get_groove_choice(),
            inherited_option=marks.MSG_SCENE_OR_SONG_GROOVE_SHOWN, inherited_shown=marks.MSG_SCENE_OR_SONG_GROOVE_SHOWN,
            choose=lambda choice: self.document().change_set(self.document().song().get_track(self.item).set_groove_choice, choice=choice, song=self.document().song()), clear_what=legends.MSG_USE_SCENE_GROOVE_WHAT,
        )

    def pick_instrument(self):
        """Choose the instrument the track plays through in real time, from the set's, or none."""
        instruments = sorted_names(self.document().get_setlist().get_instrument_names())
        self.pick(title=labels.MSG_INSTRUMENT_LABEL, values=[None, *instruments], shown=[marks.MSG_NONE_SHOWN, *instruments], current=self.track().get_instrument_name(), then=self.set_instrument)

    def set_instrument(self, instrument):
        self.document().set_track_instrument(name=self.item, instrument=instrument)

    def register_field(self, *, label, current, bind):
        """Return a field binding a CC lane or the velocity to a register, (none) first and then AX to DX."""
        choices = [marks.MSG_NONE_SHOWN, *file_format.REGISTER_NAMES]
        return ChoiceField(
            page=self, label=label, choices=choices, current=current or marks.MSG_NONE_SHOWN,
            set=lambda choice: bind(None if choice == marks.MSG_NONE_SHOWN else choice), clear=lambda: bind(None), clear_what=legends.MSG_UNBIND_WHAT,
        )

    def default_velocity_field(self):
        """Return the Default velocity field: what a step with no velocity typed plays at on the track, shown as its instrument's until the track has its own."""
        track = self.track()
        own = track.get_default_velocity()
        above = self.document().song().default_velocity_of(track)
        shown = None if own is not None else marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=above) if self.document().song().instrument_of(track) is not None else above
        return self.setting_number_field(label=labels.MSG_DEFAULT_VELOCITY_LABEL, holder=self.track(), name=TrackSetting.DEFAULT_VELOCITY, start=above, shown=shown, typed=above, clear_what=legends.MSG_NO_DEFAULT_VELOCITY_WHAT)

    def accent_field(self):
        """Return the Accent field: what a step with its Accent on adds to its velocity on the track, on top of its instrument's accent."""
        accent = self.track().get_accent()
        return self.setting_number_field(label=labels.MSG_ACCENT_LABEL, holder=self.track(), name=TrackSetting.ACCENT, in_effect=accent, shown=marks.MSG_ACCENT_SHOWN.format(accent=accent), clear_what=legends.MSG_NO_DEFAULT_VELOCITY_WHAT)

    def instrument_field(self):
        return Field(label=labels.MSG_INSTRUMENT_LABEL, value=lambda: self.track().get_instrument_name() or marks.MSG_NONE_SHOWN, adjust=None, enter=self.pick_instrument, enter_what=legends.What.CHOOSE,
                     clear=lambda: self.set_instrument(None), clear_what=legends.MSG_NO_INSTRUMENT_WHAT)

    def fields(self):
        track = self.track()
        drum = track.is_drum()
        result = [
            NameField(value=lambda: self.item, rename=self.rename),
            Toggle(label=labels.MSG_DRUM_LABEL, on=drum, set=lambda on: self.document().change_set(self.document().song().get_track(self.item).set_drum, on)),
            Toggle(label=labels.MSG_MUTE_LABEL, on=track.is_muted(), set=lambda on: self.document().change_set(self.document().song().get_track(self.item).set_mute, on)),
            self.groove_field(),
        ]
        if drum:
            result.append(Field(label=labels.MSG_TRANSPOSE_LABEL, value=lambda: marks.MSG_DRUM_TRACK_SHOWN))
        else:
            result.append(NumberField(
                page=self, label=labels.MSG_TRANSPOSE_LABEL, number=track.get_transpose(), shown=self.transpose_text(), lowest=-limits.MAX_TRANSPOSE, highest=limits.MAX_TRANSPOSE,
                set=self.set_transpose, clear=lambda: self.set_transpose(defaults.DEFAULT_TRANSPOSE), clear_what=legends.MSG_NO_TRANSPOSE_WHAT,
            ))
        result += [
            octave_field(page=self, label=labels.MSG_LOWEST_OCTAVE_LABEL, current=track.get_lowest_octave, highest=track.get_highest_octave, lowest=lambda: limits.MIN_OCTAVE, default=limits.MIN_OCTAVE,
                              set_octave=lambda octave: self.document().change_set(self.document().song().get_track(self.item).set_lowest_octave, octave)),
            octave_field(page=self, label=labels.MSG_HIGHEST_OCTAVE_LABEL, current=track.get_highest_octave, highest=lambda: limits.MAX_OCTAVE, lowest=track.get_lowest_octave, default=limits.MAX_OCTAVE,
                              set_octave=lambda octave: self.document().change_set(self.document().song().get_track(self.item).set_highest_octave, octave)),
        ]
        result += [self.default_velocity_field(), self.accent_field()]
        result += [self.cc_field(lane) for lane in range(len(file_format.CC_ROWS))]
        registers = track.get_cc_registers()
        result += [
            self.register_field(label=labels.MSG_CC_REGISTER_LABEL.format(number=lane + 1), current=registers[lane],
                                bind=lambda register, lane=lane: self.document().change_set(self.document().song().get_track(self.item).set_cc_register, lane=lane, register=register))
            for lane in range(len(file_format.CC_ROWS))
        ]
        result.append(self.register_field(label=labels.MSG_VELOCITY_REGISTER_LABEL, current=track.get_velocity_register(),
                                          bind=lambda register: self.document().change_set(self.document().song().get_track(self.item).set_velocity_register, register)))
        result.append(generators_field(page=self, names=lambda: self.track().get_chain_names(), store=lambda names: self.document().change_set(self.document().song().get_track(self.item).set_chain_names, names=names, song=self.document().song())))
        result.append(self.instrument_field())
        result += euclid_section(page=self, value=track.get_euclid_setting, store=lambda part, value: self.store_euclid(part=part, value=value))
        result += strum_section(
            page=self, value=track.get_strum_setting, first=marks.MSG_NONE_SHOWN,
            store=lambda part, value: self.document().change_set(self.document().song().get_track(self.item).set_strum_setting, part=part, value=value),
        )
        tables = ((labels.MSG_BYPASS_WHEN_LABEL, statements.FIRST_TABLE, TrackSetting.BYPASS_WHEN), (labels.MSG_SKIP_WHEN_LABEL, statements.SECOND_TABLE, TrackSetting.SKIP_WHEN))
        for label, table, name in tables:
            # The statements about the registers that bypass the generators of the track's clips, and that make its clips sit out.
            result += statement_section(
                page=self, label=label, table=table, statements=functools.partial(track.get_statements, name),
                store=lambda place, statement, name=name: self.document().change_set(self.document().song().get_track(self.item).set_statement, name=name, place=place, statement=statement),
            )
        return result

    def store_euclid(self, *, part, value):
        self.document().change_set(self.document().song().get_track(self.item).set_euclid_setting, part=part, value=value)

    def page_keys(self):
        if self.field().label == labels.MSG_EUCLID_FIELD_LABELS[EuclidPart.HITS]:
            return [self.bind(self.KEYS.PICK_RHYTHM, action=lambda: pick_rhythm(page=self, store=lambda part, value: self.store_euclid(part=part, value=value)))]
        return []

    def remarks(self, width):
        return [Text(messages.MSG_TRANSPOSE_NOTE, style=Style.DIM)]
