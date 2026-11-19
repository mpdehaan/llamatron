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

"""The musician's editor: the instrument, the tracks the chords and the tune are read from, the player's touch, and a heading for each kind of section the song has."""

from llamatron.composition import file_format
from llamatron.composition.file_format import GeneratorKind, Section
from llamatron.composition import generator_settings
from llamatron.composition.generator_settings import MusicianSetting
from llamatron.generators import musician
from llamatron.strings import help as help_text, labels, legends, marks, messages
from llamatron.tui import keybindings
from llamatron.tui.screens.shared.field import ChoiceField, NameField, NumberField, Toggle, gauge_shown
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shows_named_item import ShowsNamedItem
from llamatron.tui.text import sorted_names


class MusicianEditor(ShowsNamedItem, FieldPage):

    KEYS = keybindings.MusicianEditor
    HELP = help_text.HELP_MUSICIAN_EDITOR
    SECTION = Section.MUSICIANS
    CRUMBS_BEFORE = (labels.Crumb.GENERATORS,)
    RENAME_PROMPT = messages.MSG_RENAME_GENERATOR_PROMPT.format(label=labels.MSG_MUSICIAN_LABEL)

    def __init__(self, *, holder, name):
        super().__init__(holder)
        self.show_item(name)

    def musician(self):
        return self.document().song().get_generator_settings(kind=GeneratorKind.MUSICIAN, name=self.item)

    def store(self, *, setting, value):
        """Keep a setting, left out of the file where it is what a musician does unasked."""
        self.document().set_generator_setting(section=Section.MUSICIANS, name=self.item, setting=setting, value=None if value == generator_settings.MUSICIAN_DEFAULTS.get(setting) else value)

    def store_section(self, *, section, name, value):
        """Keep what a kind of section has of its own, left out where it is what a section does unasked."""
        self.document().set_musician_section(name=self.item, section=section, setting=name, value=None if value == generator_settings.MUSICIAN_SECTION_DEFAULTS[name] else value)

    def tracks(self, named):
        """Return the tracks a musician can read: the current song's, sorted, and the one named among them even when the song has no such track, so that it is seen and kept."""
        names = set(self.document().song().get_track_names())
        if named is not None:
            names.add(named)
        return sorted_names(names)

    def track_field(self, *, label, setting, named):
        return ChoiceField(
            page=self, label=label, choices=[marks.MSG_NONE_SHOWN, *self.tracks(named)], current=named or marks.MSG_NONE_SHOWN,
            set=lambda choice: self.store(setting=setting, value=None if choice == marks.MSG_NONE_SHOWN else choice), clear=lambda: self.store(setting=setting, value=None),
            clear_what=legends.MSG_NO_TRACK_WHAT,
        )

    def choice(self, *, label, setting, choices):
        """Return a field that chooses one of a setting's values from a list, in the list's own order."""
        return ChoiceField(page=self, label=label, choices=list(choices), current=self.musician().get_own(setting), set=lambda chosen: self.store(setting=setting, value=chosen))

    def habit(self, *, label, setting, choices):
        """Return a field for what the instrument decides until the musician is told otherwise: left to the instrument, the field shows the instrument's way and says so, and the list's first choice leaves it to the instrument again."""
        own = self.musician()
        offered = [labels.MSG_MUSICIAN_INSTRUMENT_CHOICE, *choices]
        left_to_instrument = own.follows_instrument(setting)
        usual = own.get_own(setting)
        return ChoiceField(
            page=self, label=label, choices=offered, current=labels.MSG_MUSICIAN_INSTRUMENT_CHOICE if left_to_instrument else usual,
            shown=marks.MSG_FROM_INSTRUMENT_SHOWN.format(value=usual) if left_to_instrument else usual,
            set=lambda chosen: self.store(setting=setting, value=None if chosen == labels.MSG_MUSICIAN_INSTRUMENT_CHOICE else chosen), clear=lambda: self.store(setting=setting, value=None),
        )

    def gauge(self, *, label, setting, lowest, highest):
        """Return a number stepped or typed and drawn as a horizontal gauge, which is empty at the lowest."""
        number = self.musician().get_own(setting)
        return NumberField(page=self, label=label, number=number, shown=gauge_shown(place=number, lowest=lowest + 1, highest=highest), lowest=lowest, highest=highest,
                           set=lambda chosen: self.store(setting=setting, value=chosen))

    def sections(self):
        """Return the kinds of section the musician can be told about: those the song's scenes are, and those the musician already has settings for, in the order kinds of section are listed."""
        used = {scene.get_section() for scene in self.document().song().get_scenes()}
        return [kind for kind in file_format.SECTION_KINDS if kind in used or self.section_is_set(kind)]

    def section_is_set(self, section):
        own = self.musician()
        return any(own.get_section_own(section=section, name=name) is not None for name in generator_settings.MUSICIAN_SECTION_DEFAULTS)

    def section_fields(self, section):
        own = self.musician()
        plays = own.get_for(section=section, name=musician.PLAYS)
        fields = [
            self.heading(label=labels.MSG_MUSICIAN_SECTION_HEADING.format(section=section), is_set=lambda: self.section_is_set(section)),
            Toggle(label=labels.MSG_MUSICIAN_PLAYS_LABEL, on=plays, set=lambda on: self.store_section(section=section, name=musician.PLAYS, value=on)),
        ]
        if plays:
            fields.append(ChoiceField(page=self, label=labels.MSG_MUSICIAN_PLAYED_LABEL, choices=list(musician.FORMS), current=own.get_for(section=section, name=musician.PLAYED),
                                      set=lambda chosen: self.store_section(section=section, name=musician.PLAYED, value=chosen)))
        return fields

    def fields(self):
        own = self.musician()
        pitched = own.musician_class().LOWEST is not None
        fields = [
            NameField(value=lambda: self.item, rename=self.rename),
            self.choice(label=labels.MSG_MUSICIAN_INSTRUMENT_LABEL, setting=MusicianSetting.INSTRUMENT, choices=musician.INSTRUMENTS),
            *([self.track_field(label=labels.MSG_CHORDS_FROM_LABEL, setting=MusicianSetting.CHORDS_FROM, named=own.get_chords_from())] if pitched else []),
            self.track_field(label=labels.MSG_TUNE_FROM_LABEL, setting=MusicianSetting.TUNE_FROM, named=own.get_tune_from()),
            self.choice(label=labels.MSG_MUSICIAN_ACTIVITY_LABEL, setting=MusicianSetting.ACTIVITY, choices=musician.ACTIVITIES),
            self.gauge(label=labels.MSG_MUSICIAN_LOUDNESS_LABEL, setting=MusicianSetting.LOUDNESS, lowest=musician.QUIETEST, highest=musician.LOUDEST),
            self.gauge(label=labels.MSG_MUSICIAN_LOOSENESS_LABEL, setting=MusicianSetting.LOOSENESS, lowest=musician.TIGHT, highest=musician.LOOSEST),
            # Giving way is to the melody's track, so the field shows only once a track is named.
            *([self.habit(label=labels.MSG_MUSICIAN_GIVES_WAY_LABEL, setting=MusicianSetting.GIVES_WAY, choices=musician.GIVES_WAY)] if own.get_tune_from() is not None else []),
            self.choice(label=labels.MSG_MUSICIAN_ACCENTS_LABEL, setting=MusicianSetting.ACCENTS, choices=musician.ACCENTS),
            self.habit(label=labels.MSG_MUSICIAN_NOTES_LABEL, setting=MusicianSetting.NOTES, choices=musician.NOTE_LENGTHS),
            *([self.choice(label=labels.MSG_MUSICIAN_RANGE_LABEL, setting=MusicianSetting.RANGE, choices=musician.RANGES)] if pitched else []),
        ]
        for section in self.sections():
            fields += self.section_fields(section)
        return fields
