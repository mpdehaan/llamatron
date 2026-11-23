# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later
"""The Song page as a presenter: one song's settings, its name, tempo, time signature, entry size, scale, groove, style, how soon
an edit is heard, the instrument a pattern is heard through and its visualizer, each a field, then the Export button."""

import functools

from llamatron.interface.forms.nodes import ChoiceField, Field, NameField, NumberField, stepped
from llamatron.interface.forms.text import sorted_names, tempo_text
from llamatron.interface.pages.asking import ask_time_signature
from llamatron.interface.pages.visualizer_fields import visualizer_field
from llamatron.model.schema import defaults, file_format, genres, limits
from llamatron.model.schema.genres import subgenres_of, variants_of
from llamatron.user_strings import errors, labels, legends, marks, messages


class SongPresenter:
    """What the Song page shows and does for the current song of the set a document holds: page is what its fields ask
    through, rename renames the song, which only the page can, since its crumbs follow, and export_button is the page's."""

    __slots__ = ('_page', '_document', '_rename', '_export_button')

    def __init__(self, *, page, document, rename, export_button):
        self._page = page
        self._document = document
        self._rename = rename
        self._export_button = export_button

    def song(self):
        return self._document.song()


    def form(self):
        """Return the page's form: the song's settings, one a line, then the Export button."""
        song = self.song()
        return [
            NameField(value=self._document.get_current_song_name, rename=self._rename),
            self.tempo_field(song),
            Field(label=labels.MSG_TIME_SIGNATURE_LABEL, value=self.time_signature_text, adjust=self.step_time_signature, enter=self.ask_time_signature),
            Field(label=labels.MSG_ENTRY_SIZE_LABEL, value=self.entry_size_shown, adjust=self.step_entry_size, enter=self.pick_entry_size, enter_what=legends.What.CHOOSE,
                  clear=functools.partial(self.set_entry_size, None), clear_what=marks.MSG_ONE_STEP_SHOWN),
            Field(label=labels.MSG_SCALE_LABEL, value=self.scale_shown, adjust=self.step_scale, enter=self.pick_scale, enter_what=legends.What.CHOOSE,
                  clear=functools.partial(self.set_scale_name, None), clear_what=marks.MSG_NONE_SHOWN),
            Field(label=labels.MSG_GROOVE_LABEL, value=song.get_groove_name, adjust=self.step_groove, enter=self.pick_groove, enter_what=legends.What.CHOOSE),
            *self.style_fields(song),
            self.live_responsiveness_field(song),
            Field(label=labels.MSG_PREVIEW_INSTRUMENT_LABEL, value=self.preview_instrument_shown, adjust=self.step_preview_instrument,
                  enter=self.pick_preview_instrument, enter_what=legends.What.CHOOSE, clear=functools.partial(self.set_preview_instrument_name, None),
                  clear_what=labels.MSG_PREVIEW_INSTRUMENT_UNSET),
            visualizer_field(page=self._page, current=song.get_visualizer(), set_name=self.set_visualizer, first=labels.MSG_SETS_VISUALIZER_CHOICE),
            self._export_button,
        ]


    def tempo_field(self, song):
        """Return the Tempo field, a whole number stepped and typed with the song's tempo shown in full."""
        tempo = song.get_tempo()
        typed = tempo_text(tempo)
        shown = marks.MSG_TEMPO_SHOWN.format(tempo=typed)
        return NumberField(page=self._page, label=labels.MSG_TEMPO_LABEL, number=int(tempo), shown=shown, typed=typed, lowest=limits.MIN_TEMPO, highest=limits.MAX_TEMPO,
                           set=self.set_tempo)


    def style_fields(self, song):
        """Return the Genre, Subgenre and Variant fields, each offering what the one above it allows."""
        genre = song.get_genre()
        subgenre = song.get_subgenre()
        variants = variants_of(genre=genre, subgenre=subgenre)
        return [
            self.style_field(label=labels.MSG_GENRE_LABEL, choices=genres.GENRES, current=genre, set_choice=self.set_genre),
            self.style_field(label=labels.MSG_SUBGENRE_LABEL, choices=subgenres_of(genre), current=subgenre, set_choice=self.set_subgenre),
            self.style_field(label=labels.MSG_VARIANT_LABEL, choices=variants, current=song.get_variant(), set_choice=self.set_variant),
        ]


    def live_responsiveness_field(self, song):
        """Return the Live responsiveness field: how soon an edit is heard on what plays."""
        names = []
        for choice in file_format.LIVE_RESPONSIVENESSES:
            names.append(labels.MSG_LIVE_RESPONSIVENESS_NAMES[choice])
        current = song.get_live_responsiveness()
        return ChoiceField(page=self._page, label=labels.MSG_LIVE_RESPONSIVENESS_LABEL, choices=file_format.LIVE_RESPONSIVENESSES, current=current, names=names,
                           shown=labels.MSG_LIVE_RESPONSIVENESS_NAMES[current], set=self.set_live_responsiveness)


    def time_signature_text(self):
        time_signature = self.song().get_time_signature()
        return time_signature.to_text()


    def entry_size_shown(self):
        return self.entry_size_text() or marks.MSG_ONE_STEP_SHOWN


    def scale_shown(self):
        return self.song().get_scale_name() or marks.MSG_NONE_SHOWN


    def preview_instrument_shown(self):
        return self.song().get_preview_instrument_name() or labels.MSG_PREVIEW_INSTRUMENT_UNSET


    def set_tempo(self, tempo):
        self._change(self.song().set_tempo, tempo)


    def set_time_signature(self, text):
        self._change(self.song().set_time_signature, text)


    def set_entry_size(self, size):
        self._change(self.song().set_entry_size, size)


    def set_scale_name(self, name):
        self._change(self.song().set_scale_name, name)


    def set_groove_name(self, name):
        self._change(self.song().set_groove_name, name)


    def set_genre(self, genre):
        self._change(self.song().set_genre, genre)


    def set_subgenre(self, subgenre):
        self._change(self.song().set_subgenre, subgenre)


    def set_variant(self, variant):
        self._change(self.song().set_variant, variant)


    def set_live_responsiveness(self, value):
        self._change(self.song().set_live_responsiveness, value)


    def set_preview_instrument_name(self, name):
        self._change(self.song().set_preview_instrument_name, name)


    def set_visualizer(self, name):
        self._change(self.song().set_visualizer, name)


    def step_time_signature(self, offset):
        """Move to the next or previous common time signature, from 4/4 if the song's isn't in the list."""
        choices = file_format.TIME_SIGNATURE_CHOICES
        current = self.time_signature_text()
        if current not in choices:
            current = defaults.DEFAULT_TIME_SIGNATURE
        self.set_time_signature(stepped_from(values=choices, place=choices.index(current), offset=offset))


    def ask_time_signature(self):
        current = self.time_signature_text()
        ask_time_signature(page=self._page, title=messages.MSG_SONG_TIME_SIGNATURE_PROMPT, current=current, then=self.set_time_signature, blank_allowed=False)


    def entry_size_text(self):
        """Return the song's entry size as text, like 1/8, or None for one step."""
        entry_size = self.song().get_written_entry_size()
        if entry_size is None:
            return None
        return str(entry_size)


    def step_entry_size(self, offset):
        """Move to the next or previous step size, with one step before the shortest, and from one step if the song's size isn't in the list."""
        choices = [None, *file_format.STEP_SIZE_CHOICES]
        current = self.entry_size_text()
        place = 0
        if current in choices:
            place = choices.index(current)
        self.set_entry_size(stepped_from(values=choices, place=place, offset=offset))


    def pick_entry_size(self):
        choices = [None, *file_format.STEP_SIZE_CHOICES]
        options = [marks.MSG_ONE_STEP_SHOWN, *file_format.STEP_SIZE_CHOICES]
        self._page.pick(title=labels.MSG_ENTRY_SIZE_LABEL, values=choices, shown=options, current=self.entry_size_text(), then=self.set_entry_size)


    def scale_names(self):
        """Return the set's scales, sorted by name."""
        setlist = self._document.get_setlist()
        return sorted_names(setlist.get_scale_names())


    def groove_names(self):
        """Return the set's grooves, sorted by name, in the order the picker shows them."""
        setlist = self._document.get_setlist()
        return sorted_names(setlist.get_groove_names())


    def step_scale(self, offset):
        """Move to the next or previous of the set's scales, with no scale before the first."""
        names = [None, *self.scale_names()]
        place = names.index(self.song().get_scale_name())
        self.set_scale_name(stepped_from(values=names, place=place, offset=offset))


    def preview_instruments(self):
        """Return what the Preview instrument field chooses among: none, which is the pattern's own track, then the set's instruments by name."""
        setlist = self._document.get_setlist()
        return [None, *sorted_names(setlist.get_instrument_names())]


    def step_preview_instrument(self, offset):
        """Move to the next or previous instrument, stopping at both ends."""
        names = self.preview_instruments()
        place = names.index(self.song().get_preview_instrument_name())
        self.set_preview_instrument_name(stepped_from(values=names, place=place, offset=offset))


    def pick_preview_instrument(self):
        names = self.preview_instruments()
        options = [labels.MSG_PREVIEW_INSTRUMENT_UNSET, *names[1:]]
        current = self.song().get_preview_instrument_name()
        self._page.pick(title=messages.MSG_PREVIEW_INSTRUMENT_TITLE, values=names, shown=options, current=current, then=self.set_preview_instrument_name)


    def style_field(self, *, label, choices, current, set_choice):
        """Return a field for the song's genre, its subgenre or its variant: one of the choices, or undefined, which is all a field with no choices offers."""
        offered = [marks.MSG_UNDEFINED_SHOWN, *choices]
        return ChoiceField(
            page=self._page, label=label, choices=offered, current=current or marks.MSG_UNDEFINED_SHOWN, set=functools.partial(self._set_style, set_choice=set_choice),
            clear=functools.partial(set_choice, None), clear_what=marks.MSG_UNDEFINED_SHOWN,
        )


    @staticmethod
    def _set_style(choice, *, set_choice):
        """Set a genre, a subgenre or a variant to the choice, or to none for undefined."""
        if choice == marks.MSG_UNDEFINED_SHOWN:
            choice = None
        set_choice(choice)


    def step_groove(self, offset):
        """Move to the next or previous groove, in the order the picker shows them."""
        self.set_groove_name(stepped(values=self.groove_names(), current=self.song().get_groove_name(), offset=offset))


    def pick_groove(self):
        self._page.pick(title=messages.MSG_SONG_GROOVE_TITLE, values=self.groove_names(), current=self.song().get_groove_name(), then=self.set_groove_name)


    def pick_scale(self):
        scales = self.scale_names()
        if not scales:
            self._page.refuse(errors.ERR_ADD_A_SCALE_FIRST)
            return
        self._page.pick(title=messages.MSG_SONG_SCALE_TITLE, values=scales, current=self.song().get_scale_name(), then=self.set_scale_name)


    def _change(self, setter, *arguments):
        """Change the song through one of its setters, as one edit of the set."""
        self._document.change_set(setter, *arguments)


def stepped_from(*, values, place, offset):
    """Return the value so many places on from a place in a list, stopping at both ends."""
    moved = max(min(place + offset, len(values) - 1), 0)
    return values[moved]
