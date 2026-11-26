# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Document's edits to what the whole set shares: its settings, songs, scales, generators, chains and grooves.

Renaming, copying, deleting, moving and sorting any of them is in named_edits.py, which takes
the section. What's here is what each kind alone has: how a new one starts, and its own settings.
"""


from llamatron.model.objects.groove import new_groove
from llamatron.model.objects.named_scale import NamedScale, scale_type_name
from llamatron.model.objects.naming import default_scale_name, is_default_scale_name, words
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import InstrumentRole, Section
from llamatron.model.values import note
from llamatron.user_strings import marks



class SetEdits:
    """The changes the File, Songs, Scales, Generators, Chains and Grooves pages make, each through the set's own setters.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self.change_set(method, ...)` or `self.change_pattern(method, ...)`, which make one change through an object's own
    method and notes it.
    """

    __slots__ = ()

    # The set's own settings, from the File page.

    # The songs of the set.

    def song_names(self):
        return self._setlist.get_song_names()

    def add_song(self, name):
        """Add a song with its first track and scene at the end of the set, and make it current."""
        self.change_set(self._setlist.add_started_song, name)
        self.select_song(name)

    def import_song(self, imported):
        """Add a song the MIDI import made, with its patterns and scales, as one change, and make it current."""
        self.change_set(imported.add_to, self._setlist)
        self.select_song(imported.name)

    def add_made_song(self, made):
        """Take in the one song of a set the song wizard made, with all the song uses, as one change, make the song current and return its name here."""
        name = self.change_set(self._setlist.take_in, made)[0]
        self._play_made_song_in_real_time()
        self.select_song(name)
        return name

    def replace_with_made_song(self, made, *, new=None):
        """Replace the current song, in its place, with the one song of a set the song wizard made, as one change, and return its name:
        the replaced song's, or a new name when one is given, as when an untouched song is filled."""
        name = self.change_set(self._setlist.replace_song, name=self._current, other=made, new=new)
        self._play_made_song_in_real_time()
        self.select_song(name)
        return name

    def _play_made_song_in_real_time(self):
        """Turn real-time playback on, as the first instrument added does, since a made song brings instruments and is there to be heard."""
        if self._setlist.get_instrument_names() and not self._setlist.is_real_time():
            self.change_set(self._setlist.set_real_time, True)

    def current_song_is_untouched(self):
        return self._setlist.song_is_untouched(self._current)

    # Scales.

    def _scale(self, name):
        return self._setlist.get_named_scale(name)

    def scale_size(self, name):
        return self._scale(name).get_size()

    def scale_half_steps(self, name):
        """Return a scale's degrees as half steps above its root, starting with 0."""
        return self._scale(name).get_half_steps()

    def scale_spells_flats(self, name):
        """Return whether a scale's root is spelled with a flat, so that a note between two of its degrees is named as a flat too."""
        return self._scale(name).get_root().endswith(note.FLAT_SIGN)

    def scale_note_at(self, *, name, octave, half_steps):
        """Return the name and sounding octave of the note some half steps above a scale's root in an octave, spelled as the root is, for a piano roll row between two degrees."""
        return self._scale(name).scale_at(octave).get_root().spelled_half_step(half_steps)

    def scale_degree_octave(self, *, name, octave, place):
        """Return the octave the degree at a place of a scale sounds in when its root is in an octave, for the piano roll's row labels."""
        return self._scale(name).octave_of_degree(octave=octave, place=place)

    def scale_notes_text(self, name):
        """Return what a named scale is, like F minor."""
        scale = self._scale(name)
        return marks.MSG_SCALE_NOTES_TEXT.format(root=scale.get_root(), kind=words(scale_type_name(scale.get_scale_type())))

    def scale_name_says_what_it_is(self, name):
        """Return whether a scale is still named after its root and kind, like C Major, so that showing both would say it twice."""
        scale = self._scale(name)
        return is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())

    def add_scale(self, *, name, root, kind):
        self.change_set(self._setlist.add_item, section=Section.SCALES, name=name, item=NamedScale(root=root, kind=kind))

    def set_scale_root(self, *, name, root):
        """Change a named scale's root, which moves everything that uses it, and return the scale's name, which may have followed."""
        scale = self._scale(name)
        was_default = is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())
        self.change_set(scale.set_root, root)
        return self._scale_name_following_its_notes(name=name, was_default=was_default)

    def set_scale_kind(self, *, name, kind):
        """Change a named scale's kind, which changes everything that uses it, and return the scale's name, which may have followed."""
        scale = self._scale(name)
        was_default = is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())
        self.change_set(scale.set_kind, kind)
        return self._scale_name_following_its_notes(name=name, was_default=was_default)

    def _scale_name_following_its_notes(self, *, name, was_default):
        """Rename a scale that was still named after its root and kind, like C Major, to say what it is now, and return its name.

        A scale with a name of the user's own, like main, keeps it, and so does one whose new
        name is already taken. This is so that a scale can't be
        called C Major and play D minor.
        """
        scale = self._scale(name)
        new = default_scale_name(root=scale.get_root(), kind=scale.get_kind())
        if not was_default or new == name or self._setlist.has_scale(new):
            return name
        self.rename_named(section=Section.SCALES, old=name, new=new)
        return new

    # Arps and chains.

    def generator(self, *, section, name):
        return self._setlist.get_generator_settings(kind=generator_plugins.names_by_section()[section], name=name)

    def add_generator(self, *, section, name):
        """Add a generator of a section with the settings a new one starts with, a chain with no steps."""
        if section == Section.CHAINS:
            self.add_chain(name)
            return
        kind = generator_plugins.names_by_section()[section]
        settings = generator_plugins.settings_of(kind).new()
        self.change_set(self._setlist.add_item, section=section, name=name, item=settings)

    def _chain(self, name):
        return self._setlist.get_chain(name)

    def add_chain(self, name):
        self.change_set(self._setlist.add_new_chain, name)

    def move_chain_step(self, *, chain, place, offset):
        """Move a chain's step up or down, and return whether it moved."""
        if not self._chain(chain).move_step(place=place, offset=offset):
            return False
        self.changed()
        return True

    # Grooves, of the set, beside the factory grooves every set has, which can be copied but not changed.

    def add_instrument(self, name, *, role=InstrumentRole.NORMAL):
        """Add an instrument of a role with no device yet under a name. The first instrument turns real-time playback on."""
        first = not self._setlist.get_instrument_names()
        self.change_set(self._setlist.add_new_instrument, name, role=role)
        if first:
            self.change_set(self._setlist.set_real_time, True)

    def instruments_of_role(self, role):
        """Return the names of the set's instruments of a role (InstrumentRole), in the set's order."""
        setlist = self._setlist
        return [name for name in setlist.get_instrument_names() if setlist.get_instrument(name).get_role() == role]

    def add_groove(self, name):
        """Add a straight groove of one bar of 16ths under a name, which can't be a factory groove's."""
        self.change_set(self._setlist.add_item, section=Section.GROOVES, name=name, item=new_groove())
