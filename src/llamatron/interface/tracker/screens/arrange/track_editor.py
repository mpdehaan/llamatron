# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Track editor page: one track's settings, which apply to every clip on it."""

import functools
from rich.text import Text

from llamatron.interface.forms.nodes import Field, NameField, NumberField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabBox, TabColumn
from llamatron.interface.tracker import keybindings
from llamatron.interface.tracker.document_parts import built_in_place
from llamatron.interface.tracker.drawing import Style
from llamatron.interface.tracker.screens.arrange.groove_choice import groove_choice_field
from llamatron.interface.tracker.screens.shared import percentages
from llamatron.interface.tracker.screens.shared.arrange_tabs import built_in_tabs, fields_tab
from llamatron.interface.tracker.screens.shared.field_page import FieldPage
from llamatron.interface.tracker.screens.shared.generators_field import generators_field
from llamatron.interface.tracker.screens.shared.octave_field import octave_field
from llamatron.interface.tracker.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.interface.tracker.text import sorted_names
from llamatron.model.schema import defaults, file_format, generator_plugins, limits
from llamatron.model.schema.file_format import Section, TrackSetting
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
        song = self.document().song()
        return song.get_track(self.item)

    def numbers(self):
        return self.track().get_cc_numbers()

    def set_cc(self, *, lane, number):
        self._change(self.track().set_cc_number, lane=lane, number=number)

    def set_transpose(self, transpose):
        self._change(self.track().set_transpose, transpose)

    def transpose_text(self):
        transpose = self.track().get_transpose()
        if not transpose:
            return str(defaults.DEFAULT_TRANSPOSE)
        return marks.MSG_SIGNED_NUMBER.format(number=transpose)

    def cc_text(self, lane):
        number = self.numbers()[lane]
        if number is None:
            return marks.MSG_NONE_SHOWN
        return str(number)

    def cc_field(self, lane):
        """Return the field for one of the four CC lanes, numbered from 1 on screen."""
        label = labels.MSG_CC_LABEL.format(number=lane + 1)
        title = messages.MSG_CC_PROMPT.format(number=lane + 1)
        return NumberField(
            page=self, label=label, number=self.numbers()[lane], start=midi.MIN_CC_NUMBER, shown=self.cc_text(lane), lowest=midi.MIN_CC_NUMBER, highest=midi.MAX_CC_NUMBER,
            title=title, set=functools.partial(self._set_cc_number, lane=lane), clear=functools.partial(self._set_cc_number, None, lane=lane),
            clear_what=legends.MSG_NO_CC_WHAT,
        )

    def _set_cc_number(self, number, *, lane):
        self.set_cc(lane=lane, number=number)

    def groove_field(self):
        """Return the Groove field: the scene's or the song's by default, off to play straight, or one by name."""
        return groove_choice_field(
            page=self, title=messages.MSG_TRACK_GROOVE_TITLE, choice=self.track().get_groove_choice(),
            inherited_option=marks.MSG_SCENE_OR_SONG_GROOVE_SHOWN, inherited_shown=marks.MSG_SCENE_OR_SONG_GROOVE_SHOWN,
            choose=self._set_groove, clear_what=legends.MSG_USE_SCENE_GROOVE_WHAT,
        )

    def _set_groove(self, choice):
        song = self.document().song()
        self._change(self.track().set_groove_choice, choice=choice, song=song)

    def pick_instrument(self):
        """Choose the instrument the track plays through in real time, from the set's, or none."""
        setlist = self.document().get_setlist()
        instruments = sorted_names(setlist.get_instrument_names())
        current = self.track().get_instrument_name()
        self.pick(title=labels.MSG_INSTRUMENT_LABEL, values=[None, *instruments], shown=[marks.MSG_NONE_SHOWN, *instruments], current=current, then=self.set_instrument)

    def set_instrument(self, instrument):
        self.document().set_track_instrument(name=self.item, instrument=instrument)

    def default_velocity_field(self):
        """Return the Default velocity field: what a step with no velocity typed plays at on the track, shown as its instrument's until the track has its own."""
        track = self.track()
        song = self.document().song()
        above = song.default_velocity_of(track)
        if track.get_default_velocity() is not None:
            shown = None
        elif song.instrument_of(track) is not None:
            shown = marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=above)
        else:
            shown = above
        return self.setting_number_field(label=labels.MSG_DEFAULT_VELOCITY_LABEL, holder=track, name=TrackSetting.DEFAULT_VELOCITY, start=above, shown=shown, typed=above, clear_what=legends.MSG_NO_DEFAULT_VELOCITY_WHAT)

    def velocity_change_field(self):
        """Return the Velocity field: the percentage of its written velocity every clip of the track plays, stacking with the
        instrument's, the scene's and the clip's, 100% until set."""
        holder = self.track()
        percent = holder.get_velocity_percent()
        shown = percentages.percent_shown(percentages.UNCHANGED if percent is None else percent)
        return self.setting_number_field(label=labels.MSG_VELOCITY_PERCENT_LABEL, holder=holder, name=TrackSetting.VELOCITY, shown=shown, start=percentages.UNCHANGED, clear_what=legends.MSG_RAMP_BLANK_WHAT)

    def accent_field(self):
        """Return the Accent field: what a step with its Accent on adds to its velocity on the track, on top of its instrument's accent."""
        track = self.track()
        accent = track.get_accent()
        shown = marks.MSG_ACCENT_SHOWN.format(accent=accent)
        return self.setting_number_field(label=labels.MSG_ACCENT_LABEL, holder=track, name=TrackSetting.ACCENT, in_effect=accent, shown=shown, clear_what=legends.MSG_NO_DEFAULT_VELOCITY_WHAT)

    def instrument_field(self):
        return Field(label=labels.MSG_INSTRUMENT_LABEL, value=self._instrument_shown, adjust=None, enter=self.pick_instrument, enter_what=legends.What.CHOOSE,
                     clear=functools.partial(self.set_instrument, None), clear_what=legends.MSG_NO_INSTRUMENT_WHAT)

    def _instrument_shown(self):
        return self.track().get_instrument_name() or marks.MSG_NONE_SHOWN

    def fields(self):
        return [NameField(value=self._item_name, rename=self.rename), TabBox(tabs=self._tabs())]

    def _tabs(self):
        """Return the track's tabs: Settings, MIDI CCs, the built-in generators in the order they run, then More Generators,
        whose list runs after every built-in."""
        track = self.track()
        general = [
            self.instrument_field(), Toggle(label=labels.MSG_DRUM_LABEL, on=track.is_drum(), set=self._set_drum),
            Toggle(label=labels.MSG_MUTE_LABEL, on=track.is_muted(), set=self._set_mute), self.groove_field(),
        ]
        notes = [self._transpose_field(track), *self._octave_fields(track), self.default_velocity_field(), self.accent_field(), self.velocity_change_field()]
        numbers = [self.cc_field(lane) for lane in range(len(file_format.CC_ROWS))]
        return [
            Tab(label=labels.MSG_SETTINGS_TAB, columns=[
                TabColumn(heading=labels.MSG_ROUTING_HEADING, fields=general), TabColumn(heading=labels.MSG_NOTES_HEADING, fields=notes),
            ]),
            Tab(label=labels.MSG_CC_LANES_TAB, columns=[TabColumn(heading=None, fields=numbers)]),
            *built_in_tabs(page=self, track=self.item, scene=built_in_place.OF_THE_TRACK, kinds=generator_plugins.built_in_kinds()),
            fields_tab(label=labels.MSG_USER_TAB, fields=[generators_field(page=self, names=self._chain_names, store=self._set_chain_names)]),
        ]

    def _item_name(self):
        return self.item

    def _set_drum(self, on):
        self._change(self.track().set_drum, on)

    def _set_mute(self, on):
        self._change(self.track().set_mute, on)

    def _transpose_field(self, track):
        """Return the Transpose field, which a drum track only shows, since its notes are drums."""
        if track.is_drum():
            return Field(label=labels.MSG_TRANSPOSE_LABEL, value=self._drum_transpose_shown)
        return NumberField(
            page=self, label=labels.MSG_TRANSPOSE_LABEL, number=track.get_transpose(), shown=self.transpose_text(), lowest=-limits.MAX_TRANSPOSE, highest=limits.MAX_TRANSPOSE,
            set=self.set_transpose, clear=functools.partial(self.set_transpose, defaults.DEFAULT_TRANSPOSE), clear_what=legends.MSG_NO_TRANSPOSE_WHAT,
        )

    @staticmethod
    def _drum_transpose_shown():
        return marks.MSG_DRUM_TRACK_SHOWN

    def _octave_fields(self, track):
        """Return the Lowest and Highest octave fields, each kept from crossing the other."""
        lowest = octave_field(page=self, label=labels.MSG_LOWEST_OCTAVE_LABEL, current=track.get_lowest_octave, highest=track.get_highest_octave,
                              lowest=self._lowest_octave, default=limits.MIN_OCTAVE, set_octave=self._set_lowest_octave)
        highest = octave_field(page=self, label=labels.MSG_HIGHEST_OCTAVE_LABEL, current=track.get_highest_octave, highest=self._highest_octave,
                               lowest=track.get_lowest_octave, default=limits.MAX_OCTAVE, set_octave=self._set_highest_octave)
        return [lowest, highest]

    @staticmethod
    def _lowest_octave():
        return limits.MIN_OCTAVE

    @staticmethod
    def _highest_octave():
        return limits.MAX_OCTAVE

    def _set_lowest_octave(self, octave):
        self._change(self.track().set_lowest_octave, octave)

    def _set_highest_octave(self, octave):
        self._change(self.track().set_highest_octave, octave)

    def _chain_names(self):
        return self.track().get_chain_names()

    def _set_chain_names(self, names):
        song = self.document().song()
        self._change(self.track().set_chain_names, names=names, song=song)

    def remarks(self, width):
        return [Text(messages.MSG_TRANSPOSE_NOTE, style=Style.DIM)]

    def _change(self, setter, *arguments, **named):
        """Change the track through one of its setters, as one edit of the set."""
        self.document().change_set(setter, *arguments, **named)
