# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""One track's page as a presenter: its name, then its tabs, Settings (where it plays, and how its notes play), MIDI CCs, its
built-in generators in the order they run, and More Generators, whose list runs after every built-in."""

import functools

from llamatron.interface.forms import percentages
from llamatron.interface.forms.nodes import Field, NameField, NumberField, SettingNumberField, Toggle
from llamatron.interface.forms.tab_box import Tab, TabBox, TabColumn
from llamatron.interface.forms.text import sorted_names
from llamatron.interface.pages import built_in_place
from llamatron.interface.pages.arrange_tabs import built_in_tabs, fields_tab
from llamatron.interface.pages.generators_field import generators_field
from llamatron.interface.pages.groove_choice import groove_choice_field
from llamatron.interface.pages.octave_field import octave_field
from llamatron.model.schema import defaults, file_format, generator_plugins, limits
from llamatron.model.schema.file_format import InstrumentRole, TrackSetting
from llamatron.model.values import midi
from llamatron.user_strings import errors, labels, legends, marks, messages


class TrackPresenter:
    """What a track's page shows and does, for one track of the current song by name. Its page does what only the tracker can:
    rename(), pick() among choices, and the page actions a built-in generator's tab and the Generators field ask of it."""

    __slots__ = ('_page', '_document', '_name')

    def __init__(self, *, page, document, name):
        self._page = page
        self._document = document
        self._name = name

    def track(self):
        song = self._document.song()
        return song.get_track(self._name)

    def form(self):
        """Return the page's form: the track's name, then its tabs."""
        return [NameField(value=lambda: self._name, rename=self._page.rename), TabBox(tabs=self.tabs())]

    def tabs(self):
        """Return the track's tabs: Settings, MIDI CCs, the built-in generators in the order they run, then More Generators."""
        track = self.track()
        general = [
            self.instrument_field(), Toggle(label=labels.MSG_DRUM_LABEL, on=track.is_drum(), set=self._set_drum),
            Toggle(label=labels.MSG_MUTE_LABEL, on=track.is_muted(), set=self._set_mute), self.groove_field(),
        ]
        notes = [self.transpose_field(track), *self.octave_fields(track), self.default_velocity_field(), self.accent_field(), self.velocity_change_field()]
        numbers = [self.cc_field(lane) for lane in range(len(file_format.CC_ROWS))]
        generators = generators_field(page=self._page, names=self._chain_names, store=self._set_chain_names)
        return [
            Tab(label=labels.MSG_SETTINGS_TAB, columns=[
                TabColumn(heading=labels.MSG_ROUTING_HEADING, fields=general), TabColumn(heading=labels.MSG_NOTES_HEADING, fields=notes),
            ]),
            Tab(label=labels.MSG_CC_LANES_TAB, columns=[TabColumn(heading=None, fields=numbers)]),
            *built_in_tabs(page=self._page, track=self._name, scene=built_in_place.OF_THE_TRACK, kinds=generator_plugins.built_in_kinds()),
            fields_tab(label=labels.MSG_USER_TAB, fields=[generators]),
        ]

    def cc_field(self, lane):
        """Return the field for one of the four CC lanes, numbered from 1 on screen."""
        label = labels.MSG_CC_LABEL.format(number=lane + 1)
        title = messages.MSG_CC_PROMPT.format(number=lane + 1)
        return NumberField(
            page=self._page, label=label, number=self.track().get_cc_numbers()[lane], start=midi.MIN_CC_NUMBER, shown=self.cc_text(lane),
            lowest=midi.MIN_CC_NUMBER, highest=midi.MAX_CC_NUMBER, title=title, set=functools.partial(self._set_cc_number, lane=lane),
            clear=functools.partial(self._set_cc_number, None, lane=lane), clear_what=marks.MSG_NONE_SHOWN,
        )

    def cc_text(self, lane):
        number = self.track().get_cc_numbers()[lane]
        if number is None:
            return marks.MSG_NONE_SHOWN
        return str(number)

    def groove_field(self):
        """Return the Groove field: the scene's or the song's by default, off to play straight, or one by name. A track plays in
        every scene, so what it takes from above is the song's groove, named, only while no scene sets one of its own."""
        song = self._document.song()
        inherited = marks.MSG_SCENE_OR_SONG_GROOVE_SHOWN
        cleared = legends.MSG_FROM_SCENE_OR_SONG_WHAT
        if all(scene.get_groove_choice() is None for scene in song.get_scenes()):
            inherited = marks.MSG_SONG_GROOVE_SHOWN.format(groove=song.get_groove_name())
            cleared = legends.MSG_FROM_SONG_WHAT
        return groove_choice_field(
            page=self._page, title=messages.MSG_TRACK_GROOVE_TITLE, choice=self.track().get_groove_choice(),
            inherited_option=marks.MSG_SCENE_OR_SONG_GROOVE_SHOWN, inherited_shown=inherited, choose=self._set_groove, clear_what=cleared,
        )

    def instrument_field(self):
        """Return the Instrument field: the instrument the track plays through in real time, chosen from the set's, or none."""
        return Field(
            label=labels.MSG_INSTRUMENT_LABEL, value=self._instrument_shown, adjust=None, enter=self.pick_instrument, enter_what=legends.What.CHOOSE,
            clear=functools.partial(self.set_instrument, None), clear_what=marks.MSG_NONE_SHOWN,
        )

    def pick_instrument(self):
        """Choose the instrument the track plays through in real time, from the set's of its role, or none: a drum track's are
        the percussion instruments, any other's the normal ones."""
        instruments = sorted_names(self._document.instruments_of_role(role_of_track(self.track())))
        current = self.track().get_instrument_name()
        self._page.pick(title=labels.MSG_INSTRUMENT_LABEL, values=[None, *instruments], shown=[marks.MSG_NONE_SHOWN, *instruments], current=current, then=self.set_instrument)

    def set_instrument(self, instrument):
        self._document.set_track_instrument(name=self._name, instrument=instrument)

    def default_velocity_field(self):
        """Return the Default velocity field: what a step with no velocity typed plays at on the track, shown as its instrument's
        until the track has its own."""
        track = self.track()
        song = self._document.song()
        above = song.default_velocity_of(track)
        if track.get_default_velocity() is not None:
            shown = None
        elif song.instrument_of(track) is not None:
            shown = marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=above)
        else:
            shown = above
        cleared = str(defaults.DEFAULT_VELOCITY)
        if song.instrument_of(track) is not None:
            cleared = legends.MSG_FROM_INSTRUMENT_WHAT
        return self._setting_field(label=labels.MSG_DEFAULT_VELOCITY_LABEL, name=TrackSetting.DEFAULT_VELOCITY, start=above, shown=shown, typed=above, clear_what=cleared)

    def velocity_change_field(self):
        """Return the Velocity field: the percentage of its written velocity every clip of the track plays, stacking with the
        instrument's, the scene's and the clip's, 100% until set."""
        percent = self.track().get_velocity_percent()
        shown = percentages.percent_shown(percentages.UNCHANGED if percent is None else percent)
        return self._setting_field(label=labels.MSG_VELOCITY_PERCENT_LABEL, name=TrackSetting.VELOCITY, shown=shown, start=percentages.UNCHANGED, clear_what=percentages.percent_shown(percentages.UNCHANGED))

    def accent_field(self):
        """Return the Accent field: what a step with its Accent on adds to its velocity on the track, on top of its instrument's accent."""
        accent = self.track().get_accent()
        shown = marks.MSG_ACCENT_SHOWN.format(accent=accent)
        return self._setting_field(label=labels.MSG_ACCENT_LABEL, name=TrackSetting.ACCENT, in_effect=accent, shown=shown, clear_what=marks.MSG_ACCENT_SHOWN.format(accent=defaults.DEFAULT_TRACK_ACCENT))

    def transpose_field(self, track):
        """Return the Transpose field, which a drum track only shows, since its notes are drums."""
        if track.is_drum():
            return Field(label=labels.MSG_TRANSPOSE_LABEL, value=_drum_transpose_shown)
        return NumberField(
            page=self._page, label=labels.MSG_TRANSPOSE_LABEL, number=track.get_transpose(), shown=self.transpose_text(), lowest=-limits.MAX_TRANSPOSE,
            highest=limits.MAX_TRANSPOSE, set=self._set_transpose, clear=functools.partial(self._set_transpose, defaults.DEFAULT_TRANSPOSE),
            clear_what=str(defaults.DEFAULT_TRANSPOSE),
        )

    def transpose_text(self):
        transpose = self.track().get_transpose()
        if not transpose:
            return str(defaults.DEFAULT_TRANSPOSE)
        return marks.MSG_SIGNED_NUMBER.format(number=transpose)

    def octave_fields(self, track):
        """Return the Lowest and Highest octave fields, each kept from crossing the other."""
        lowest = octave_field(page=self._page, label=labels.MSG_LOWEST_OCTAVE_LABEL, current=track.get_lowest_octave, highest=track.get_highest_octave,
                              lowest=_lowest_octave, default=limits.MIN_OCTAVE, set_octave=self._set_lowest_octave)
        highest = octave_field(page=self._page, label=labels.MSG_HIGHEST_OCTAVE_LABEL, current=track.get_highest_octave, highest=_highest_octave,
                               lowest=track.get_lowest_octave, default=limits.MAX_OCTAVE, set_octave=self._set_highest_octave)
        return [lowest, highest]

    def _setting_field(self, *, label, name, **given):
        """Return a field for a whole number that is a setting of the track, by the setting's file name."""
        return SettingNumberField(page=self._page, document=self._document, label=label, holder=self.track(), name=name, **given)

    def _instrument_shown(self):
        return self.track().get_instrument_name() or marks.MSG_NONE_SHOWN

    def _set_cc_number(self, number, *, lane):
        self._change(self.track().set_cc_number, lane=lane, number=number)

    def _set_groove(self, choice):
        song = self._document.song()
        self._change(self.track().set_groove_choice, choice=choice, song=song)

    def _set_transpose(self, transpose):
        self._change(self.track().set_transpose, transpose)

    def _set_drum(self, on):
        """Make the track a drum track or not, refused on the status line where its instrument would no longer fit."""
        instrument = self.track().get_instrument_name()
        wanted = InstrumentRole.PERCUSSION if on else InstrumentRole.NORMAL
        if instrument is not None and instrument in self._document.get_setlist().get_instrument_names():
            role = self._document.get_setlist().get_instrument(instrument).get_role()
            if role != wanted:
                self._page.refuse(errors.ERR_INSTRUMENT_DOES_NOT_FIT.format(instrument=instrument, role=labels.MSG_ROLE_NAMES[role].lower()))
                return
        self._change(self.track().set_drum, on)

    def _set_mute(self, on):
        self._change(self.track().set_mute, on)

    def _set_lowest_octave(self, octave):
        self._change(self.track().set_lowest_octave, octave)

    def _set_highest_octave(self, octave):
        self._change(self.track().set_highest_octave, octave)

    def _chain_names(self):
        return self.track().get_chain_names()

    def _set_chain_names(self, names):
        song = self._document.song()
        self._change(self.track().set_chain_names, names=names, song=song)

    def _change(self, setter, *arguments, **named):
        """Change the track through one of its setters, as one edit of the set."""
        self._document.change_set(setter, *arguments, **named)


def role_of_track(track):
    """Return the role of the instruments a track may play: percussion for a drum track, normal for any other."""
    if track.is_drum():
        return InstrumentRole.PERCUSSION
    return InstrumentRole.NORMAL


def _drum_transpose_shown():
    return marks.MSG_DRUM_TRACK_SHOWN


def _lowest_octave():
    return limits.MIN_OCTAVE


def _highest_octave():
    return limits.MAX_OCTAVE
