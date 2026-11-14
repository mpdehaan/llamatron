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

"""The Track editor page: one track's settings, which apply to every clip on it."""

from rich.text import Text

from llamatron.composition.defaults import DEFAULT_TRANSPOSE
from llamatron.composition.file_format import EuclidPart, CC_ROWS, REGISTER_NAMES, Section
from llamatron.composition.limits import MAX_OCTAVE, MAX_TRANSPOSE, MIN_OCTAVE
from llamatron.tui.screens.octave_field import octave_field
from llamatron.tui.screens.strum_fields import strum_section
from llamatron.tui.screens.euclid_fields import euclid_section, pick_rhythm
from llamatron.music.midi import MAX_CC_NUMBER, MIN_CC_NUMBER
from llamatron.tui.drawing import Style
from llamatron.strings.help import HELP_TRACK_EDITOR
from llamatron.tui.screens.field import ChoiceField, Field, NameField, NumberField, Toggle
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.groove_choice import groove_choice_field
from llamatron.strings.labels import (
    MSG_EUCLID_FIELD_LABELS,
    MSG_CC_REGISTER_LABEL, MSG_VELOCITY_REGISTER_LABEL,
    MSG_HIGHEST_OCTAVE_LABEL, MSG_LOWEST_OCTAVE_LABEL, Crumb, MSG_CC_LABEL, MSG_TRACK_CRUMB, MSG_DRUM_LABEL, MSG_MUTE_LABEL,
    MSG_INSTRUMENT_LABEL, MSG_TRANSPOSE_LABEL,
)
from llamatron.strings.legends import MSG_NO_INSTRUMENT_WHAT, MSG_NO_CC_WHAT, MSG_NO_TRANSPOSE_WHAT, MSG_UNBIND_WHAT, MSG_USE_SCENE_GROOVE_WHAT, What
from llamatron.strings.marks import (
    MSG_DRUM_TRACK_SHOWN, MSG_NONE_SHOWN, MSG_SCENE_OR_SONG_GROOVE_SHOWN, MSG_SIGNED_NUMBER,
)
from llamatron.tui.screens.shows_named_item import ShowsNamedItem
from llamatron.strings.messages import MSG_RENAME_TRACK_PROMPT, MSG_CC_PROMPT, MSG_TRACK_GROOVE_TITLE, MSG_TRANSPOSE_NOTE
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.text import sorted_names
from llamatron.tui.screens.chains_field import chains_field
from llamatron.tui import keybindings

# The place of (none) in the instrument picker, before the names.
NO_INSTRUMENT_PLACE = 0


class TrackEditor(ShowsNamedItem, FieldPage):
    """One track's settings, which apply to every clip on it."""

    KEYS = keybindings.TrackEditor

    HELP = HELP_TRACK_EDITOR
    SECTION = Section.TRACKS
    CRUMBS_BEFORE = (Crumb.ARRANGE,)
    ITEM_CRUMB = MSG_TRACK_CRUMB
    RENAME_PROMPT = MSG_RENAME_TRACK_PROMPT

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def track(self):
        return self.document().song().get_track(self.item)

    def numbers(self):
        return self.track().get_cc_numbers()

    def set_cc(self, *, lane, number):
        self.document().set_track_cc_number(name=self.item, lane=lane, number=number)

    def set_transpose(self, transpose):
        self.document().set_track_transpose(name=self.item, transpose=transpose)

    def transpose_text(self):
        transpose = self.track().get_transpose()
        return MSG_SIGNED_NUMBER.format(number=transpose) if transpose else str(DEFAULT_TRANSPOSE)

    def cc_text(self, lane):
        number = self.numbers()[lane]
        return MSG_NONE_SHOWN if number is None else str(number)

    def cc_field(self, lane):
        """Return the field for one of the four CC lanes, numbered from 1 on screen."""
        label = MSG_CC_LABEL.format(number=lane + 1)
        return NumberField(
            page=self, label=label, number=self.numbers()[lane], start=MIN_CC_NUMBER, shown=self.cc_text(lane), lowest=MIN_CC_NUMBER, highest=MAX_CC_NUMBER,
            title=MSG_CC_PROMPT.format(number=lane + 1), set=lambda number: self.set_cc(lane=lane, number=number),
            clear=lambda: self.set_cc(lane=lane, number=None), clear_what=MSG_NO_CC_WHAT,
        )

    def groove_field(self):
        """Return the Groove field: the scene's or the song's by default, off to play straight, or one by name."""
        return groove_choice_field(
            page=self, title=MSG_TRACK_GROOVE_TITLE, choice=self.track().get_groove_choice(),
            inherited_option=MSG_SCENE_OR_SONG_GROOVE_SHOWN, inherited_shown=MSG_SCENE_OR_SONG_GROOVE_SHOWN,
            choose=lambda choice: self.document().set_track_groove(name=self.item, choice=choice), clear_what=MSG_USE_SCENE_GROOVE_WHAT,
        )

    def pick_instrument(self):
        """Choose the instrument the track plays through in real time, from the set's, or none."""
        instruments = sorted_names(self.document().setlist().get_instrument_names())
        options = [MSG_NONE_SHOWN, *instruments]
        current = self.track().get_instrument_name()

        def chosen(place):
            self.set_instrument(None if place == NO_INSTRUMENT_PLACE else instruments[place - 1])
        self.ask(dialog=ChoiceDialog(title=MSG_INSTRUMENT_LABEL, options=options, current=options.index(current) if current in options else NO_INSTRUMENT_PLACE), then=chosen)

    def set_instrument(self, instrument):
        self.document().set_track_instrument(name=self.item, instrument=instrument)

    def register_field(self, *, label, current, bind):
        """Return a field binding a CC lane or the velocity to a register, (none) first and then AX to DX, the user's design of 2026-11-11."""
        choices = [MSG_NONE_SHOWN, *REGISTER_NAMES]
        return ChoiceField(
            page=self, label=label, choices=choices, current=current or MSG_NONE_SHOWN,
            set=lambda choice: bind(None if choice == MSG_NONE_SHOWN else choice), clear=lambda: bind(None), clear_what=MSG_UNBIND_WHAT,
        )

    def instrument_field(self):
        return Field(label=MSG_INSTRUMENT_LABEL, value=lambda: self.track().get_instrument_name() or MSG_NONE_SHOWN, adjust=None, enter=self.pick_instrument, enter_what=What.CHOOSE,
                     clear=lambda: self.set_instrument(None), clear_what=MSG_NO_INSTRUMENT_WHAT)

    def fields(self):
        track = self.track()
        drum = track.is_drum()
        result = [
            NameField(value=lambda: self.item, rename=self.rename),
            Toggle(label=MSG_DRUM_LABEL, on=drum, set=lambda on: self.document().set_track_drum(name=self.item, drum=on)),
            Toggle(label=MSG_MUTE_LABEL, on=track.is_muted(), set=lambda on: self.document().set_track_mute(name=self.item, muted=on)),
            self.groove_field(),
        ]
        if drum:
            result.append(Field(label=MSG_TRANSPOSE_LABEL, value=lambda: MSG_DRUM_TRACK_SHOWN))
        else:
            result.append(NumberField(
                page=self, label=MSG_TRANSPOSE_LABEL, number=track.get_transpose(), shown=self.transpose_text(), lowest=-MAX_TRANSPOSE, highest=MAX_TRANSPOSE,
                set=self.set_transpose, clear=lambda: self.set_transpose(DEFAULT_TRANSPOSE), clear_what=MSG_NO_TRANSPOSE_WHAT,
            ))
        result += [
            octave_field(page=self, label=MSG_LOWEST_OCTAVE_LABEL, current=track.get_lowest_octave, highest=track.get_highest_octave, lowest=lambda: MIN_OCTAVE, default=MIN_OCTAVE,
                              set_octave=lambda octave: self.document().set_track_lowest_octave(name=self.item, octave=octave)),
            octave_field(page=self, label=MSG_HIGHEST_OCTAVE_LABEL, current=track.get_highest_octave, highest=lambda: MAX_OCTAVE, lowest=track.get_lowest_octave, default=MAX_OCTAVE,
                              set_octave=lambda octave: self.document().set_track_highest_octave(name=self.item, octave=octave)),
        ]
        result += [self.cc_field(lane) for lane in range(len(CC_ROWS))]
        registers = track.get_cc_registers()
        result += [
            self.register_field(label=MSG_CC_REGISTER_LABEL.format(number=lane + 1), current=registers[lane],
                                bind=lambda register, lane=lane: self.document().set_track_cc_register(name=self.item, lane=lane, register=register))
            for lane in range(len(CC_ROWS))
        ]
        result.append(self.register_field(label=MSG_VELOCITY_REGISTER_LABEL, current=track.get_velocity_register(),
                                          bind=lambda register: self.document().set_track_velocity_register(name=self.item, register=register)))
        result.append(chains_field(page=self, names=lambda: self.track().get_chain_names(), store=lambda names: self.document().set_track_chains(name=self.item, names=names)))
        result.append(self.instrument_field())
        result += euclid_section(page=self, value=track.get_euclid_setting, store=lambda part, value: self.store_euclid(part=part, value=value))
        result += strum_section(
            page=self, value=track.get_strum_setting, first=MSG_NONE_SHOWN,
            store=lambda part, value: self.document().set_track_strum_setting(name=self.item, part=part, value=value),
        )
        return result

    def store_euclid(self, *, part, value):
        self.document().set_track_euclid_setting(name=self.item, part=part, value=value)

    def page_keys(self):
        if self.field().label == MSG_EUCLID_FIELD_LABELS[EuclidPart.HITS]:
            return [self.bind(self.KEYS.PICK_RHYTHM, action=lambda: pick_rhythm(page=self, store=lambda part, value: self.store_euclid(part=part, value=value)))]
        return []

    def notes(self, width):
        return [Text(MSG_TRANSPOSE_NOTE, style=Style.DIM)]
