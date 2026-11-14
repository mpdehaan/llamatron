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
"""The Song page: one song's name, tempo, scale and seed, reached from the Songs page, which makes it current first."""

from llamatron.composition.defaults import DEFAULT_TIME_SIGNATURE
from llamatron.composition.file_format import LIVE_RESPONSIVENESSES, STEP_SIZE_CHOICES, TIME_SIGNATURE_CHOICES, Section
from llamatron.composition.limits import MAX_TEMPO, MIN_TEMPO
from llamatron.tui.dialogs.choice_dialog import ChoiceDialog
from llamatron.tui.text import sorted_names, tempo_text
from llamatron.strings.help import HELP_SONG_PAGE
from llamatron.tui.screens.everywhere import export
from llamatron.tui.screens.field import ChoiceField, Field, NameField, NumberField
from llamatron.tui.screens.visualizer_fields import visualizer_field
from llamatron.tui.screens.field_page import FieldPage
from llamatron.tui.screens.shared import NO_SEED, ask_time_signature, stepped
from llamatron.strings.errors import ERR_ADD_A_SCALE_FIRST
from llamatron.strings.labels import MSG_CAPTION_WORDS, MSG_EDITING_CAPTION
from llamatron.strings.labels import (
    MSG_GENRE_LABEL, MSG_LIVE_RESPONSIVENESS_LABEL, MSG_LIVE_RESPONSIVENESS_NAMES, MSG_SETS_VISUALIZER_CHOICE,
    MSG_ENTRY_SIZE_LABEL, Crumb, MSG_GROOVE_LABEL, MSG_SCALE_LABEL, MSG_SEED_LABEL, MSG_TEMPO_LABEL,
    MSG_TIME_SIGNATURE_LABEL, PageName,
)
from llamatron.strings.legends import MSG_ONE_STEP_WHAT, What
from llamatron.strings.marks import MSG_ONE_STEP_SHOWN, MSG_NONE_SHOWN, MSG_TEMPO_SHOWN
from llamatron.strings.messages import (
    MSG_NO_SCALE, MSG_NO_SEED, MSG_RENAME_SONG_PROMPT, MSG_SONG_GROOVE_TITLE, MSG_SONG_SCALE_TITLE, MSG_SONG_TIME_SIGNATURE_PROMPT,
)
from llamatron.tui import themes
from llamatron.tui import keybindings


class SongPage(FieldPage):
    """The current song's own settings."""

    THEME = themes.SONGS

    KEYS = keybindings.SongPage

    HELP = HELP_SONG_PAGE

    def crumb_trail(self):
        # The current song can be renamed here and by an undo, so the crumb is read each time.
        return (Crumb.SONGS, self.document().current_song_name())

    def caption(self):
        return MSG_EDITING_CAPTION.format(what=MSG_CAPTION_WORDS[Section.SONGS].upper(), name=self.document().current_song_name())

    def duration(self):
        return self.document().lengths().song_seconds()

    def song(self):
        return self.document().song()

    def fields(self):
        document = self.document()
        song = self.song()
        return [
            NameField(value=document.current_song_name, rename=self.rename),
            NumberField(
                page=self, label=MSG_TEMPO_LABEL, number=int(song.get_tempo()), shown=MSG_TEMPO_SHOWN.format(tempo=tempo_text(song.get_tempo())),
                typed=tempo_text(song.get_tempo()), lowest=MIN_TEMPO, highest=MAX_TEMPO, set=document.set_tempo,
            ),
            Field(label=MSG_TIME_SIGNATURE_LABEL, value=lambda: song.get_time_signature().to_text(), adjust=self.step_time_signature, enter=self.ask_time_signature),
            Field(label=MSG_ENTRY_SIZE_LABEL, value=lambda: self.entry_size_text() or MSG_ONE_STEP_SHOWN, adjust=self.step_entry_size, enter=self.pick_entry_size, enter_what=What.CHOOSE,
                  clear=lambda: document.set_entry_size(None), clear_what=MSG_ONE_STEP_WHAT),
            Field(label=MSG_SCALE_LABEL, value=lambda: song.get_scale_name() or MSG_NONE_SHOWN, adjust=self.step_scale, enter=self.pick_scale, enter_what=What.CHOOSE,
                  clear=lambda: document.set_scale_name(None), clear_what=MSG_NO_SCALE),
            NumberField(
                page=self, label=MSG_SEED_LABEL, number=song.get_seed(), start=NO_SEED, shown=MSG_NONE_SHOWN if song.get_seed() is None else None,
                set=document.set_seed, clear=lambda: document.set_seed(None), clear_what=MSG_NO_SEED,
            ),
            Field(label=MSG_GROOVE_LABEL, value=song.get_groove_name, adjust=self.step_groove, enter=self.pick_groove, enter_what=What.CHOOSE),
            self.text_field(label=MSG_GENRE_LABEL, current=song.get_genre, set_text=document.set_genre),
            ChoiceField(
                page=self, label=MSG_LIVE_RESPONSIVENESS_LABEL, choices=LIVE_RESPONSIVENESSES, current=song.get_live_responsiveness(),
                names=[MSG_LIVE_RESPONSIVENESS_NAMES[choice] for choice in LIVE_RESPONSIVENESSES], shown=MSG_LIVE_RESPONSIVENESS_NAMES[song.get_live_responsiveness()],
                set=document.set_live_responsiveness,
            ),
            visualizer_field(page=self, current=song.get_visualizer(), set_name=document.set_song_visualizer, first=MSG_SETS_VISUALIZER_CHOICE),
            self.button(binding=self.KEYS.EXPORT, label=PageName.EXPORT, action=lambda: export(self)),
        ]

    def rename(self):
        """Rename the current song, which the Songs page's N does too, and put the new name in the crumbs."""
        document = self.document()
        name = document.current_song_name()

        def renamed(new):
            document.rename_named(section=Section.SONGS, old=name, new=new)
            self.crumbs = (Crumb.SONGS, new)
        self.ask_name(title=MSG_RENAME_SONG_PROMPT, value=name, taken=document.song_names(), then=renamed)

    def step_time_signature(self, offset):
        """Move to the next or previous common time signature, from 4/4 if the song's isn't in the list."""
        current = self.song().get_time_signature().to_text()
        place = TIME_SIGNATURE_CHOICES.index(current if current in TIME_SIGNATURE_CHOICES else DEFAULT_TIME_SIGNATURE)
        self.document().set_time_signature(TIME_SIGNATURE_CHOICES[max(min(place + offset, len(TIME_SIGNATURE_CHOICES) - 1), 0)])

    def ask_time_signature(self):
        current = self.song().get_time_signature().to_text()
        ask_time_signature(page=self, title=MSG_SONG_TIME_SIGNATURE_PROMPT, current=current, then=self.document().set_time_signature, blank_allowed=False)

    def entry_size_text(self):
        """Return the song's entry size as text, like 1/8, or None for one step."""
        entry_size = self.song().get_written_entry_size()
        return None if entry_size is None else str(entry_size)

    def step_entry_size(self, offset):
        """Move to the next or previous step size, with one step before the shortest, and from one step if the song's size isn't in the list."""
        choices = [None, *STEP_SIZE_CHOICES]
        current = self.entry_size_text()
        place = choices.index(current) if current in choices else 0
        self.document().set_entry_size(choices[max(min(place + offset, len(choices) - 1), 0)])

    def pick_entry_size(self):
        choices = [None, *STEP_SIZE_CHOICES]
        current = self.entry_size_text()
        options = [MSG_ONE_STEP_SHOWN, *STEP_SIZE_CHOICES]
        place = choices.index(current) if current in choices else 0
        self.ask(dialog=ChoiceDialog(title=MSG_ENTRY_SIZE_LABEL, options=options, current=place), then=lambda chosen: self.document().set_entry_size(choices[chosen]))

    def step_scale(self, offset):
        """Move to the next or previous of the set's scales, with no scale before the first."""
        names = [None, *sorted_names(self.song().get_scale_names())]
        place = names.index(self.song().get_scale_name())
        self.document().set_scale_name(names[max(min(place + offset, len(names) - 1), 0)])

    def step_groove(self, offset):
        """Move to the next or previous groove, in the order the picker shows them."""
        names = sorted_names(self.song().get_groove_names())
        self.document().set_groove_name(stepped(values=names, current=self.song().get_groove_name(), offset=offset))

    def pick_groove(self):
        names = sorted_names(self.song().get_groove_names())
        self.ask(dialog=ChoiceDialog(title=MSG_SONG_GROOVE_TITLE, options=names, current=names.index(self.song().get_groove_name())), then=lambda chosen: self.document().set_groove_name(names[chosen]))

    def pick_scale(self):
        scales = sorted_names(self.song().get_scale_names())
        if not scales:
            self.refuse(ERR_ADD_A_SCALE_FIRST)
            return
        current = self.song().get_scale_name()
        place = scales.index(current) if current in scales else 0
        self.ask(dialog=ChoiceDialog(title=MSG_SONG_SCALE_TITLE, options=scales, current=place), then=lambda chosen: self.document().set_scale_name(scales[chosen]))
