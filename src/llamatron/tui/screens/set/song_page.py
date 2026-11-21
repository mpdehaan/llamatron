# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Song page: one song's name, tempo, scale and seed, reached from the Songs page, which makes it current first."""

from llamatron.composition import defaults, file_format, genres, limits
from llamatron.composition.file_format import Section
from llamatron.composition.genres import subgenres_of, variants_of
from llamatron.strings import errors, help as help_text, labels, legends, marks, messages
from llamatron.tui import keybindings, themes
from llamatron.tui.screens.set.visualizer_fields import visualizer_field
from llamatron.tui.screens.shared.everywhere import export
from llamatron.tui.screens.shared.field import ChoiceField, Field, NameField, NumberField
from llamatron.tui.screens.shared.field_page import FieldPage
from llamatron.tui.screens.shared.shared import ask_time_signature, stepped
from llamatron.tui.text import sorted_names, tempo_text


class SongPage(FieldPage):
    """The current song's own settings."""

    THEME = themes.SONGS

    KEYS = keybindings.SongPage

    HELP = help_text.HELP_SONG_PAGE

    def crumb_trail(self):
        # The current song can be renamed here and by an undo, so the crumb is read each time.
        return (labels.Crumb.SONGS, self.document().get_current_song_name())

    def caption(self):
        return labels.MSG_EDITING_CAPTION.format(what=labels.MSG_CAPTION_WORDS[Section.SONGS].upper(), name=self.document().get_current_song_name())

    def duration(self):
        return self.document().lengths().song_seconds()

    def song(self):
        return self.document().song()

    def fields(self):
        document = self.document()
        song = self.song()
        return [
            NameField(value=document.get_current_song_name, rename=self.rename),
            NumberField(
                page=self, label=labels.MSG_TEMPO_LABEL, number=int(song.get_tempo()), shown=marks.MSG_TEMPO_SHOWN.format(tempo=tempo_text(song.get_tempo())),
                typed=tempo_text(song.get_tempo()), lowest=limits.MIN_TEMPO, highest=limits.MAX_TEMPO, set=lambda tempo: document.change(document.song().set_tempo, tempo),
            ),
            Field(label=labels.MSG_TIME_SIGNATURE_LABEL, value=lambda: song.get_time_signature().to_text(), adjust=self.step_time_signature, enter=self.ask_time_signature),
            Field(label=labels.MSG_ENTRY_SIZE_LABEL, value=lambda: self.entry_size_text() or marks.MSG_ONE_STEP_SHOWN, adjust=self.step_entry_size, enter=self.pick_entry_size, enter_what=legends.What.CHOOSE,
                  clear=lambda: document.change(document.song().set_entry_size, None), clear_what=legends.MSG_ONE_STEP_WHAT),
            Field(label=labels.MSG_SCALE_LABEL, value=lambda: song.get_scale_name() or marks.MSG_NONE_SHOWN, adjust=self.step_scale, enter=self.pick_scale, enter_what=legends.What.CHOOSE,
                  clear=lambda: document.change(document.song().set_scale_name, None), clear_what=messages.MSG_NO_SCALE),
            Field(label=labels.MSG_GROOVE_LABEL, value=song.get_groove_name, adjust=self.step_groove, enter=self.pick_groove, enter_what=legends.What.CHOOSE),
            self.style_field(label=labels.MSG_GENRE_LABEL, choices=genres.GENRES, current=song.get_genre(), set_choice=lambda genre: document.change(document.song().set_genre, genre)),
            self.style_field(label=labels.MSG_SUBGENRE_LABEL, choices=subgenres_of(song.get_genre()), current=song.get_subgenre(), set_choice=lambda subgenre: document.change(document.song().set_subgenre, subgenre)),
            self.style_field(
                label=labels.MSG_VARIANT_LABEL, choices=variants_of(genre=song.get_genre(), subgenre=song.get_subgenre()), current=song.get_variant(), set_choice=lambda variant: document.change(document.song().set_variant, variant),
            ),
            ChoiceField(
                page=self, label=labels.MSG_LIVE_RESPONSIVENESS_LABEL, choices=file_format.LIVE_RESPONSIVENESSES, current=song.get_live_responsiveness(),
                names=[labels.MSG_LIVE_RESPONSIVENESS_NAMES[choice] for choice in file_format.LIVE_RESPONSIVENESSES], shown=labels.MSG_LIVE_RESPONSIVENESS_NAMES[song.get_live_responsiveness()],
                set=lambda value: document.change(document.song().set_live_responsiveness, value),
            ),
            Field(label=labels.MSG_PREVIEW_INSTRUMENT_LABEL, value=lambda: song.get_preview_instrument_name() or labels.MSG_PREVIEW_INSTRUMENT_UNSET, adjust=self.step_preview_instrument,
                  enter=self.pick_preview_instrument, enter_what=legends.What.CHOOSE, clear=lambda: document.change(document.song().set_preview_instrument_name, None), clear_what=labels.MSG_PREVIEW_INSTRUMENT_UNSET),
            visualizer_field(page=self, current=song.get_visualizer(), set_name=lambda name: document.change(document.song().set_visualizer, name), first=labels.MSG_SETS_VISUALIZER_CHOICE),
            self.button(binding=self.KEYS.EXPORT, label=labels.PageName.EXPORT, action=lambda: export(self)),
        ]

    def rename(self):
        """Rename the current song, which the Songs page's N does too, and put the new name in the crumbs."""
        document = self.document()
        name = document.get_current_song_name()

        def renamed(new):
            document.rename_named(section=Section.SONGS, old=name, new=new)
            self.crumbs = (labels.Crumb.SONGS, new)
        self.ask_name(title=messages.MSG_RENAME_SONG_PROMPT, value=name, taken=document.song_names(), then=renamed)

    def step_time_signature(self, offset):
        """Move to the next or previous common time signature, from 4/4 if the song's isn't in the list."""
        current = self.song().get_time_signature().to_text()
        place = file_format.TIME_SIGNATURE_CHOICES.index(current if current in file_format.TIME_SIGNATURE_CHOICES else defaults.DEFAULT_TIME_SIGNATURE)
        self.document().change(self.document().song().set_time_signature, file_format.TIME_SIGNATURE_CHOICES[max(min(place + offset, len(file_format.TIME_SIGNATURE_CHOICES) - 1), 0)])

    def ask_time_signature(self):
        current = self.song().get_time_signature().to_text()
        ask_time_signature(page=self, title=messages.MSG_SONG_TIME_SIGNATURE_PROMPT, current=current, then=lambda text: self.document().change(self.document().song().set_time_signature, text), blank_allowed=False)

    def entry_size_text(self):
        """Return the song's entry size as text, like 1/8, or None for one step."""
        entry_size = self.song().get_written_entry_size()
        return None if entry_size is None else str(entry_size)

    def step_entry_size(self, offset):
        """Move to the next or previous step size, with one step before the shortest, and from one step if the song's size isn't in the list."""
        choices = [None, *file_format.STEP_SIZE_CHOICES]
        current = self.entry_size_text()
        place = choices.index(current) if current in choices else 0
        self.document().change(self.document().song().set_entry_size, choices[max(min(place + offset, len(choices) - 1), 0)])

    def pick_entry_size(self):
        choices = [None, *file_format.STEP_SIZE_CHOICES]
        options = [marks.MSG_ONE_STEP_SHOWN, *file_format.STEP_SIZE_CHOICES]
        self.pick(title=labels.MSG_ENTRY_SIZE_LABEL, values=choices, shown=options, current=self.entry_size_text(), then=lambda size: self.document().change(self.document().song().set_entry_size, size))

    def step_scale(self, offset):
        """Move to the next or previous of the set's scales, with no scale before the first."""
        names = [None, *sorted_names(self.song().get_scale_names())]
        place = names.index(self.song().get_scale_name())
        self.document().change(self.document().song().set_scale_name, names[max(min(place + offset, len(names) - 1), 0)])

    def preview_instruments(self):
        """Return what the Preview instrument field chooses among: none, which is the pattern's own track, then the set's instruments by name."""
        return [None, *sorted_names(self.document().get_setlist().get_instrument_names())]

    def step_preview_instrument(self, offset):
        """Move to the next or previous instrument, stopping at both ends."""
        names = self.preview_instruments()
        place = names.index(self.song().get_preview_instrument_name())
        self.document().change(self.document().song().set_preview_instrument_name, names[max(min(place + offset, len(names) - 1), 0)])

    def pick_preview_instrument(self):
        names = self.preview_instruments()
        options = [labels.MSG_PREVIEW_INSTRUMENT_UNSET, *names[1:]]
        self.pick(
            title=messages.MSG_PREVIEW_INSTRUMENT_TITLE, values=names, shown=options, current=self.song().get_preview_instrument_name(),
            then=lambda name: self.document().change(self.document().song().set_preview_instrument_name, name),
        )

    def style_field(self, *, label, choices, current, set_choice):
        """Return a field for the song's genre, its subgenre or its variant: one of the choices, or undefined, which is all a field with no choices offers."""
        offered = [marks.MSG_UNDEFINED_SHOWN, *choices]
        return ChoiceField(
            page=self, label=label, choices=offered, current=current or marks.MSG_UNDEFINED_SHOWN, set=lambda choice: set_choice(None if choice == marks.MSG_UNDEFINED_SHOWN else choice),
            clear=lambda: set_choice(None), clear_what=legends.What.CLEAR,
        )

    def step_groove(self, offset):
        """Move to the next or previous groove, in the order the picker shows them."""
        names = sorted_names(self.song().get_groove_names())
        self.document().change(self.document().song().set_groove_name, stepped(values=names, current=self.song().get_groove_name(), offset=offset))

    def pick_groove(self):
        names = sorted_names(self.song().get_groove_names())
        self.pick(title=messages.MSG_SONG_GROOVE_TITLE, values=names, current=self.song().get_groove_name(), then=lambda name: self.document().change(self.document().song().set_groove_name, name))

    def pick_scale(self):
        scales = sorted_names(self.song().get_scale_names())
        if not scales:
            self.refuse(errors.ERR_ADD_A_SCALE_FIRST)
            return
        self.pick(title=messages.MSG_SONG_SCALE_TITLE, values=scales, current=self.song().get_scale_name(), then=lambda name: self.document().change(self.document().song().set_scale_name, name))
