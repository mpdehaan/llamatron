# llamatron: a music program
# Copyright (C) 2026  Michael DeHaan
# SPDX-License-Identifier: GPL-3.0-or-later

"""The Document's edits to what the whole set shares: its settings, songs, scales, generators, chains and grooves.

Renaming, copying, deleting, moving and sorting any of them is in named_edits.py, which takes
the section. What's here is what each kind alone has: how a new one starts, and its own settings.
"""


from llamatron.engine.generators import arp as arp_plugin, musician as musician_plugin, progression as progression_plugin
from llamatron.engine.generators.progression.settings import ProgressionSetting
from llamatron.importers.writing import add_imported
from llamatron.model.objects.chain import Chain
from llamatron.model.objects.groove import new_groove
from llamatron.model.objects.instrument import Instrument
from llamatron.model.objects.named_scale import NamedScale, scale_type_name
from llamatron.model.objects.naming import default_scale_name, is_default_scale_name, words
from llamatron.model.schema import generator_plugins
from llamatron.model.schema.file_format import Section
from llamatron.model.values import note
from llamatron.user_strings import marks



class SetEdits:
    """The changes the File, Songs, Scales, Generators, Chains and Grooves pages make, each through the set's own setters.

    It holds no data of its own: it works on what Document keeps, through `self._setlist`,
    `self.song()` and `self.change(method, ...)`, which makes one change through an object's own
    method and notes it.
    """

    __slots__ = ()

    # The set's own settings, from the File page.

    # The songs of the set.

    def song_names(self):
        return self._setlist.get_song_names()

    def add_song(self, name):
        """Add a song with its first track and scene at the end of the set, and make it current."""
        self.change(self._setlist.add_started_song, name)
        self.select_song(name)

    def import_song(self, imported):
        """Add a song the MIDI import made, with its patterns and scales, as one change, and make it current."""
        add_imported(setlist=self._setlist, imported=imported)
        self.changed()
        self.select_song(imported.name)

    def add_made_song(self, made):
        """Take in the one song of a set the song wizard made, with all the song uses, as one change, make the song current and return its name here."""
        name = self.change(self._setlist.take_in, made)[0]
        self._play_made_song_in_real_time()
        self.select_song(name)
        return name

    def replace_with_made_song(self, made, *, new=None):
        """Replace the current song, in its place, with the one song of a set the song wizard made, as one change, and return its name:
        the replaced song's, or a new name when one is given, as when an untouched song is filled."""
        name = self.change(self._setlist.replace_song, name=self._current, other=made, new=new)
        self._play_made_song_in_real_time()
        self.select_song(name)
        return name

    def _play_made_song_in_real_time(self):
        """Turn real-time playback on, as the first instrument added does, since a made song brings instruments and is there to be heard."""
        if self._setlist.get_instrument_names() and not self._setlist.is_real_time():
            self.change(self._setlist.set_real_time, True)

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
        self.change(self._setlist.add_item, section=Section.SCALES, name=name, item=NamedScale(root=root, kind=kind))

    def set_scale_root(self, *, name, root):
        """Change a named scale's root, which moves everything that uses it, and return the scale's name, which may have followed."""
        scale = self._scale(name)
        was_default = is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())
        self.change(scale.set_root, root)
        return self._scale_name_following_its_notes(name=name, was_default=was_default)

    def set_scale_kind(self, *, name, kind):
        """Change a named scale's kind, which changes everything that uses it, and return the scale's name, which may have followed."""
        scale = self._scale(name)
        was_default = is_default_scale_name(name=name, root=scale.get_root(), kind=scale.get_kind())
        self.change(scale.set_kind, kind)
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
        self.change(self._setlist.add_item, section=section, name=name, item=settings)

    def set_musician_section(self, *, name, section, setting, value):
        """Set what a kind of section has of its own for a musician, whether the musician plays there or how the part is played, or None for what a section does unasked."""
        self.change(self.generator(section=musician_plugin.SECTION, name=name).set_section_own, section=section, name=setting, value=value)

    def set_progression(self, *, name, chords, accidentals, inversions, scales=None, qualities=None, tensions=None):
        """Set a progression's chords, with a sharp or flat, an inversion, a borrowed scale type, a quality and tensions for each, a row of nothing left out."""
        progression = self.generator(section=progression_plugin.SECTION, name=name)
        nothing = [None] * len(chords)
        rows = {
            ProgressionSetting.CHORDS: chords, ProgressionSetting.ACCIDENTALS: accidentals, ProgressionSetting.INVERSIONS: inversions,
            ProgressionSetting.SCALES: scales or nothing, ProgressionSetting.QUALITIES: qualities or nothing,
            ProgressionSetting.TENSIONS: [None if value is None else list(value) for value in tensions or nothing],
        }
        for setting, values in rows.items():
            self.change(progression.set_setting, name=setting, value=list(values) if any(value is not None for value in values) else None)

    def set_arp_offset(self, *, name, step, offset):
        """Set one step of an arp's offsets, where None is a silent step."""
        self.change(self.generator(section=arp_plugin.SECTION, name=name).set_cell, step=step, value=offset)

    def insert_arp_offset(self, *, name, step):
        """Add a step of 0 before a step of an arp's offsets."""
        self.change(self.generator(section=arp_plugin.SECTION, name=name).insert_cell, step)

    def set_arp_step_add(self, *, name, register, step, add):
        """Set what one step of an arp's offsets adds to a register, where None or 0 adds nothing."""
        self.change(self.generator(section=arp_plugin.SECTION, name=name).set_step_add, register=register, step=step, add=add)

    def remove_arp_offset(self, *, name, step):
        self.change(self.generator(section=arp_plugin.SECTION, name=name).remove_cell, step)

    def _chain(self, name):
        return self._setlist.get_chain(name)

    def add_chain(self, name):
        self.change(self._setlist.add_item, section=Section.CHAINS, name=name, item=Chain([]))

    def move_chain_step(self, *, chain, place, offset):
        """Move a chain's step up or down, and return whether it moved."""
        if not self._chain(chain).move_step(place=place, offset=offset):
            return False
        self.changed()
        return True

    # Grooves, of the set, beside the factory grooves every set has, which can be copied but not changed.

    def add_instrument(self, name):
        """Add an instrument with no device yet under a name. The first instrument turns real-time playback on."""
        first = not self._setlist.get_instrument_names()
        self.change(self._setlist.add_item, section=Section.INSTRUMENTS, name=name, item=Instrument())
        if first:
            self.change(self._setlist.set_real_time, True)

    def add_groove(self, name):
        """Add a straight groove of one bar of 16ths under a name, which can't be a factory groove's."""
        self.change(self._setlist.add_item, section=Section.GROOVES, name=name, item=new_groove())
